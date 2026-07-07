"""
=============================================================================
Observer Node — 工具结果观察分析
=============================================================================
职责：
  1. 读取刚完成的工具调用结果
  2. 分析成功/失败，提取关键事实
  3. 决定是否需要重新规划（need_replan）

输入（State 读取）：
  - tool_calls[-1]: 最新的工具调用记录
  - plan_steps[current_step_index - 1]: 当前步骤的计划信息
  - retry_count: 累计重试次数

输出（State 写入）：
  - observations: 追加一条观察结论
  - next_action: "continue" | "replan" | "answer"
  - retry_count: 需要时递增
  - steps: 追加一条 "observe" 步骤

设计说明：
  - 不调 LLM，纯规则判断
  - 简单的事实提取（天气有雨 → need_umbrella=true）
  - 根据 on_failure 策略决定下一步动作
=============================================================================
"""

from app.agent.state import AgentState, MAX_RETRIES
from app.utils.logger import logger


async def observer_node(state: AgentState) -> dict:
    """
    观察工具结果并分析

    参数：
        state: 当前 AgentState

    返回值：
        要更新的 State 字段（部分）
    """
    tool_calls = state.get("tool_calls", [])
    if not tool_calls:
        logger.warning("[observer] 没有工具调用记录，跳过观察")
        return {
            "next_action": "continue",
            "steps": [{
                "id": "step-observe",
                "name": "观察工具结果",
                "status": "completed",
                "type": "observe",
            }],
        }

    latest = tool_calls[-1]
    tool_name = latest.get("tool_name", "unknown")
    status = latest.get("status", "error")
    summary = latest.get("summary", "")
    tool_output_raw = latest.get("tool_output")
    step_id = latest.get("step_id", 0)

    # ---- 防御性处理：tool_output 可能为 None、str、或 dict ----
    tool_output: dict = {}
    if isinstance(tool_output_raw, dict):
        tool_output = tool_output_raw
    elif isinstance(tool_output_raw, str):
        tool_output = {"_raw": tool_output_raw}
    elif tool_output_raw is None:
        logger.debug(
            f"[observer] {tool_name} 的 tool_output 为 None"
        )
    else:
        logger.warning(
            f"[observer] {tool_name} 的 tool_output 类型异常: "
            f"{type(tool_output_raw).__name__}"
        )

    # 查找对应 plan step 的失败策略
    plan_steps = state.get("plan_steps", [])
    current_index = state.get("current_step_index", 0)
    on_failure = "abort"
    if current_index > 0 and current_index <= len(plan_steps):
        on_failure = plan_steps[current_index - 1].get("on_failure", "abort")

    logger.info(
        f"[observer] 观察 {tool_name} 结果: status={status}, "
        f"on_failure={on_failure} | summary={summary[:100]}"
    )
    logger.debug(
        f"[observer] {tool_name} tool_output 关键字段: "
        f"{list(tool_output.keys())[:10] if tool_output else '(empty)'}"
    )

    # =====================================================================
    # 提取关键事实
    # =====================================================================
    extracted_facts = {}
    observation_text = ""

    if status == "success":
        # 尝试从工具输出中提取结构化事实
        # 天气工具 → 提取降雨、温度
        if tool_name in ("weather", "weather_tool"):
            forecast_days = tool_output.get("forecast_days") or []
            weather = tool_output.get("weather", "")
            temperature = tool_output.get("temperature", "")
            if forecast_days:
                rainy_days = [
                    day for day in forecast_days
                    if isinstance(day, dict) and day.get("has_precipitation")
                ]
                extracted_facts["forecast_days"] = len(forecast_days)
                extracted_facts["has_precipitation"] = bool(rainy_days)
                extracted_facts["rainy_dates"] = [
                    day.get("date") for day in rainy_days if isinstance(day, dict)
                ]
                extracted_facts["temperature_range"] = [
                    {
                        "date": day.get("date"),
                        "temperature": day.get("temperature"),
                    }
                    for day in forecast_days if isinstance(day, dict)
                ]
            elif weather and any(kw in str(weather).lower() for kw in ["雨", "rain", "雪", "snow"]):
                extracted_facts["has_precipitation"] = True
                extracted_facts["precipitation_type"] = weather
                extracted_facts["temperature"] = temperature

        # 日期工具 → 提取解析结果
        elif tool_name in ("date_parser", "date_parser_tool"):
            parsed = tool_output.get("date", "")
            extracted_facts["parsed_date"] = parsed
            extracted_facts["day_of_week"] = tool_output.get("weekday", "")

        # 城市解析工具 → 提取 adcode 和 city
        elif tool_name in ("city_resolver", "city_resolver_tool"):
            adcode_val = tool_output.get("adcode", "")
            city_val = tool_output.get("city", "")
            province_val = tool_output.get("province", "")

            if not adcode_val:
                logger.warning(
                    f"[observer] CityResolver 返回了成功状态但 adcode 为空！"
                    f" | tool_output keys: {list(tool_output.keys())}"
                    f" | city={city_val!r} | province={province_val!r}"
                )
            else:
                logger.info(
                    f"[observer] CityResolver 提取: city={city_val!r} "
                    f"adcode={adcode_val!r} province={province_val!r}"
                )

            extracted_facts["adcode"] = adcode_val
            extracted_facts["city"] = city_val
            extracted_facts["province"] = province_val

        # 路线工具 → 提取距离、耗时
        elif tool_name in ("route_planner", "route_planner_tool"):
            extracted_facts["distance"] = tool_output.get("distance", "")
            extracted_facts["duration"] = tool_output.get("duration", "")

        observation_text = f"{tool_name} 执行成功。{summary}"

    else:
        # 工具执行失败
        error_msg = latest.get("error", "未知错误")
        observation_text = f"{tool_name} 执行失败: {error_msg}"

    # =====================================================================
    # 判断下一步动作
    # =====================================================================
    retry_count = state.get("retry_count", 0)
    next_action = "continue"

    if status != "success":
        if on_failure == "retry_once" and retry_count < MAX_RETRIES:
            # 重试
            next_action = "continue"
            retry_count += 1
            logger.info(
                f"[observer] {tool_name} 失败，准备重试 "
                f"(第 {retry_count}/{MAX_RETRIES} 次)"
            )
        elif on_failure == "skip":
            # 跳过，继续下一步
            next_action = "continue"
            logger.info(f"[observer] {tool_name} 失败，按策略跳过")
        else:
            # abort → 直接进入 answer
            next_action = "answer"
            logger.warning(f"[observer] {tool_name} 失败，按策略终止")

    # 追加观察结论
    observation_record = {
        "step_id": step_id,
        "tool_name": tool_name,
        "observation": observation_text,
        "extracted_facts": extracted_facts,
        "need_replan": False,
        "confidence": 0.9 if status == "success" else 0.2,
    }

    # 追加前端展示步骤
    step = {
        "id": f"step-observe-{len(tool_calls)}",
        "name": f"分析{tool_name}结果",
        "status": "completed" if status == "success" else "failed",
        "type": "observe",
        "error": latest.get("error") if status != "success" else None,
    }

    return {
        "observations": [observation_record],
        "next_action": next_action,
        "retry_count": retry_count,
        "steps": [step],
        # 将 CityResolver 解析结果同步写入 State 顶层字段
        "city": extracted_facts.get("city", state.get("city", "")),
        "adcode": extracted_facts.get("adcode", state.get("adcode", "")),
    }
