"""
=============================================================================
天气查询工具 — 调用第三方天气 API 获取天气数据
=============================================================================
职责：
  1. 接收城市名称和日期（可选）
  2. 调用第三方天气 API（OpenWeatherMap / 和风天气 等）
  3. 将 API 返回的结构化数据转为 LLM 友好的文本摘要

当前状态：
  提供模拟数据（Mock），用于开发调试。
  替换为真实 API 只需修改 _call_api 方法，不影响 Agent 和其他模块。

使用示例：
    tool = WeatherTool()
    result = await tool.run(city="北京", date="2026-07-08")
    # => {"success": True, "summary": "北京 7月8日 晴转多云，18°C~26°C...", ...}
=============================================================================
"""

from typing import Any

import requests

from app.core.config import settings
from app.tools.base import BaseTool
from app.utils.logger import logger


class WeatherTool(BaseTool):
    """
    天气查询工具

    支持查询指定城市当天和未来天气信息。
    当前使用模拟数据，实际接入天气 API 时修改 _call_api 方法即可。
    """

    @property
    def name(self) -> str:
        """工具唯一名称"""
        return "weather"

    @property
    def description(self) -> str:
        """工具描述（LLM 据此判断何时调用）"""
        return (
            "查询指定城市在指定日期（或当天）的天气信息。"
            "返回温度、天气状况、风力、湿度等信息。"
            "参数：city（城市名称，必填），date（日期，格式YYYY-MM-DD，可选，默认为当天）"
        )

    @property
    def input_schema(self) -> dict:
        """输入参数 Schema"""
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，如 北京、上海、深圳",
                },
                "date": {
                    "type": "string",
                    "description": "查询日期，格式 YYYY-MM-DD，如 2026-07-08。不传则默认查询当天",
                },
            },
            "required": ["city"],
        }

    async def _execute(self, city: str, date: str | None = None, **kwargs: Any) -> dict:
        """
        执行天气查询

        参数：
            city: 城市名称
            date: 查询日期（可选）

        返回值：
            dict 包含 success、result、summary 等字段
        """
        logger.info(f"查询天气 | 城市={city} | 日期={date or '今天'}")

        # ---- 调用天气 API ----
        weather_data = await self._call_api(city, date)

        # ---- 转为可读摘要 ----
        summary = self._format_summary(city, date, weather_data)

        return {
            "success": True,
            "result": weather_data,
            "error": None,
            "summary": summary,
        }

    async def _call_api(self, city: str, date: str | None) -> dict:
        """
        调用第三方天气 API

        当前使用模拟数据。
        接入真实 API 的方案（如 OpenWeatherMap）：
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": city, "appid": settings.WEATHER_API_KEY, "units": "metric"}
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        """
        # ---- 模拟数据（开发阶段使用） ----
        # 根据城市名生成稍微不同的模拟数据，方便测试
        city_hash = sum(ord(c) for c in city) % 10

        mock_weathers = {
            0: {"condition": "晴", "temp_high": 32, "temp_low": 22, "humidity": 45, "wind": "东南风 2-3级"},
            1: {"condition": "多云", "temp_high": 28, "temp_low": 20, "humidity": 55, "wind": "北风 3-4级"},
            2: {"condition": "阴", "temp_high": 25, "temp_low": 18, "humidity": 70, "wind": "东北风 3级"},
            3: {"condition": "小雨", "temp_high": 22, "temp_low": 16, "humidity": 85, "wind": "东风 4-5级"},
            4: {"condition": "中雨", "temp_high": 20, "temp_low": 15, "humidity": 90, "wind": "东风 5-6级"},
            5: {"condition": "晴转多云", "temp_high": 30, "temp_low": 21, "humidity": 50, "wind": "南风 2级"},
            6: {"condition": "雷阵雨", "temp_high": 27, "temp_low": 19, "humidity": 80, "wind": "西风 4级"},
            7: {"condition": "雾霾", "temp_high": 24, "temp_low": 17, "humidity": 60, "wind": "无持续风向 1-2级"},
            8: {"condition": "暴晒", "temp_high": 36, "temp_low": 26, "humidity": 35, "wind": "西南风 2级"},
            9: {"condition": "阵雪", "temp_high": -3, "temp_low": -10, "humidity": 65, "wind": "北风 5-6级"},
        }

        weather = mock_weathers.get(city_hash, mock_weathers[0])
        # 如果有日期，稍微修改温度和天气（模拟不同日期的天气变化）
        if date:
            import hashlib
            date_hash = int(hashlib.md5(date.encode()).hexdigest()[:2], 16) % 5
            weather = dict(weather)
            weather["temp_high"] += date_hash - 2
            weather["temp_low"] += date_hash - 2

        return weather

    def _format_summary(self, city: str, date: str | None, data: dict) -> str:
        """
        将天气数据转为 LLM 友好的文本摘要

        参数：
            city: 城市名称
            date: 日期
            data: 天气数据字典

        返回值：
            可读的天气摘要文本
        """
        date_str = date or "今天"
        return (
            f"{city} {date_str}天气：{data['condition']}，"
            f"温度 {data['temp_low']}°C ~ {data['temp_high']}°C，"
            f"湿度 {data['humidity']}%，"
            f"风力 {data['wind']}。"
        )

    def validate_input(self, city: str, **kwargs: Any) -> None:
        """
        参数校验

        参数：
            city: 城市名称

        异常：
            ValueError：城市名称为空
        """
        if not city or not city.strip():
            raise ValueError("城市名称不能为空")
