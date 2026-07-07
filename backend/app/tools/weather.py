"""
=============================================================================
天气查询工具 — 调用高德天气 API 获取真实天气数据
=============================================================================
职责：
  1. 接收 adcode（行政区划代码）和日期（可选）
  2. 调用高德地图天气 API：https://restapi.amap.com/v3/weather/weatherInfo
  3. 将 API 返回的结构化数据转为统一格式

API 说明：
  - 基础 URL：https://restapi.amap.com/v3/weather/weatherInfo
  - 参数：
      key        — API Key（从 .env 读取）
      city       — 行政区划 adcode（如 420981），不是城市中文名！
      extensions — base（实况天气）/ all（预报天气，4天）
  - 返回格式：JSON

统一返回格式：
  成功: {"success": true, "city": "...", "adcode": "...", "date": "...",
         "weather": "...", "temperature": "...", "winddirection": "...",
         "windpower": "...", "humidity": "...", "reporttime": "...", "raw": {...}}
  失败: {"success": false, "error": "...", "message": "...", "raw": {...}}

使用示例：
    tool = WeatherTool()
    result = await tool.run(adcode="420981", date="2026-07-08")
=============================================================================
"""

import re
from typing import Any

import requests

from app.core.config import settings
from app.tools.base import BaseTool
from app.utils.logger import logger


class WeatherTool(BaseTool):
    """
    天气查询工具

    调用高德天气 API，根据 adcode 查询指定地区的天气信息。
    必须先通过 city_resolver 将城市名转为 adcode，再调用本工具。
    """

    @property
    def name(self) -> str:
        return "weather"

    @property
    def description(self) -> str:
        return (
            "查询指定行政区划代码（adcode）对应地区的天气信息。"
            "返回温度、天气状况、风力、湿度等信息。支持查询单日天气，也支持从指定日期开始的未来多天预报（高德最多返回4天）。"
            "注意：city 参数必须是 adcode（如 420981），不是城市中文名。"
            "在调用本工具之前，必须先调用 city_resolver 将城市名转换为 adcode。"
            "参数：adcode（行政区划代码，必填），date（日期 YYYY-MM-DD，可选），days（需要返回的天数，1-4，可选）。"
            "如果用户问“未来三天/接下来3天/近几天是否下雨”，应传入 days=3 或相应天数。"
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "adcode": {
                    "type": "string",
                    "description": "行政区划代码（adcode），如 420981。不是城市中文名！必须先通过 city_resolver 转换。",
                },
                "date": {
                    "type": "string",
                    "description": "查询日期，格式 YYYY-MM-DD，如 2026-07-08。不传则查询当天",
                },
                "days": {
                    "type": "integer",
                    "description": "从 date（或今天）开始返回的预报天数，1-4。用于“未来三天/接下来几天”等问题。",
                    "minimum": 1,
                    "maximum": 4,
                },
            },
            "required": ["adcode"],
        }

    async def _execute(
        self,
        adcode: str,
        date: str | None = None,
        days: int | None = None,
        **kwargs: Any,
    ) -> dict:
        """
        执行天气查询

        参数：
            adcode: 行政区划代码（6位数字）。如果传入的不是合法 adcode，
                    自动尝试作为城市中文名调用 CityResolver 解析。
            date: 查询日期（可选）
            days: 预报天数（1-4，可选）

        返回值：
            统一格式的天气数据 dict
        """
        logger.info(
            f"[weather_tool] 查询天气 | adcode={adcode!r} | "
            f"date={date or '今天'} | days={days or 1} | "
            f"extra_kwargs={list(kwargs.keys())}"
        )

        # ---- 自动回退：如果 adcode 不是合法的 6 位数字，尝试城市名解析 ----
        resolved_adcode = await self._ensure_adcode(adcode)
        if resolved_adcode is None:
            # CityResolver 也失败了 → 直接返回错误
            error_msg = (
                f"Weather Tool: 无法解析 adcode 或城市名 '{adcode}'。"
                f"adcode 必须是6位数字（如 420981），或者传合法的城市中文名（如 '应城'）。"
            )
            logger.error(f"[weather_tool] {error_msg}")
            return self._build_error(
                adcode=adcode,
                date=date,
                error="InvalidAdcodeOrCity",
                message=error_msg,
            )

        if resolved_adcode != adcode:
            logger.info(
                f"[weather_tool] 自动解析城市名 → adcode | "
                f"{adcode!r} → {resolved_adcode!r}"
            )

        # ---- 调用高德天气 API ----
        try:
            api_result = await self._call_amap_api(resolved_adcode, date, days)
            return api_result
        except Exception as exc:
            logger.error(
                f"[weather_tool] API 调用异常 | "
                f"adcode={resolved_adcode} | {type(exc).__name__}: {exc}"
            )
            return self._build_error(
                adcode=resolved_adcode,
                date=date,
                error=f"APIException: {str(exc)}",
                message=f"调用高德天气 API 失败：{str(exc)}",
            )

    async def _ensure_adcode(self, adcode: str) -> str | None:
        """
        确保拿到合法的 adcode（6位数字）。异步方法，可被 await 调用。

        逻辑：
          1. 如果已经是合法 adcode → 直接返回
          2. 如果是城市中文名 → 异步调用 CityResolver 转换

        参数：
            adcode: 可能是 adcode 或城市名

        返回值：
            合法的 6 位数字 adcode，解析失败返回 None
        """
        if not adcode or not adcode.strip():
            logger.warning("[weather_tool] adcode 为空，无法自动解析")
            return None

        adcode_clean = adcode.strip()

        # 已经是合法的6位数字
        if adcode_clean.isdigit() and len(adcode_clean) == 6:
            return adcode_clean

        # 看起来像城市名 → 尝试 CityResolver（异步调用）
        logger.info(
            f"[weather_tool] adcode 不是合法格式('{adcode_clean}')，"
            f"尝试作为城市名调用 CityResolver"
        )
        try:
            from app.tools.city_resolver import CityResolverTool

            resolver = CityResolverTool()
            if resolver.load_error:
                logger.error(
                    f"[weather_tool] CityResolver 数据加载失败: {resolver.load_error}"
                )
                return None

            # 直接 await 异步调用（_ensure_adcode 本身是 async 的）
            result = await resolver.run(city=adcode_clean)

            if result.get("success") and result.get("result"):
                resolved = result["result"].get("adcode", "")
                if resolved and resolved.isdigit() and len(resolved) == 6:
                    logger.info(
                        f"[weather_tool] 城市名自动解析成功 | "
                        f"{adcode_clean!r} → {resolved!r}"
                    )
                    return resolved

            logger.warning(
                f"[weather_tool] CityResolver 解析失败 | "
                f"city={adcode_clean!r} | result={result.get('summary', 'N/A')}"
            )
            return None
        except Exception as exc:
            logger.error(
                f"[weather_tool] CityResolver 调用异常 | "
                f"city={adcode_clean!r} | {type(exc).__name__}: {exc}"
            )
            return None

    async def _call_amap_api(
        self,
        adcode: str,
        date: str | None,
        days: int | None = None,
    ) -> dict:
        """
        调用高德天气 API

        API 文档: https://lbs.amap.com/api/webservice/guide/api/weatherinfo

        参数：
            adcode: 行政区划代码
            date: 查询日期（高德不支持指定日期查询，仅返回当天及未来预报）

        返回值：
            统一格式的天气数据
        """
        # 检查 API Key 是否配置
        api_key = settings.AMAP_API_KEY
        if not api_key:
            logger.warning("[weather_tool] AMAP_API_KEY 未配置，返回错误")
            return self._build_error(
                adcode=adcode,
                date=date,
                error="AMAP_API_KEY 未配置",
                message="请在 .env 文件中配置 AMAP_API_KEY（高德开放平台 API Key）",
            )

        # 高德天气 API URL（从配置读取，不硬编码）
        url = settings.AMAP_WEATHER_URL

        # 使用预报模式（extensions=all），可获取未来 4 天预报
        # 如果只想实况，用 extensions=base
        params = {
            "key": api_key,
            "city": adcode,
            "extensions": "all",  # 预报模式（4天）
        }

        logger.info(
            f"[weather_tool] 请求高德天气 API | "
            f"adcode={adcode} | date={date or '今天'} | "
            f"extensions=all | days={days or 1}"
        )

        # 发送请求
        resp = requests.get(url, params=params, timeout=10)

        logger.debug(
            f"[weather_tool] 高德响应 | status={resp.status_code} | "
            f"body_len={len(resp.text)} | "
            f"耗时={resp.elapsed.total_seconds() if hasattr(resp, 'elapsed') else 'N/A'}s"
        )

        if resp.status_code != 200:
            return self._build_error(
                adcode=adcode,
                date=date,
                error=f"HTTP {resp.status_code}",
                message=f"高德 API 返回 HTTP {resp.status_code}",
                raw={"status_code": resp.status_code, "body": resp.text[:500]},
            )

        # 解析 JSON
        try:
            data = resp.json()
        except Exception as exc:
            return self._build_error(
                adcode=adcode,
                date=date,
                error=f"JSONDecodeError: {str(exc)}",
                message="高德 API 返回了非 JSON 格式的数据",
                raw={"body": resp.text[:500]},
            )

        logger.debug(
            f"[weather_tool] 高德响应数据 | status={data.get('status')} | "
            f"infocode={data.get('infocode')} | count={data.get('count', 0)}"
        )

        # 检查 API 返回状态
        if data.get("status") != "1":
            info = data.get("info", "未知错误")
            infocode = data.get("infocode", "")
            return self._build_error(
                adcode=adcode,
                date=date,
                error=f"AMapError({infocode}): {info}",
                message=f"高德天气 API 返回错误: {info}",
                raw=data,
            )

        # 解析预报数据
        forecasts = data.get("forecasts", [])
        if not forecasts:
            return self._build_error(
                adcode=adcode,
                date=date,
                error="NoForecastData",
                message="高德 API 未返回天气预报数据",
                raw=data,
            )

        forecast = forecasts[0]
        city_name = forecast.get("city", "")
        report_time = forecast.get("reporttime", "")
        casts = forecast.get("casts", [])

        if not casts:
            return self._build_error(
                adcode=adcode,
                date=date,
                error="NoCastData",
                message="未找到天气详情数据",
                raw=data,
            )

        requested_days = self._normalize_days(days)

        # 如果指定了日期，尝试匹配。高德只返回未来数天，无法匹配时从第一天开始。
        target_cast = None
        target_index = 0
        if date:
            for index, cast in enumerate(casts):
                if cast.get("date") == date:
                    target_cast = cast
                    target_index = index
                    break
            if not target_cast:
                # 如果没找到指定日期，使用第一天（最近一天）
                logger.warning(
                    f"[weather_tool] 未找到日期 {date} 的预报数据，"
                    f"可用日期: {[c.get('date') for c in casts]}，使用第一天"
                )
                target_cast = casts[0]
        else:
            target_cast = casts[0]

        selected_casts = casts[target_index: target_index + requested_days]
        if not selected_casts:
            selected_casts = [target_cast]

        forecast_days = [self._normalize_cast(cast) for cast in selected_casts]
        has_precipitation = any(
            self._has_precipitation(day["dayweather"], day["nightweather"])
            for day in forecast_days
        )

        # 构建统一返回格式
        return {
            "success": True,
            "city": city_name,
            "adcode": adcode,
            "date": target_cast.get("date", ""),
            "week": target_cast.get("week", ""),
            "weather": f"{target_cast.get('dayweather', '')}转{target_cast.get('nightweather', '')}"
            if target_cast.get("nightweather") and target_cast.get("nightweather") != target_cast.get("dayweather", "")
            else target_cast.get("dayweather", ""),
            "dayweather": target_cast.get("dayweather", ""),
            "nightweather": target_cast.get("nightweather", ""),
            "temperature": f"{target_cast.get('nighttemp', '')}°C ~ {target_cast.get('daytemp', '')}°C",
            "daytemp": target_cast.get("daytemp", ""),
            "nighttemp": target_cast.get("nighttemp", ""),
            "winddirection": f"{target_cast.get('daywind', '')}/{target_cast.get('nightwind', '')}",
            "daywind": target_cast.get("daywind", ""),
            "nightwind": target_cast.get("nightwind", ""),
            "windpower": f"{target_cast.get('daypower', '')}级/{target_cast.get('nightpower', '')}级",
            "daypower": target_cast.get("daypower", ""),
            "nightpower": target_cast.get("nightpower", ""),
            "humidity": "N/A",  # 高德预报 API 不提供湿度
            "reporttime": report_time,
            "days": len(forecast_days),
            "forecast_days": forecast_days,
            "has_precipitation": has_precipitation,
            "summary": self._build_summary(city_name, forecast_days),
            "result": {
                "city": city_name,
                "adcode": adcode,
                "days": len(forecast_days),
                "forecast_days": forecast_days,
                "has_precipitation": has_precipitation,
                "target_cast": target_cast,
            },
            "error": None,
            "raw": data,
        }

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def _normalize_days(self, days: int | None) -> int:
        """将预报天数限制在高德天气 API 可返回的 1-4 天内。"""
        if days is None:
            return 1
        return max(1, min(int(days), 4))

    def _normalize_cast(self, cast: dict) -> dict:
        """把高德单日 cast 转成稳定、易读的字段。"""
        day_weather = cast.get("dayweather", "")
        night_weather = cast.get("nightweather", "")
        weather = day_weather
        if night_weather and night_weather != day_weather:
            weather += f"转{night_weather}"

        return {
            "date": cast.get("date", ""),
            "week": cast.get("week", ""),
            "weather": weather,
            "dayweather": day_weather,
            "nightweather": night_weather,
            "temperature": f"{cast.get('nighttemp', '')}°C ~ {cast.get('daytemp', '')}°C",
            "daytemp": cast.get("daytemp", ""),
            "nighttemp": cast.get("nighttemp", ""),
            "winddirection": f"{cast.get('daywind', '')}/{cast.get('nightwind', '')}",
            "daywind": cast.get("daywind", ""),
            "nightwind": cast.get("nightwind", ""),
            "windpower": f"{cast.get('daypower', '')}级/{cast.get('nightpower', '')}级",
            "daypower": cast.get("daypower", ""),
            "nightpower": cast.get("nightpower", ""),
            "has_precipitation": self._has_precipitation(day_weather, night_weather),
        }

    def _has_precipitation(self, *weather_values: str) -> bool:
        """判断天气文本中是否包含雨雪等降水信息。"""
        text = "".join(weather_values)
        return any(keyword in text for keyword in ("雨", "雪", "冰雹", "冻雨"))

    def _build_summary(self, city: str, forecast_days: list[dict]) -> str:
        """
        从高德 API 的 cast 数据构建人类可读摘要

        参数：
            city: 城市名
            forecast_days: 多日预报数据
        """
        if not forecast_days:
            return f"{city} 未查询到可用天气预报。"

        if len(forecast_days) == 1:
            day = forecast_days[0]
            return (
                f"{city} {day['date']}（{day['week']}）天气：{day['weather']}，"
                f"温度 {day['temperature']}，风力 {day['daywind']} {day['daypower']}级。"
            )

        lines = [
            f"{city}未来{len(forecast_days)}天天气预报："
        ]
        for day in forecast_days:
            rain_text = "有降水" if day["has_precipitation"] else "无明显降水"
            lines.append(
                f"{day['date']}（{day['week']}）：{day['weather']}，"
                f"{day['temperature']}，{rain_text}"
            )

        conclusion = "有降水，建议带伞。" if any(day["has_precipitation"] for day in forecast_days) else "暂无明显降水。"
        lines.append(f"降水判断：未来{len(forecast_days)}天{conclusion}")
        return "；".join(lines)

    def _build_error(
        self,
        adcode: str,
        date: str | None,
        error: str,
        message: str,
        raw: dict | None = None,
    ) -> dict:
        """构建统一错误格式"""
        return {
            "success": False,
            "city": "",
            "adcode": adcode,
            "date": date or "",
            "weather": "",
            "temperature": "",
            "winddirection": "",
            "windpower": "",
            "humidity": "",
            "reporttime": "",
            "error": error,
            "message": message,
            "summary": f"天气查询失败: {message}",
            "result": None,
            "raw": raw or {},
        }

    def validate_input(self, adcode: str, date: str | None = None, days: int | None = None, **kwargs: Any) -> None:
        """
        参数校验

        参数：
            adcode: 行政区划代码（或城市名，_ensure_adcode 会自动处理）
            date: 日期（YYYY-MM-DD）
            days: 预报天数（1-4）
        """
        if not adcode or not adcode.strip():
            raise ValueError("adcode 不能为空")

        adcode_clean = adcode.strip()

        # 注意：不再严格要求必须 6 位数字，因为 _ensure_adcode 会自动回退
        # 只做最基本的格式检查
        if not adcode_clean.isdigit() or len(adcode_clean) != 6:
            logger.info(
                f"[weather_tool] validate_input: adcode='{adcode_clean}' 不是标准6位数字，"
                f"将在 _execute 中尝试作为城市名自动解析"
            )

        if date and not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            logger.warning(f"[weather_tool] validate_input: 忽略非标准日期参数: {date}")

        if days is not None:
            try:
                days_int = int(days)
            except (TypeError, ValueError) as exc:
                raise ValueError("days 必须是 1-4 的整数") from exc
            if days_int < 1 or days_int > 4:
                raise ValueError("days 必须在 1-4 之间（高德天气预报最多返回4天）")
