"""
=============================================================================
日期解析工具 — 将自然语言日期转换为标准格式
=============================================================================
职责：
  1. 接收自然语言日期描述（如"明天"、"下周三"、"7月15日"）
  2. 转换为标准 YYYY-MM-DD 格式
  3. 返回星期几、是否为节假日等附加信息

Agent 使用场景：
  用户说"后天北京天气怎么样"时，Agent 先调用本工具将"后天"转为具体日期，
  再将日期传给 WeatherTool 查询。
=============================================================================
"""

import re
from datetime import datetime, timedelta
from typing import Any

from app.tools.base import BaseTool
from app.utils.logger import logger


class DateParserTool(BaseTool):
    """
    日期解析工具

    将中文自然语言日期描述转为标准格式。
    支持：今天、明天、后天、大后天、下周X、X天后、YYYY-MM-DD、MM月DD日等。
    """

    # 中文数字映射
    _CN_NUM = {
        "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
        "日": 7, "天": 7,  # "周日" / "周天"
    }

    # 星期映射
    _WEEKDAY_CN = {
        0: "星期一", 1: "星期二", 2: "星期三", 3: "星期四",
        4: "星期五", 5: "星期六", 6: "星期日",
    }

    @property
    def name(self) -> str:
        return "date_parser"

    @property
    def description(self) -> str:
        return (
            "将自然语言描述的日期转换为标准日期格式（YYYY-MM-DD）。"
            "支持：今天、明天、后天、下周X、X天后、MM月DD日、YYYY-MM-DD。"
            "参数：date_text（自然语言日期描述，必填）"
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "date_text": {
                    "type": "string",
                    "description": "自然语言日期描述，如 '明天'、'下周三'、'7月15日'、'2026-07-08'",
                },
            },
            "required": ["date_text"],
        }

    async def _execute(self, date_text: str, **kwargs: Any) -> dict:
        """
        解析自然语言日期

        参数：
            date_text: 自然语言日期描述

        返回值：
            dict 包含解析结果
        """
        logger.info(f"解析日期 | 输入={date_text}")

        today = datetime.now()

        try:
            parsed_date = self._parse(today, date_text)
            weekday_str = self._WEEKDAY_CN[parsed_date.weekday()]
            date_iso = parsed_date.strftime("%Y-%m-%d")

            result = {
                "date": date_iso,
                "weekday": weekday_str,
                "year": parsed_date.year,
                "month": parsed_date.month,
                "day": parsed_date.day,
                "is_weekend": parsed_date.weekday() >= 5,
                "days_from_today": (parsed_date - today.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )).days,
            }

            summary = f"'{date_text}' 解析为 {date_iso}（{weekday_str}）"

            return {
                "success": True,
                "result": result,
                "error": None,
                "summary": summary,
            }

        except ValueError as exc:
            return {
                "success": False,
                "result": None,
                "error": str(exc),
                "summary": f"无法解析日期 '{date_text}': {str(exc)}",
            }

    def _parse(self, today: datetime, text: str) -> datetime:
        """
        核心解析逻辑

        策略：按优先级尝试多种解析方式，匹配到第一种即返回。

        参数：
            today: 当前日期
            text:  自然语言日期文本

        返回值：
            解析后的 datetime 对象

        异常：
            ValueError：无法解析时抛出
        """
        text = text.strip()

        # ---- 1. ISO 格式（2026-07-08） ----
        iso_match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", text)
        if iso_match:
            return datetime(
                int(iso_match.group(1)),
                int(iso_match.group(2)),
                int(iso_match.group(3)),
                12, 0, 0,
            )

        # ---- 2. MM月DD日 ----
        mmdd_match = re.match(r"^(\d{1,2})月(\d{1,2})日?$", text)
        if mmdd_match:
            month = int(mmdd_match.group(1))
            day = int(mmdd_match.group(2))
            result = datetime(today.year, month, day, 12, 0, 0)
            # 如果日期已过，推到明年
            if result < today.replace(hour=0, minute=0, second=0, microsecond=0):
                result = result.replace(year=today.year + 1)
            return result

        # ---- 3. 今天 ----
        if text in ("今天", "今日"):
            return today.replace(hour=12, minute=0, second=0, microsecond=0)

        # ---- 4. 明天 ----
        if text in ("明天", "明日"):
            return (today + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)

        # ---- 5. 后天 ----
        if text in ("后天", "後天"):
            return (today + timedelta(days=2)).replace(hour=12, minute=0, second=0, microsecond=0)

        # ---- 6. 大后天 ----
        if text in ("大后天"):
            return (today + timedelta(days=3)).replace(hour=12, minute=0, second=0, microsecond=0)

        # ---- 7. N天后（如 "3天后"） ----
        nday_match = re.match(r"^(\d+)天后$", text)
        if nday_match:
            n = int(nday_match.group(1))
            return (today + timedelta(days=n)).replace(hour=12, minute=0, second=0, microsecond=0)

        # ---- 8. 下周X（如 "下周三"、"下周5"） ----
        zx_match = re.match(r"^下周([一二三四五六日天1-6])$", text)
        if zx_match:
            wd_str = zx_match.group(1)
            target_wd = self._parse_weekday(wd_str)  # 0=星期一
            today_wd = today.weekday()
            # 下周 = 当前周往后推 7 天
            days_ahead = (7 - today_wd) + target_wd
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).replace(hour=12, minute=0, second=0, microsecond=0)

        # ---- 9. 本周X（如 "本周五"） ----
        bz_match = re.match(r"^(本周)([一二三四五六日天1-6])$", text)
        if bz_match:
            wd_str = bz_match.group(2)
            target_wd = self._parse_weekday(wd_str)
            today_wd = today.weekday()
            days_ahead = target_wd - today_wd
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).replace(hour=12, minute=0, second=0, microsecond=0)

        # ---- 无法解析 ----
        raise ValueError(
            f"无法识别的日期表达: '{text}'。"
            f"支持：今天、明天、后天、下周X、N天后、MM月DD日、YYYY-MM-DD。"
        )

    def _parse_weekday(self, s: str) -> int:
        """
        解析星期几的字符串，返回 0-6（0=星期一，6=星期日）

        支持：
          - 中文：一/二/三/四/五/六/日/天
          - 数字：1/2/3/4/5/6
        """
        if s in self._CN_NUM:
            return self._CN_NUM[s] - 1  # 中文"一"=1 → 0(星期一)
        if s.isdigit():
            n = int(s)
            if 1 <= n <= 6:
                return n - 1
        raise ValueError(f"无法识别的星期: '{s}'")
