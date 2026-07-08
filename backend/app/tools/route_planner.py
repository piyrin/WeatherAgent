"""
=============================================================================
路线规划工具 — 调用高德路径规划 API 获取真实路线数据
=============================================================================
职责：
  1. 接收起点、终点（经纬度坐标或地名）、出行方式（驾车/公交/步行）
  2. 调用高德路径规划 API：driving / transit / walking
  3. 返回距离、耗时、路线坐标串（polyline）、打车费用等结构化数据

API 说明：
  - 驾车：https://restapi.amap.com/v3/direction/driving
  - 公交：https://restapi.amap.com/v3/direction/transit/integrated
  - 步行：https://restapi.amap.com/v3/direction/walking
  - origin/destination 格式：lng,lat（经度在前，小数点不超过6位）
  - 公交必填 city（起点城市），跨城必填 cityd
  - extensions=all 才返回 polyline（路线坐标串），用于前端地图绘制

依赖链：
  地理编码（geocoding）→ 得到经纬度 → 传给本工具
  若传入地名而非经纬度，本工具会自动调用 geocoding 转换

统一返回格式：
  成功: {"success": true, "result": {"distance": ..., "duration": ...,
         "polyline": "lng,lat;lng,lat;...", "origin_coord": ...,
         "destination_coord": ..., "travel_mode": ..., "taxi_cost": ...},
         "summary": "...", "raw": {...}}
  失败: {"success": false, "error": "...", "message": "...", "raw": {...}}

使用示例：
    tool = RoutePlannerTool()
    # 传经纬度（推荐，由 geocoding 转换后传入）
    result = await tool.run(
        origin="114.3535,30.5478", destination="114.3052,30.5928",
        travel_mode="transit", city="武汉"
    )
    # 传地名（自动调 geocoding 转换）
    result = await tool.run(
        origin="武汉大学", destination="武汉站", travel_mode="driving"
    )
=============================================================================
"""

import re
from typing import Any

import requests

from app.core.config import settings
from app.tools.base import BaseTool
from app.utils.logger import logger


# 经纬度坐标正则：lng,lat（经度 2-3 位整数+小数，纬度 1-2 位整数+小数，小数最多6位）
_COORD_PATTERN = re.compile(r"^\d{2,3}\.\d{1,6},\d{1,2}\.\d{1,6}$")


class RoutePlannerTool(BaseTool):
    """
    路线规划工具

    调用高德路径规划 API，根据起终点规划出行路线。
    支持驾车（driving）、公交/地铁（transit）、步行（walking）三种方式。
    起终点可传经纬度坐标（lng,lat）或地名（自动调用 geocoding 转换）。
    """

    @property
    def name(self) -> str:
        return "route_planner"

    @property
    def description(self) -> str:
        return (
            "根据起点和终点规划出行路线，返回距离、耗时、路线坐标串（polyline）等详细数据。"
            "支持三种出行方式：driving（驾车）、transit（公交/地铁）、walking（步行）。"
            "参数："
            "origin（起点，可传经纬度坐标 lng,lat 或地名。推荐先用 geocoding 转换为坐标后传入）、"
            "destination（终点，格式同 origin）、"
            "travel_mode（出行方式，可选，默认 driving）、"
            "city（起点城市，公交模式 transit 必填，可传城市名或 adcode）、"
            "cityd（终点城市，跨城公交可选）。"
            "返回结果包含 distance（米）、duration（秒）、polyline（路线坐标串，可用于地图绘制）、"
            "taxi_cost（打车费用，驾车/公交有）。"
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": (
                        "出发地点。可传经纬度坐标（lng,lat 格式，如 '114.3535,30.5478'），"
                        "也可传地名（如 '武汉大学'）。推荐先用 geocoding 工具获取坐标后传入，更精准。"
                    ),
                },
                "destination": {
                    "type": "string",
                    "description": (
                        "目的地。格式同 origin，可传经纬度坐标或地名。"
                    ),
                },
                "travel_mode": {
                    "type": "string",
                    "enum": ["driving", "walking", "transit"],
                    "description": (
                        "出行方式：driving（驾车，默认）、walking（步行）、transit（公交/地铁）。"
                        "用户说'坐地铁/公交/坐车'→transit；'开车/驾车/自驾'→driving；'走路/步行'→walking。"
                    ),
                },
                "city": {
                    "type": "string",
                    "description": (
                        "起点城市（公交模式 transit 必填）。可传城市名（如 '武汉'）或 adcode。"
                        "驾车和步行模式不需要。"
                    ),
                },
                "cityd": {
                    "type": "string",
                    "description": "终点城市（跨城公交可选）。市内公交可不传。",
                },
            },
            "required": ["origin", "destination"],
        }

    async def _execute(
        self,
        origin: str,
        destination: str,
        travel_mode: str = "driving",
        city: str = "",
        cityd: str = "",
        **kwargs: Any,
    ) -> dict:
        """
        执行路线规划

        参数：
            origin:      起点（经纬度或地名）
            destination: 终点（经纬度或地名）
            travel_mode: 出行方式 driving/walking/transit
            city:        起点城市（公交必填）
            cityd:       终点城市（跨城公交可选）
        """
        logger.info(
            f"[route_planner] 路线规划 | 起点={origin!r} | 终点={destination!r} | "
            f"方式={travel_mode} | city={city or '(无)'}"
        )

        # ---- 参数规范化 ----
        if travel_mode not in ("driving", "walking", "transit"):
            travel_mode = "driving"

        # ---- 确保 origin/destination 是经纬度坐标 ----
        origin_coord = await self._ensure_coordinate(origin, "起点")
        if origin_coord is None:
            return self._build_error(
                error="ORIGIN_RESOLVE_FAILED",
                message=f"无法解析起点 '{origin}' 的经纬度坐标",
            )

        destination_coord = await self._ensure_coordinate(destination, "终点")
        if destination_coord is None:
            return self._build_error(
                error="DESTINATION_RESOLVE_FAILED",
                message=f"无法解析终点 '{destination}' 的经纬度坐标",
            )

        # ---- 公交模式必须提供 city ----
        if travel_mode == "transit" and not city:
            logger.warning(
                "[route_planner] 公交模式未提供 city 参数，可能导致规划失败"
            )

        # ---- 调用高德路径规划 API ----
        try:
            api_result = await self._call_amap_direction(
                origin_coord, destination_coord, travel_mode, city, cityd
            )
            return api_result
        except Exception as exc:
            logger.error(
                f"[route_planner] API 调用异常 | {type(exc).__name__}: {exc}"
            )
            return self._build_error(
                error=f"APIException: {str(exc)}",
                message=f"调用高德路径规划 API 失败：{str(exc)}",
            )

    # =========================================================================
    # 坐标解析（地名 → 经纬度）
    # =========================================================================

    def _is_coordinate(self, text: str) -> bool:
        """判断字符串是否为经纬度坐标格式（lng,lat）"""
        if not text:
            return False
        return bool(_COORD_PATTERN.match(text.strip()))

    async def _ensure_coordinate(self, text: str, label: str) -> str | None:
        """
        确保拿到经纬度坐标（lng,lat）。

        - 如果已是坐标格式 → 直接返回
        - 如果是地名 → 调用 geocoding 工具转换

        返回值：经纬度坐标字符串，失败返回 None
        """
        if not text or not text.strip():
            return None

        text = text.strip()

        # 已是坐标格式
        if self._is_coordinate(text):
            return text

        # 当作地名 → 调用 geocoding
        logger.info(f"[route_planner] {label}='{text}' 不是坐标，调用 geocoding 转换")
        try:
            from app.tools.geocoding import GeocodingTool

            geocoder = GeocodingTool()
            result = await geocoder.run(address=text)

            if result.get("success") and result.get("result"):
                location = result["result"].get("location", "")
                if location and self._is_coordinate(location):
                    logger.info(
                        f"[route_planner] {label}地理编码成功 | {text!r} → {location}"
                    )
                    return location

            logger.warning(
                f"[route_planner] {label}地理编码失败 | {text!r} | "
                f"result={result.get('summary', 'N/A')}"
            )
            return None
        except Exception as exc:
            logger.error(
                f"[route_planner] {label}地理编码异常 | {text!r} | "
                f"{type(exc).__name__}: {exc}"
            )
            return None

    # =========================================================================
    # 调用高德路径规划 API
    # =========================================================================

    async def _call_amap_direction(
        self,
        origin: str,
        destination: str,
        travel_mode: str,
        city: str,
        cityd: str,
    ) -> dict:
        """
        调用高德路径规划 API

        参数：
            origin:      起点坐标 lng,lat
            destination: 终点坐标 lng,lat
            travel_mode: driving/walking/transit
            city:        起点城市（公交用）
            cityd:       终点城市（跨城公交用）
        """
        api_key = settings.AMAP_API_KEY
        if not api_key:
            return self._build_error(
                error="AMAP_API_KEY 未配置",
                message="请在 .env 文件中配置 AMAP_API_KEY",
            )

        url = settings.amap_direction_url(travel_mode)

        params: dict[str, str] = {
            "key": api_key,
            "origin": origin,
            "destination": destination,
            "output": "JSON",
        }

        # 驾车和公交需要 extensions=all 才返回 polyline
        if travel_mode == "driving":
            params["extensions"] = "all"
            # 策略 10：躲避拥堵，路程较短，尽量缩短时间（返回多条路径，与高德地图默认一致）
            params.setdefault("strategy", "10")
        elif travel_mode == "transit":
            params["extensions"] = "all"
            # 公交换乘策略 0：最快捷模式
            params.setdefault("strategy", "0")
            if city:
                params["city"] = city
            if cityd:
                params["cityd"] = cityd
        # walking 默认返回 steps（含 polyline），无需 extensions

        logger.info(
            f"[route_planner] 请求高德路径规划 API | mode={travel_mode} | "
            f"origin={origin} | destination={destination} | url={url}"
        )

        try:
            resp = requests.get(url, params=params, timeout=15)
        except requests.Timeout:
            return self._build_error(
                error="API_TIMEOUT",
                message="高德路径规划 API 请求超时",
            )
        except requests.ConnectionError as exc:
            return self._build_error(
                error=f"ConnectionError: {exc}",
                message="无法连接到高德路径规划 API",
            )

        logger.debug(
            f"[route_planner] 高德响应 | status={resp.status_code} | "
            f"body_len={len(resp.text)}"
        )

        if resp.status_code != 200:
            return self._build_error(
                error=f"HTTP {resp.status_code}",
                message=f"高德 API 返回 HTTP {resp.status_code}",
                raw={"status_code": resp.status_code, "body": resp.text[:500]},
            )

        try:
            data = resp.json()
        except Exception as exc:
            return self._build_error(
                error=f"JSONDecodeError: {exc}",
                message="高德 API 返回了非 JSON 格式的数据",
                raw={"body": resp.text[:500]},
            )

        # 检查 API 返回状态
        if data.get("status") != "1":
            info = data.get("info", "未知错误")
            infocode = data.get("infocode", "")
            return self._build_error(
                error=f"AMapError({infocode}): {info}",
                message=f"高德路径规划 API 返回错误: {info}",
                raw=data,
            )

        # ---- 按出行方式解析结果 ----
        route = data.get("route", {})
        if not route:
            return self._build_error(
                error="NoRouteData",
                message="高德 API 未返回路线数据",
                raw=data,
            )

        if travel_mode == "transit":
            return self._parse_transit(route, origin, destination, travel_mode, data)
        else:
            return self._parse_driving_walking(
                route, origin, destination, travel_mode, data
            )

    # =========================================================================
    # 结果解析
    # =========================================================================

    def _parse_driving_walking(
        self, route: dict, origin: str, destination: str, mode: str, raw: dict
    ) -> dict:
        """
        解析驾车/步行路线结果

        高德返回结构：route.paths[0].{distance, duration, steps[].polyline, taxi_cost}
        """
        paths = route.get("paths", [])
        if not paths:
            return self._build_error(
                error="NoPathData",
                message=f"未找到{self._mode_name(mode)}路线方案",
                raw=raw,
            )

        # 取第一条路径（最优方案）
        path = paths[0]
        distance_m = int(path.get("distance", 0))  # 米
        duration_s = int(path.get("duration", 0))  # 秒

        # 拼接所有 step 的 polyline 形成完整路线
        steps = path.get("steps", [])
        polyline = self._merge_step_polylines(steps)

        # 驾车特有字段
        taxi_cost = ""
        tolls = ""
        if mode == "driving":
            taxi_cost = path.get("taxi_cost", "")  # 打车费用（元），extensions=all 时返回
            tolls = path.get("tolls", "")  # 道路收费（元）

        result = {
            "travel_mode": mode,
            "origin": origin,
            "destination": destination,
            "origin_coord": origin,
            "destination_coord": destination,
            "distance": distance_m,                     # 距离（米）
            "distance_km": round(distance_m / 1000, 2), # 距离（公里）
            "duration": duration_s,                     # 耗时（秒）
            "duration_min": max(1, round(duration_s / 60)),  # 耗时（分钟）
            "polyline": polyline,                       # 完整路线坐标串 lng,lat;lng,lat;...
            "steps_count": len(steps),                  # 路段数
            "taxi_cost": taxi_cost,                     # 打车费用
            "tolls": tolls,                             # 道路收费
            "route_count": len(paths),                  # 备选路线数
        }

        summary = self._build_summary(result, mode)
        point_count = polyline.count(";") + 1 if polyline else 0
        logger.info(
            f"[route_planner] {self._mode_name(mode)}路线规划成功 | "
            f"距离={result['distance_km']}km | 耗时={result['duration_min']}分钟 | "
            f"路线点数={point_count}"
        )

        return {
            "success": True,
            "result": result,
            "error": None,
            "summary": summary,
            "raw": raw,
        }

    def _parse_transit(
        self, route: dict, origin: str, destination: str, mode: str, raw: dict
    ) -> dict:
        """
        解析公交/地铁路线结果

        高德返回结构：
          route.distance: 起终点直线距离（米）
          route.taxi_cost: 打车费用（元）
          route.transits[0].{duration, distance, walking_distance,
                            segments[].{walking.steps[].polyline, bus.buslines[].polyline}}
        """
        transits = route.get("transits", [])
        if not transits:
            return self._build_error(
                error="NoTransitData",
                message="未找到公交/地铁路线方案",
                raw=raw,
            )

        # 取第一个换乘方案（最快捷）
        transit = transits[0]
        duration_s = int(transit.get("duration", 0))  # 秒
        distance_m = int(route.get("distance", 0))  # 起终点距离（米）
        walking_distance_m = int(transit.get("walking_distance", 0))  # 步行距离（米）
        taxi_cost = route.get("taxi_cost", "")  # 打车费用（元）

        # 拼接所有 segment 的 polyline（步行段 + 公交段）
        segments = transit.get("segments", [])
        polyline = self._merge_transit_polylines(segments)

        # 统计换乘段信息
        bus_segments = [s for s in segments if s.get("bus", {}).get("buslines")]
        bus_count = len(bus_segments)
        walk_count = sum(1 for s in segments if s.get("walking", {}).get("steps"))

        # 提取详细换乘方案（供 answer 节点生成"坐几号线转几号线"的文字说明）
        transit_detail = self._extract_transit_detail(segments)

        result = {
            "travel_mode": mode,
            "origin": origin,
            "destination": destination,
            "origin_coord": origin,
            "destination_coord": destination,
            "distance": distance_m,
            "distance_km": round(distance_m / 1000, 2),
            "duration": duration_s,
            "duration_min": max(1, round(duration_s / 60)),
            "walking_distance": walking_distance_m,              # 步行距离（米）
            "walking_distance_km": round(walking_distance_m / 1000, 2),
            "polyline": polyline,
            "segments_count": len(segments),                     # 总段数
            "bus_count": bus_count,                              # 公交/地铁段数
            "walk_count": walk_count,                            # 步行段数
            "transit_detail": transit_detail,                    # 详细换乘方案列表
            "taxi_cost": taxi_cost,
            "route_count": len(transits),                        # 备选方案数
        }

        summary = self._build_summary(result, mode)
        point_count = polyline.count(";") + 1 if polyline else 0
        logger.info(
            f"[route_planner] 公交路线规划成功 | "
            f"耗时={result['duration_min']}分钟 | 换乘段={bus_count} | "
            f"步行={result['walking_distance_km']}km | 路线点数={point_count}"
        )

        return {
            "success": True,
            "result": result,
            "error": None,
            "summary": summary,
            "raw": raw,
        }

    # =========================================================================
    # Polyline 提取与合并
    # =========================================================================

    def _merge_step_polylines(self, steps: list[dict]) -> str:
        """
        合并驾车/步行各路段的 polyline 为完整路线坐标串

        高德每个 step 的 polyline 格式："lng,lat;lng,lat;..."
        合并时去重相邻段的连接点（前一段末尾 == 后一段开头）

        返回值："lng,lat;lng,lat;..." 完整坐标串
        """
        all_points: list[str] = []
        for step in steps:
            poly = step.get("polyline", "")
            if not poly:
                continue
            points = [p.strip() for p in poly.split(";") if p.strip()]
            if not points:
                continue
            # 去重：若当前段首点与上一段末点相同，跳过
            if all_points and all_points[-1] == points[0]:
                points = points[1:]
            all_points.extend(points)

        return ";".join(all_points)

    def _merge_transit_polylines(self, segments: list[dict]) -> str:
        """
        合并公交换乘各段的 polyline（步行段 + 公交段）

        每个 segment 结构：
          - walking.steps[].polyline  （步行段坐标）
          - bus.buslines[].polyline   （公交/地铁段坐标）

        返回值：完整坐标串
        """
        all_points: list[str] = []

        def _add_points(poly: str):
            if not poly:
                return
            points = [p.strip() for p in poly.split(";") if p.strip()]
            if not points:
                return
            if all_points and all_points[-1] == points[0]:
                points = points[1:]
            all_points.extend(points)

        for seg in segments:
            # 步行段
            walking = seg.get("walking", {})
            for w_step in walking.get("steps", []):
                _add_points(w_step.get("polyline", ""))

            # 公交/地铁段
            bus = seg.get("bus", {})
            for busline in bus.get("buslines", []):
                _add_points(busline.get("polyline", ""))

        return ";".join(all_points)

    def _extract_transit_detail(self, segments: list[dict]) -> list[dict]:
        """
        提取公交/地铁换乘的详细方案，供 answer 节点生成换乘文字说明

        返回值：换乘段列表，每段含类型、线路名、上下车站、途经站数等
        """
        detail = []
        for seg in segments:
            # 公交/地铁段
            bus = seg.get("bus", {})
            buslines = bus.get("buslines", [])
            if buslines:
                bl = buslines[0]
                # 途经站点名列表（高德 via_stops: [{name, id, location}, ...]）
                via_stops_raw = bl.get("via_stops", [])
                via_stops = [v.get("name", "") for v in via_stops_raw if v.get("name")]
                detail.append({
                    "type": "bus",
                    "line_name": bl.get("name", ""),
                    "departure_stop": bl.get("departure_stop", {}).get("name", ""),
                    "arrival_stop": bl.get("arrival_stop", {}).get("name", ""),
                    "via_num": bl.get("via_num", ""),
                    "via_stops": via_stops,
                    "distance_m": self._safe_int(bl.get("distance")),
                    "duration_s": self._safe_int(bl.get("duration")),
                })
            # 步行段
            walking = seg.get("walking", {})
            w_dist = self._safe_int(walking.get("distance"))
            if w_dist > 0:
                detail.append({
                    "type": "walk",
                    "distance_m": w_dist,
                    "duration_s": self._safe_int(walking.get("duration")),
                })
        return detail

    @staticmethod
    def _safe_int(value) -> int:
        """安全转 int（高德返回值可能是字符串或数字）"""
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def _build_summary(self, result: dict, mode: str) -> str:
        """构建人类可读的路线摘要"""
        mode_name = self._mode_name(mode)
        parts = [
            f"从起点到终点，{mode_name}距离约 {result['distance_km']} 公里，"
            f"预计耗时 {result['duration_min']} 分钟"
        ]

        if mode == "transit":
            parts.append(
                f"共 {result.get('bus_count', 0)} 段公交/地铁，"
                f"步行约 {result.get('walking_distance_km', 0)} 公里"
            )
            # 详细换乘方案：乘 X号线（A站→B站）途经N站 → 换乘 Y号线...
            detail = result.get("transit_detail", [])
            if detail:
                detail_parts = []
                for seg in detail:
                    if seg["type"] == "bus":
                        line = f"乘 {seg['line_name']}（{seg['departure_stop']}→{seg['arrival_stop']}）"
                        # 优先用真实途经站点列表，避免 LLM 编造站点
                        if seg.get("via_stops"):
                            all_stops = [seg["departure_stop"]] + seg["via_stops"] + [seg["arrival_stop"]]
                            line += f"，途经：{'→'.join(all_stops)}"
                        elif seg.get("via_num"):
                            line += f"，{seg['via_num']}"
                        detail_parts.append(line)
                    elif seg["type"] == "walk" and seg.get("distance_m", 0) > 0:
                        detail_parts.append(f"步行{round(seg['distance_m'] / 1000, 2)}公里")
                if detail_parts:
                    parts.append("换乘详情：" + " → ".join(detail_parts))

        if result.get("taxi_cost"):
            parts.append(f"参考打车费用约 {result['taxi_cost']} 元")

        return "，".join(parts) + "。"

    def _mode_name(self, mode: str) -> str:
        """出行方式中文名"""
        return {"driving": "驾车", "walking": "步行", "transit": "公交/地铁"}.get(
            mode, mode
        )

    def _build_error(
        self,
        error: str,
        message: str,
        raw: dict | None = None,
    ) -> dict:
        """构建统一错误格式"""
        return {
            "success": False,
            "result": None,
            "error": error,
            "message": message,
            "summary": f"路线规划失败: {message}",
            "raw": raw or {},
        }

    def validate_input(
        self,
        origin: str,
        destination: str,
        travel_mode: str = "driving",
        city: str = "",
        **kwargs: Any,
    ) -> None:
        """参数校验"""
        if not origin or not origin.strip():
            raise ValueError("起点不能为空")
        if not destination or not destination.strip():
            raise ValueError("终点不能为空")
        if travel_mode and travel_mode not in ("driving", "walking", "transit"):
            raise ValueError(f"不支持的出行方式: {travel_mode}")
