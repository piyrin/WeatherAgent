"""
=============================================================================
地理编码工具 — 调用高德地理/逆地理编码 API
=============================================================================
职责：
  1. 地理编码：结构化地址 → 经纬度坐标
  2. 逆地理编码：经纬度坐标 → 结构化地址 + 周边 POI/AOI

API 说明：
  - 地理编码 URL：https://restapi.amap.com/v3/geocode/geo
    参数：key（必填）、address（必填）、city（可选）
  - 逆地理编码 URL：https://restapi.amap.com/v3/geocode/regeo
    参数：key（必填）、location（必填）、extensions（可选 base/all）

结构化地址格式（address 参数）：
  遵循层级：国家 → 省份 → 城市 → 区县 → 城镇 → 乡村 → 街道 → 门牌号码 → 屋邨 → 大厦
  - 大陆/港/澳：可省略国家，但省、市、区县级不能省略
  - 示例：北京市朝阳区阜通东大街6号
  - 不支持台湾省的详细地址信息
  - 地标建筑/景区名称也可直接传入（如：天安门、武汉大学）

如果用户只给了模糊地址（如"天安门"、"武汉大学"），直接传入即可。
如果用户给了非结构化的自然语言描述，Agent（LLM）应尽量将其整理为结构化格式再传入。

依赖链中的位置：
  - 路径规划的前置步骤：用户输入地名 → 地理编码 → 得到坐标 → 传给路径规划
  - 逆地理编码：路径规划返回坐标 → 逆地理编码 → 获取可读地址信息

统一返回格式：
  地理编码成功: {"success": true, "result": {"location": "116.48,39.99",
                "formatted_address": "...", "adcode": "...", "level": "..."}}
  逆地理编码成功: {"success": true, "result": {"formatted_address": "...",
                  "adcode": "...", "addressComponent": {...}, "pois": [...]}}

使用示例（地理编码）：
    tool = GeocodingTool()
    # 结构化地址
    result = await tool.run(address="北京市朝阳区阜通东大街6号")
    # 地标名称（也支持，但结构化地址更精准）
    result = await tool.run(address="天安门", city="北京")
    # → {"location": "116.397499,39.908722", ...}

使用示例（逆地理编码）：
    result = await tool.run(location="116.397499,39.908722")
    # → {"formatted_address": "北京市东城区...", ...}
=============================================================================
"""

from typing import Any

import requests

from app.core.config import settings
from app.tools.base import BaseTool
from app.utils.logger import logger


class GeocodingTool(BaseTool):
    """
    地理编码工具

    支持两种模式：
      - geo（默认）：地址 → 坐标（地理编码）
      - regeo：坐标 → 地址（逆地理编码）

    根据传入参数自动判断模式：
      - 传 address → 地理编码
      - 传 location → 逆地理编码
    """

    @property
    def name(self) -> str:
        return "geocoding"

    @property
    def description(self) -> str:
        return (
            "地理编码/逆地理编码工具，提供地址与经纬度坐标之间的相互转化。"
            "地理编码（地址→坐标）：将结构化地址转换为经纬度坐标。"
            "地址必须遵循层级格式：国家、省份、城市、区县、城镇、乡村、街道、门牌号码、屋邨、大厦。"
            "大陆/港/澳可省略国家，但省、市、区县级不能省略。"
            "示例：'北京市朝阳区阜通东大街6号'。地标建筑如'天安门'也可直接传入。"
            "逆地理编码（坐标→地址）：将经纬度转换为详细的结构化地址，"
            "并可获取周边的 POI、AOI 信息。"
            "参数："
            "address（结构化地址或地标名称，地理编码时必填。尽量按省+市+区+街道层级拼接）、"
            "city（限定城市，可选，用于缩小搜索范围，提高准确率）、"
            "location（经纬度坐标，逆地理编码时必填，格式 lng,lat）"
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": (
                        "结构化地址信息，遵循层级格式：国家、省份、城市、区县、城镇、"
                        "乡村、街道、门牌号码、屋邨、大厦。"
                        "大陆/港/澳可省略国家，但省、市、区县级不能省略。"
                        "如：'北京市朝阳区阜通东大街6号'。"
                        "地标性建筑、景区名称也可直接传入，如：'天安门'、'武汉大学'。"
                        "注意：不支持台湾省的详细地址信息。"
                    ),
                },
                "city": {
                    "type": "string",
                    "description": (
                        "限定查询城市，可选。可输入城市中文名、中文全拼、citycode、adcode。"
                        "如：'北京'、'beijing'、'010'、'110000'。"
                        "指定后优先在该城市范围内搜索，提高准确率。"
                    ),
                },
                "location": {
                    "type": "string",
                    "description": (
                        "经纬度坐标（逆地理编码模式），经度在前纬度在后，逗号分隔。"
                        "如：'116.480881,39.989410'"
                    ),
                },
            },
            "required": [],
        }

    async def _execute(
        self,
        address: str = "",
        city: str = "",
        location: str = "",
        **kwargs: Any,
    ) -> dict:
        """
        执行地理编码或逆地理编码

        参数：
            address:  地址或地标名称（地理编码）
            city:     限定城市（可选，地理编码时使用）
            location: 经纬度坐标（逆地理编码）

        返回值：
            统一格式的编码结果 dict
        """
        # ---- 自动判断模式 ----
        if location and location.strip():
            return await self._regeo(location.strip())
        elif address and address.strip():
            return await self._geo(address.strip(), city.strip() if city else "")
        else:
            return {
                "success": False,
                "result": None,
                "error": "参数缺失",
                "message": "请提供 address（地理编码）或 location（逆地理编码）参数",
                "summary": "地理编码失败：缺少 address 或 location 参数",
                "raw": {},
            }

    # =========================================================================
    # 地理编码（地址 → 坐标）
    # =========================================================================

    async def _geo(self, address: str, city: str = "") -> dict:
        """
        地理编码：地址 → 经纬度

        参数：
            address: 地址或地标名称
            city:    限定城市（可选）
        """
        logger.info(
            f"[geocoding] 地理编码 | address={address!r} | city={city or '(不限)'}"
        )

        api_key = settings.AMAP_API_KEY
        if not api_key:
            return self._build_error(
                error="AMAP_API_KEY 未配置",
                message="请在 .env 文件中配置 AMAP_API_KEY",
            )

        url = f"{settings.AMAP_BASE_URL}/v3/geocode/geo"
        params: dict[str, str] = {
            "key": api_key,
            "address": address,
            "output": "JSON",
        }
        if city:
            params["city"] = city

        try:
            resp = requests.get(url, params=params, timeout=10)
        except requests.Timeout:
            return self._build_error(
                error="API_TIMEOUT",
                message="高德地理编码 API 请求超时",
            )
        except requests.ConnectionError as exc:
            return self._build_error(
                error=f"ConnectionError: {exc}",
                message="无法连接到高德地理编码 API",
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

        if data.get("status") != "1":
            info = data.get("info", "未知错误")
            return self._build_error(
                error=f"AMapError: {info}",
                message=f"高德地理编码 API 返回错误: {info}",
                raw=data,
            )

        # ---- 解析结果 ----
        geocodes = data.get("geocodes", [])
        if not geocodes:
            logger.warning(f"[geocoding] 未找到地址的坐标 | address={address!r}")
            return {
                "success": False,
                "result": None,
                "error": "GEOCODE_NOT_FOUND",
                "message": f"未找到地址 '{address}' 的坐标信息",
                "summary": f"地理编码失败：未找到 '{address}' 的坐标信息，请检查地址是否正确。",
                "raw": data,
            }

        # 取第一个结果（最匹配）
        best = geocodes[0]
        location = best.get("location", "")
        formatted_address = best.get("formatted_address", "")
        adcode = best.get("adcode", "")
        level = best.get("level", "")
        country = best.get("country", "")
        province = best.get("province", "")
        city_name = best.get("city", "")
        district = best.get("district", "")
        township = best.get("township", [])

        # township 可能是列表或字符串
        township_str = ""
        if isinstance(township, list):
            township_str = township[0] if township else ""
        elif isinstance(township, str):
            township_str = township

        count = len(geocodes)
        logger.info(
            f"[geocoding] 地理编码成功 | address={address!r} → "
            f"location={location} | level={level} | 返回{count}条结果"
        )

        summary = (
            f"地理编码成功：'{address}' → 坐标 {location}（{level}）"
            f" | {formatted_address}"
        )

        return {
            "success": True,
            "result": {
                "location": location,
                "formatted_address": formatted_address,
                "country": country,
                "province": province,
                "city": city_name,
                "district": district,
                "township": township_str,
                "adcode": adcode,
                "level": level,
                "count": count,
            },
            "error": None,
            "summary": summary,
            "raw": data,
        }

    # =========================================================================
    # 逆地理编码（坐标 → 地址）
    # =========================================================================

    async def _regeo(self, location: str) -> dict:
        """
        逆地理编码：经纬度 → 地址

        参数：
            location: 经纬度坐标，格式 lng,lat
        """
        logger.info(f"[geocoding] 逆地理编码 | location={location!r}")

        api_key = settings.AMAP_API_KEY
        if not api_key:
            return self._build_error(
                error="AMAP_API_KEY 未配置",
                message="请在 .env 文件中配置 AMAP_API_KEY",
            )

        url = f"{settings.AMAP_BASE_URL}/v3/geocode/regeo"
        params: dict[str, str] = {
            "key": api_key,
            "location": location,
            "extensions": "all",  # 返回完整信息（地址+POI+AOI+道路）
            "output": "JSON",
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
        except requests.Timeout:
            return self._build_error(
                error="API_TIMEOUT",
                message="高德逆地理编码 API 请求超时",
            )
        except requests.ConnectionError as exc:
            return self._build_error(
                error=f"ConnectionError: {exc}",
                message="无法连接到高德逆地理编码 API",
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

        if data.get("status") != "1":
            info = data.get("info", "未知错误")
            return self._build_error(
                error=f"AMapError: {info}",
                message=f"高德逆地理编码 API 返回错误: {info}",
                raw=data,
            )

        # ---- 解析结果 ----
        regeocode = data.get("regeocode", {})
        formatted_address = regeocode.get("formatted_address", "")
        address_component = regeocode.get("addressComponent", {})
        pois = regeocode.get("pois", [])
        roads = regeocode.get("roads", [])
        aois = regeocode.get("aois", [])

        adcode = address_component.get("adcode", "")
        city_name = address_component.get("city", "") or address_component.get("province", "")

        logger.info(
            f"[geocoding] 逆地理编码成功 | location={location!r} → "
            f"address={formatted_address[:50]} | "
            f"POIs={len(pois)} | roads={len(roads)}"
        )

        # 构建附近 POI 摘要
        nearby_summary = ""
        if pois:
            nearby_poi_names = [
                p.get("name", "") for p in pois[:5] if p.get("name")
            ]
            if nearby_poi_names:
                nearby_summary = f" 附近设施：{'、'.join(nearby_poi_names)}"

        summary = (
            f"逆地理编码成功：坐标 {location} → {formatted_address}。"
            f"{nearby_summary}"
        )

        return {
            "success": True,
            "result": {
                "location": location,
                "formatted_address": formatted_address,
                "addressComponent": address_component,
                "adcode": adcode,
                "city": city_name,
                "pois": pois,
                "roads": roads,
                "aois": aois,
            },
            "error": None,
            "summary": summary,
            "raw": data,
        }

    # =========================================================================
    # 辅助方法
    # =========================================================================

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
            "summary": f"地理编码失败: {message}",
            "raw": raw or {},
        }

    def validate_input(self, address: str = "", city: str = "", location: str = "", **kwargs: Any) -> None:
        """参数校验"""
        if not address and not location:
            raise ValueError("地理编码需要 address 参数，逆地理编码需要 location 参数")
        if location and address:
            raise ValueError("address 和 location 不能同时传入，请选择一种模式")
