"""
=============================================================================
路线规划工具 — 根据起点终点提供出行建议
=============================================================================
职责：
  1. 接收起点、终点、出行方式（驾车/公交/步行）
  2. 返回距离、预计耗时、简要路线描述
  3. 结合天气给出出行建议

当前状态：
  使用模拟数据。
  接入高德路线规划 API 时：
    1. 使用 settings.AMAP_API_KEY 获取 Key
    2. 调用 https://restapi.amap.com/v3/direction/driving 等接口
    3. 替换 _get_mock_route 方法即可
=============================================================================
"""

from typing import Any

from app.tools.base import BaseTool
from app.utils.logger import logger


class RoutePlannerTool(BaseTool):
    """
    路线规划工具

    根据起点和终点规划出行路线，返回距离、耗时和出行建议。
    """

    @property
    def name(self) -> str:
        return "route_planner"

    @property
    def description(self) -> str:
        return (
            "根据起点和终点规划出行路线。返回距离、预计耗时和出行方式建议。"
            "参数：origin（起点），destination（终点），"
            "travel_mode（出行方式，可选，driving/walking/transit，默认driving）"
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "出发地点，如 '北京天安门'、'上海浦东机场'",
                },
                "destination": {
                    "type": "string",
                    "description": "目的地，如 '北京故宫'、'上海外滩'",
                },
                "travel_mode": {
                    "type": "string",
                    "enum": ["driving", "walking", "transit"],
                    "description": "出行方式：driving（驾车）、walking（步行）、transit（公交/地铁）",
                },
            },
            "required": ["origin", "destination"],
        }

    async def _execute(
        self,
        origin: str,
        destination: str,
        travel_mode: str = "driving",
        **kwargs: Any,
    ) -> dict:
        """
        执行路线规划

        参数：
            origin:      起点
            destination: 终点
            travel_mode: 出行方式
        """
        logger.info(
            f"路线规划 | 起点={origin} | 终点={destination} | 方式={travel_mode}"
        )

        # ---- 模拟路线数据 ----
        route_data = self._get_mock_route(origin, destination, travel_mode)

        # ---- 生成出行建议 ----
        suggestions = self._generate_suggestions(route_data, travel_mode)

        summary = (
            f"从 {origin} 到 {destination}，"
            f"建议{self._mode_name(travel_mode)}出行，"
            f"距离约 {route_data['distance_km']} 公里，"
            f"预计耗时 {route_data['duration_min']} 分钟。"
            f"{suggestions}"
        )

        return {
            "success": True,
            "result": route_data,
            "error": None,
            "summary": summary,
        }

    def _get_mock_route(self, origin: str, destination: str, mode: str) -> dict:
        """
        生成模拟路线数据

        真实接入高德/百度 API 时替换此方法。
        """
        import hashlib

        # 根据起终点生成稳定的随机数据
        key = f"{origin}→{destination}"
        seed = int(hashlib.md5(key.encode()).hexdigest()[:4], 16)

        distance_km = round((seed % 30) + 1 + (seed % 100) / 100, 1)

        if mode == "walking":
            speed = 5  # 步行 5 km/h
        elif mode == "transit":
            speed = 25  # 公交/地铁约 25 km/h（含等待时间）
        else:
            speed = 40  # 驾车 40 km/h（城市道路）

        duration_min = max(5, int(distance_km / speed * 60))

        # 模拟途经主要道路
        roads = ["主干道", "快速路", "环路", "高速"]
        route_desc = f"途经{roads[seed % 4]}，路况{'畅通' if seed % 3 == 0 else ('缓行' if seed % 3 == 1 else '拥堵')}"

        return {
            "distance_km": distance_km,
            "duration_min": duration_min,
            "travel_mode": mode,
            "route_description": route_desc,
            "origin": origin,
            "destination": destination,
        }

    def _generate_suggestions(self, route_data: dict, mode: str) -> str:
        """
        根据路线数据生成出行建议
        """
        suggestions = []

        dist = route_data["distance_km"]
        duration = route_data["duration_min"]

        if dist > 10 and mode == "walking":
            suggestions.append("距离较远，不建议步行，可考虑驾车或公交出行")
        if duration > 60:
            suggestions.append("行程较长，建议携带饮用水，提前出发")
        if "拥堵" in route_data.get("route_description", ""):
            suggestions.append("当前路况拥堵，建议预留额外时间")

        return "。".join(suggestions) + "。" if suggestions else ""

    def _mode_name(self, mode: str) -> str:
        """出行方式中文名"""
        return {"driving": "驾车", "walking": "步行", "transit": "公交/地铁"}.get(
            mode, mode
        )

    def validate_input(self, origin: str, destination: str, **kwargs: Any) -> None:
        """参数校验"""
        if not origin or not origin.strip():
            raise ValueError("起点不能为空")
        if not destination or not destination.strip():
            raise ValueError("终点不能为空")
