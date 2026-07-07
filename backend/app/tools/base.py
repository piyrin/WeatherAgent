"""
=============================================================================
Tool 抽象基类 — 所有工具的统一接口契约
=============================================================================
职责：
  1. 定义 Tool 的标准接口（name、description、input_schema、run）
  2. 提供错误边界保护（run 方法自动捕获异常）
  3. 提供耗时统计

Agent 核心设计：
  每个工具必须遵守此接口，Agent 才能统一调用。
  新增工具只需：
    ① 继承 BaseTool
    ② 实现 name、description、input_schema、_execute 方法
    ③ 在 tool_registry.py 中注册

设计原则：
  - 开闭原则：对扩展开放（新增 Tool），对修改关闭（不改 Agent 代码）
  - 接口隔离：Tool 只暴露 Agent 需要的四个属性/方法
  - 错误隔离：单个 Tool 异常不会导致整个 Agent 崩溃
=============================================================================
"""

import time
from abc import ABC, abstractmethod
from typing import Any

from app.utils.logger import logger


class BaseTool(ABC):
    """
    Tool 抽象基类 — 所有工具的父类

    子类必须实现的方法：
      - name：           str，工具名称（唯一标识，如 "weather", "date_parser"）
      - description：    str，工具描述（给 LLM 看的，用于 Function Calling）
      - input_schema：   dict，工具输入参数的 JSON Schema（约束 LLM 传参格式）
      - _execute(**kwargs)：工具核心逻辑（私有方法，由 run 包装调用）

    子类可选覆盖的方法：
      - validate_input：校验 LLM 传入的参数是否合法（默认不做校验）

    用法示例：
        class WeatherTool(BaseTool):
            name = "weather"
            description = "查询指定城市在指定日期的天气信息"

            @property
            def input_schema(self) -> dict:
                return {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "城市名称"},
                        "date": {"type": "string", "description": "日期（YYYY-MM-DD）"},
                    },
                    "required": ["city"],
                }

            async def _execute(self, city: str, date: str | None = None) -> dict:
                # 实际调用天气 API
                ...
    """

    # =========================================================================
    # 子类必须定义的属性/方法（抽象）
    # =========================================================================

    @property
    @abstractmethod
    def name(self) -> str:
        """
        工具名称（唯一标识）

        示例： "weather", "date_parser", "route_planner"
        注意：名称必须在整个系统中唯一
        """
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """
        工具描述（给 LLM 看的）

        LLM 根据此描述决定何时调用此工具。
        描述应清晰说明：
          - 工具的功能
          - 适用的场景
          - 输入参数的含义

        示例：
            "查询指定城市的天气信息。支持查询当天和未来 7 天的天气。
             参数：city（城市名称），date（日期，可选，默认当天）"
        """
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict:
        """
        工具输入参数的 JSON Schema

        LLM 根据此 Schema 知道该传什么参数、什么类型。

        示例：
            {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"},
                    "date": {"type": "string", "description": "日期（YYYY-MM-DD）"},
                },
                "required": ["city"],
            }
        """
        ...

    @abstractmethod
    async def _execute(self, **kwargs: Any) -> dict:
        """
        工具的核心执行逻辑（私有方法，需子类实现）

        参数：
            **kwargs：LLM 传入的参数（由 input_schema 约束类型）

        返回值：
            dict，必须包含以下字段：
              - success:   bool（执行是否成功）
              - result:    Any（成功时的结果数据）
              - error:     str（失败时的错误信息）
              - summary:   str（可读的结果摘要，用于 LLM 理解和前端展示）
        """
        ...

    # =========================================================================
    # 公共方法（不推荐子类覆盖）
    # =========================================================================

    async def run(self, **kwargs: Any) -> dict:
        """
        工具执行的公共入口 — 提供错误边界和耗时统计

        子类不应覆盖此方法。_execute 中的任何异常都会被此方法捕获并转为统一格式。

        参数：
            **kwargs：LLM 传入的参数

        返回值：
            dict，格式为：
            {
                "success": True/False,
                "result": ...,
                "error": None/"错误信息",
                "summary": "可读摘要",
                "tool_name": "weather",
                "duration_ms": 123.45,
            }
        """
        start_time = time.perf_counter()

        logger.debug(f"Tool [{self.name}] 开始执行 | 参数={kwargs}")

        try:
            # 参数校验
            self.validate_input(**kwargs)

            # 执行核心逻辑
            result = await self._execute(**kwargs)

            duration = (time.perf_counter() - start_time) * 1000

            # 确保返回格式统一
            if not isinstance(result, dict):
                result = {"success": True, "result": result, "summary": str(result)}
            result.setdefault("success", True)
            result.setdefault("error", None)
            result["tool_name"] = self.name
            result["duration_ms"] = round(duration, 2)

            logger.info(
                f"Tool [{self.name}] 执行成功 | "
                f"耗时={duration:.1f}ms | 结果摘要={result.get('summary', '')[:100]}"
            )
            return result

        except Exception as exc:
            duration = (time.perf_counter() - start_time) * 1000
            error_msg = f"{type(exc).__name__}: {str(exc)}"

            logger.error(
                f"Tool [{self.name}] 执行失败 | "
                f"耗时={duration:.1f}ms | 错误={error_msg}"
            )

            return {
                "success": False,
                "result": None,
                "error": error_msg,
                "summary": f"工具 [{self.name}] 执行失败: {str(exc)}",
                "tool_name": self.name,
                "duration_ms": round(duration, 2),
            }

    def validate_input(self, **kwargs: Any) -> None:
        """
        参数校验方法（可选覆盖）

        默认不做校验（信任 LLM 的输出和 input_schema 的约束）。
        子类可以覆盖此方法添加业务级校验（如 city 是否在支持列表中）。

        参数：
            **kwargs：LLM 传入的参数

        异常：
            ValueError：参数不合法时抛出
        """
        pass

    def to_langchain_tool(self):
        """
        将当前 Tool 转为 LangChain 的 Tool 对象

        此方法将 Python 对象转为 LangChain 的 BaseTool 子类实例，
        使 Agent 可以通过 LangChain 的 Function Calling 机制调用。

        返回值：
            langchain_core.tools.BaseTool 实例
        """
        from langchain_core.tools import tool as langchain_tool_decorator

        tool_name = self.name
        tool_desc = self.description
        tool_func = self.run
        input_schema = self.input_schema

        # 使用 LangChain 的 @tool 装饰器创建 Tool 对象
        # 注意：装饰器要求函数必须有 docstring，因此在装饰前先动态设置
        async def _tool_func(**kwargs: Any) -> str:
            result = await tool_func(**kwargs)
            if result["success"]:
                return result.get("summary", str(result.get("result", "")))
            else:
                return f"错误: {result.get('error', '未知错误')}"

        _tool_func.__name__ = tool_name
        _tool_func.__doc__ = tool_desc
        if input_schema:
            _tool_func.args_schema = input_schema

        _tool_func = langchain_tool_decorator(name_or_callable=tool_name)(_tool_func)

        return _tool_func

    def __repr__(self) -> str:
        return f"<Tool(name={self.name})>"
