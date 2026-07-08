"""
=============================================================================
Tool 注册中心 — 管理 & 发现所有可用工具
=============================================================================
职责：
  1. 维护全局工具注册表（tool name → Tool 实例）
  2. 提供 get_all_tools() 方法给 Agent 获取全部工具列表
  3. 提供 get_tool() 方法按名称查找工具
  4. 自动发现：注册新工具只需在此文件添加一行

设计原则：
  开闭原则 — 新增 Tool 时：
    ① 在 tools/ 目录创建新文件（继承 BaseTool）
    ② 在此文件的 _register_all() 方法中添加注册代码
    ③ Agent 和 Service 层代码零修改

Agent 如何使用：
    from app.agent.tool_registry import tool_registry
    tools = tool_registry.get_all_langchain_tools()  # → list[BaseTool]
    agent = create_agent(tools=tools)
=============================================================================
"""

from app.tools.base import BaseTool
from app.tools.weather import WeatherTool
from app.tools.date_parser import DateParserTool
from app.tools.route_planner import RoutePlannerTool
from app.tools.calculator import CalculatorTool
from app.tools.city_resolver import CityResolverTool
from app.tools.ip_location import IPLocationTool
from app.tools.geocoding import GeocodingTool
from app.utils.logger import logger


class ToolRegistry:
    """
    工具注册中心

    维护 {tool_name: ToolInstance} 的映射表，
    提供 Agent 所需的全部工具列表和单个工具查找。

    用法：
        registry = ToolRegistry()
        registry.register(tool_instance)
        all_tools = registry.get_all()          # → list[BaseTool]
        langchain_tools = registry.get_all_langchain_tools()  # → list[LangChain Tool]
    """

    def __init__(self):
        # 工具映射表：{name: Tool instance}
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        注册一个新工具

        参数：
            tool: BaseTool 子类实例

        注意：
            如果工具名已存在，记录警告但不覆盖（防止运行时异常）
        """
        if tool.name in self._tools:
            logger.warning(
                f"工具名冲突: '{tool.name}' 已存在，跳过多余注册"
            )
            return

        self._tools[tool.name] = tool
        logger.info(f"工具已注册: [{tool.name}] {tool.description[:60]}...")

    def get_tool(self, name: str) -> BaseTool | None:
        """
        按名称查找工具

        参数：
            name: 工具名称

        返回值：
            Tool 实例，未找到返回 None
        """
        return self._tools.get(name)

    def get_all(self) -> list[BaseTool]:
        """
        获取所有已注册的工具实例

        返回值：
            BaseTool 实例列表
        """
        return list(self._tools.values())

    def get_all_langchain_tools(self) -> list:
        """
        获取所有已注册工具的 LangChain 版本

        返回值：
            LangChain BaseTool 列表，可直接传给 Agent

        用法：
            tools = registry.get_all_langchain_tools()
            agent = create_react_agent(llm, tools, prompt)
        """
        return [tool.to_langchain_tool() for tool in self._tools.values()]

    def get_tool_names(self) -> list[str]:
        """
        获取所有已注册工具的名称列表

        用于日志输出和调试
        """
        return list(self._tools.keys())

    def size(self) -> int:
        """已注册工具数量"""
        return len(self._tools)

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={self.get_tool_names()}>"


# =============================================================================
# 全局单例 — 全项目唯一的工具注册中心
# =============================================================================

tool_registry = ToolRegistry()


# =============================================================================
# 注册所有工具（新增工具时在此函数中添加一行即可）
# =============================================================================

def _register_all():
    """
    一次性注册所有可用工具

    新增工具时：
      1. from app.tools.new_tool import NewTool
      2. tool_registry.register(NewTool())
    """
    # 核心工具
    tool_registry.register(WeatherTool())
    tool_registry.register(DateParserTool())
    tool_registry.register(CityResolverTool())
    tool_registry.register(RoutePlannerTool())
    tool_registry.register(CalculatorTool())
    # 路径规划前置依赖工具
    tool_registry.register(IPLocationTool())
    tool_registry.register(GeocodingTool())

    logger.info(f"工具注册完成 | 共 {tool_registry.size()} 个工具 | {tool_registry.get_tool_names()}")


# 模块加载时自动注册所有工具
_register_all()
