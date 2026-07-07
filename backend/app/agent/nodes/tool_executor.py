"""
=============================================================================
Tool Executor Node — 工具调度执行
=============================================================================
职责：
  1. 从 plan_steps[current_step_index] 读取工具名和参数
  2. 通过 tool_registry 查找并执行工具
  3. 记录执行结果、耗时、状态到 state.tool_calls

输入（State 读取）：
  - plan_steps[current_step_index]: 当前要执行的步骤
  - tool_calls: 上一步的工具结果（用于参数引用替换）

输出（State 写入）：
  - tool_calls: 追加一条工具调用记录
  - current_step_index: 递增 1
  - steps: 追加一条 "tool_call" 步骤

设计说明：
  - 不调 LLM，纯工具调度
  - 每个工具调用独立计时
  - 异常隔离：一个工具失败不影响其他工具
  - 支持 $step_N.field 参数引用（从之前步骤的输出中取值）
=============================================================================
"""

import time
import re
from datetime import datetime, timezone

from app.agent.state import AgentState
from app.agent.tool_registry import tool_registry
from app.utils.logger import logger


# 参数引用正则：匹配 "$step_2.parsed_date" 格式
_PARAM_REF_PATTERN = re.compile(r"\$step_(\d+)\.(\w+)")


def _resolve_params(tool_input: dict, tool_calls: list[dict]) -> dict:
    """
    解析工具参数中的 $step_N.field 引用

    例如：
      tool_input = {"city": "武汉", "date": "$step_1.date"}
      如果 step_1 的输出中有 date="2026-07-08"，
      则替换为 {"city": "武汉", "date": "2026-07-08"}

    参数：
        tool_input: 原始参数（可能含引用）
        tool_calls: 已完成的工具调用记录

    返回值：
        解析后的参数字典
    """
    resolved = {}
    for key, value in tool_input.items():
        if isinstance(value, str):
            match = _PARAM_REF_PATTERN.search(value)
            if match:
                step_id = int(match.group(1))
                field = match.group(2)
                resolved_value = None
                found = False

                # 在已完成工具调用中查找对应步骤的输出
                for tc in tool_calls:
                    if tc.get("step_id") == step_id:
                        output = tc.get("tool_output")

                        # ---- 防御性检查：tool_output 可能为 None 或非 dict ----
                        if output is None:
                            resolved_value = None
                            found = True
                            logger.warning(
                                f"[executor] 参数引用 ${step_id}.{field}: "
                                f"step_{step_id} 的 tool_output 为 None "
                                f"（工具可能执行失败），无法解析"
                            )
                            break

                        if isinstance(output, dict):
                            if field in output:
                                resolved_value = output.get(field)
                                found = True
                                logger.info(
                                    f"[executor] 参数引用解析成功: "
                                    f"${step_id}.{field} → {resolved_value!r}"
                                )
                            else:
                                found = True
                                available = list(output.keys())
                                logger.warning(
                                    f"[executor] 参数引用字段不存在: "
                                    f"${step_id}.{field} | "
                                    f"step_{step_id} 可用字段: {available} | "
                                    f"tool_name={tc.get('tool_name', '?')}"
                                )
                            break
                        elif isinstance(output, str):
                            resolved_value = output
                            found = True
                            logger.debug(
                                f"[executor] 参数引用: step_{step_id} 输出为纯文本，"
                                f"使用全文作为值"
                            )
                            break

                if found and resolved_value is not None:
                    resolved[key] = resolved_value
                elif found:
                    # 找到了步骤但值为 None 或字段不存在 → 保留原引用，记录日志
                    resolved[key] = value
                    logger.warning(
                        f"[executor] 参数引用保留原值: {key}={value!r} "
                        f"（无法从 step_{step_id} 解析字段 '{field}'）"
                    )
                else:
                    # 完全没找到对应步骤
                    resolved[key] = value
                    logger.warning(
                        f"[executor] 参数引用目标步骤不存在: {value!r} "
                        f"（tool_calls 中无 step_id={step_id}）"
                    )
            else:
                resolved[key] = value
        else:
            resolved[key] = value
    return resolved


async def executor_node(state: AgentState) -> dict:
    """
    执行当前工具调用步骤

    参数：
        state: 当前 AgentState

    返回值：
        要更新的 State 字段（部分）
    """
    current_index = state["current_step_index"]
    plan_steps = state["plan_steps"]
    current_step = plan_steps[current_index]

    tool_name = current_step.get("tool_name", "")
    tool_input_raw = current_step.get("tool_input", {})
    step_id = current_step.get("step_id", current_index + 1)

    logger.info(
        f"[Executor → Tool] 步骤 {step_id}/{len(plan_steps)}: "
        f"调用 {tool_name} | "
        f"原始参数={tool_input_raw}"
    )
    logger.debug(
        f"[Executor] State 摘要 | "
        f"tool_calls 历史={len(state.get('tool_calls', []))}条 | "
        f"observations={len(state.get('observations', []))}条 | "
        f"iteration={state.get('iteration_count', 0)}"
    )

    # 追加前端步骤（running 状态）
    running_step = {
        "id": f"step-tool-{current_index}",
        "name": f"调用{tool_name}工具",
        "status": "running",
        "type": "tool_call",
        "toolName": tool_name,
        "toolInput": tool_input_raw,
    }

    # 解析参数引用
    resolved_input = _resolve_params(tool_input_raw, state.get("tool_calls", []))
    logger.debug(f"[Executor] Tool Input (解析后): {resolved_input}")

    # 记录开始时间
    start = time.perf_counter()
    tool_call_record = {
        "step_id": step_id,
        "tool_name": tool_name,
        "tool_input": resolved_input,
        "tool_output": None,
        "summary": "",
        "status": "success",
        "duration_ms": 0.0,
        "error": None,
    }

    try:
        # 从注册中心获取工具实例
        tool = tool_registry.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"工具 '{tool_name}' 未注册")

        # 执行工具（BaseTool.run() 自带异常处理）
        result = await tool.run(**resolved_input)

        # 记录结果
        tool_call_record["tool_output"] = result.get("result") if isinstance(result, dict) else result
        tool_call_record["summary"] = result.get("summary", str(result)) if isinstance(result, dict) else str(result)
        tool_call_record["status"] = "success" if result.get("success", True) else "error"
        tool_call_record["error"] = result.get("error") if isinstance(result, dict) else None

        logger.info(
            f"[Executor] {tool_name} 执行{'成功' if tool_call_record['status'] == 'success' else '失败'} | "
            f"耗时={tool_call_record['duration_ms']:.1f}ms | "
            f"结果摘要: {tool_call_record.get('summary', 'N/A')[:200]}"
        )
        if tool_call_record["status"] != "success":
            logger.warning(
                f"[Executor] {tool_name} 返回错误 | "
                f"error={tool_call_record.get('error')}"
            )

    except Exception as exc:
        # 工具执行异常
        tool_call_record["status"] = "error"
        tool_call_record["summary"] = f"工具调用失败: {str(exc)}"
        tool_call_record["error"] = str(exc)
        logger.error(f"[executor] {tool_name} 执行异常: {exc}")

    finally:
        # 记录耗时
        tool_call_record["duration_ms"] = round(
            (time.perf_counter() - start) * 1000, 2
        )

    # 更新前端步骤状态
    completed_step = {
        **running_step,
        "status": "completed" if tool_call_record["status"] == "success" else "failed",
        "toolOutput": tool_call_record.get("tool_output"),
        "error": tool_call_record.get("error"),
    }

    return {
        "tool_calls": [tool_call_record],
        "current_step_index": current_index + 1,
        "iteration_count": state.get("iteration_count", 0) + 1,
        "steps": [completed_step],
    }
