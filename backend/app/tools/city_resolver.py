"""
=============================================================================
城市解析工具 — 将城市名称（中文）转换为高德行政区划 adcode
=============================================================================
职责：
  1. 接收城市中文名称（如 "应城"、"北京"、"武汉"）
  2. 在本地行政区划数据库中查找对应的 adcode
  3. 返回 adcode、省份、城市等信息

数据来源：
  - app/data/cities.json（基于国家统计局行政区划代码 + 高德 adcode）

设计说明：
  - 支持精确匹配和模糊匹配（含/不含"市"后缀）
  - 支持区县级查询（如"应城"→420981，"昌平"→110114）
  - JSON 数据库，新增城市只需追加条目，无需修改代码

使用示例：
    tool = CityResolverTool()
    result = await tool.run(city="应城")
    # => {"adcode": "420981", "city": "应城", ...}
=============================================================================
"""

import json
from pathlib import Path
from typing import Any

from app.tools.base import BaseTool
from app.utils.logger import logger


class CityResolverTool(BaseTool):
    """
    城市解析工具

    将用户输入的城市中文名转换为高德天气 API 所需的行政区划代码（adcode）。
    支持省、市、区/县三级行政区划查询。
    """

    def __init__(self, data_path: str | None = None):
        """
        初始化城市解析工具

        参数：
            data_path: cities.json 路径，默认在 app/data/cities.json
        """
        if data_path is None:
            # 相对于此文件的路径：tools/../data/cities.json
            data_path = Path(__file__).parent.parent / "data" / "cities.json"
        self._data_path = Path(data_path)
        self._cities: list[dict] = []
        self._index: dict[str, dict] = {}  # name -> city entry
        self._load_data()

    # 统计属性（公开，方便外部诊断）
    load_error: str = ""
    load_summary: str = ""

    def _load_data(self):
        """从 JSON 文件加载城市数据并建立索引（含数据完整性校验）"""
        try:
            with open(self._data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw_cities = data.get("cities", [])
            logger.info(
                f"[city_resolver] 开始加载城市数据 | 文件={self._data_path} | "
                f"原始条目数={len(raw_cities)}"
            )

            valid_entries = 0
            skipped_entries = 0
            for entry in raw_cities:
                # ---- 数据完整性校验 ----
                name = entry.get("name", "")
                adcode = entry.get("adcode", "")
                province = entry.get("province", "")

                if not name or not adcode or not province:
                    skipped_entries += 1
                    logger.warning(
                        f"[city_resolver] 跳过不完整的城市条目 | "
                        f"name={name!r} adcode={adcode!r} "
                        f"province={province!r}"
                    )
                    continue

                if len(adcode) != 6 or not adcode.isdigit():
                    skipped_entries += 1
                    logger.warning(
                        f"[city_resolver] 跳过无效 adcode | "
                        f"name={name!r} adcode={adcode!r}"
                    )
                    continue

                valid_entries += 1
                self._cities.append(entry)

                # 建立精确名称索引（按短名称优先）
                if name in self._index:
                    existing = self._index[name]
                    existing_level = existing.get("level", "")
                    new_level = entry.get("level", "")
                    # 优先保留 county 级别（更精确）
                    if new_level == "county" and existing_level != "county":
                        self._index[name] = entry
                else:
                    self._index[name] = entry

            self.load_error = ""
            self.load_summary = (
                f"共 {len(self._cities)} 条有效记录 "
                f"（{skipped_entries} 条跳过）| "
                f"唯一索引 {len(self._index)} 条"
            )
            logger.info(
                f"[city_resolver] {self.load_summary}"
            )
        except FileNotFoundError:
            self.load_error = f"城市数据文件未找到: {self._data_path}"
            logger.error(f"[city_resolver] {self.load_error}")
            self._cities = []
            self._index = {}
            self.load_summary = "加载失败：数据文件未找到"
        except json.JSONDecodeError as exc:
            self.load_error = f"城市数据 JSON 解析失败: {exc}"
            logger.error(f"[city_resolver] {self.load_error}")
            self._cities = []
            self._index = {}
            self.load_summary = f"加载失败：JSON 解析错误"

    @property
    def name(self) -> str:
        return "city_resolver"

    @property
    def description(self) -> str:
        return (
            "将城市中文名称（如'应城'、'北京'、'武汉'）转换为高德行政区划代码（adcode）。"
            "在调用天气查询工具之前，必须先调用此工具将城市名转换为 adcode。"
            "参数：city（城市中文名称，必填），如 '应城'、'朝阳'、'武汉'"
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市中文名称，如 应城、北京、武汉、朝阳",
                },
            },
            "required": ["city"],
        }

    async def _execute(self, city: str, **kwargs: Any) -> dict:
        """
        解析城市名称 → adcode

        参数：
            city: 用户输入的城市名称

        返回值：
            {
                "success": True/False,
                "result": {"adcode": "...", "city": "...", "province": "...", "level": "..."},
                "summary": "...",
                "error": None/"..."
            }
        """
        logger.info(
            f"[city_resolver] 开始解析 | 输入={city!r} | "
            f"索引条目数={len(self._index)} | 加载状态={self.load_summary or 'OK'}"
        )

        if not city or not city.strip():
            logger.warning("[city_resolver] 输入为空字符串")
            return {
                "success": False,
                "result": None,
                "error": "城市名称不能为空",
                "summary": "错误：城市名称不能为空",
            }

        city_clean = city.strip()
        logger.debug(
            f"[city_resolver] 清洗后输入={city_clean!r} | "
            f"精确匹配={city_clean in self._index}"
        )

        # 1. 精确匹配
        if city_clean in self._index:
            entry = self._index[city_clean]
            logger.debug(f"[city_resolver] 精确命中 | name={entry.get('name')} adcode={entry.get('adcode')}")
            return self._build_success(entry)

        # 2. 添加"市"后缀再匹配（如 "武汉" → "武汉市"）
        if not city_clean.endswith("市"):
            with_suffix = city_clean + "市"
            if with_suffix in self._index:
                logger.debug(f"[city_resolver] 加'市'后缀命中 | {city_clean!r} → {with_suffix!r}")
                return self._build_success(self._index[with_suffix])

        # 3. 去除"市"后缀再匹配（如 "北京市" → "北京"）
        if city_clean.endswith("市") and len(city_clean) > 1:
            without_suffix = city_clean[:-1]
            if without_suffix in self._index:
                logger.debug(f"[city_resolver] 去'市'后缀命中 | {city_clean!r} → {without_suffix!r}")
                return self._build_success(self._index[without_suffix])

        # 4. 添加"区"后缀再匹配
        if not city_clean.endswith("区"):
            with_suffix = city_clean + "区"
            if with_suffix in self._index:
                logger.debug(f"[city_resolver] 加'区'后缀命中 | {city_clean!r} → {with_suffix!r}")
                return self._build_success(self._index[with_suffix])

        # 5. 模糊搜索（子串匹配，在 name 中查找）
        candidates = []
        for entry in self._cities:
            entry_name = entry.get("name", "")
            if entry_name and city_clean in entry_name:
                candidates.append(entry)
        if candidates:
            # 优先返回匹配度最高的（name 最短的）
            candidates.sort(
                key=lambda x: (
                    len(x.get("name", "")),
                    0 if x.get("level") == "county" else 1,
                )
            )
            best = candidates[0]
            logger.debug(
                f"[city_resolver] 模糊匹配 | 候选数={len(candidates)} | "
                f"最优={best.get('name')} adcode={best.get('adcode')}"
            )
            return self._build_success(best)

        # 6. 模糊搜索（name 在 city_clean 中）
        for entry in self._cities:
            entry_name = entry.get("name", "")
            if entry_name and entry_name in city_clean:
                logger.debug(f"[city_resolver] 反向模糊命中 | entry={entry_name}")
                return self._build_success(entry)

        # 未找到
        logger.warning(
            f"[city_resolver] 未找到城市 '{city_clean}' | "
            f"索引中有 {len(self._index)} 个城市 | "
            f"输入长度={len(city_clean)}"
        )
        return {
            "success": False,
            "result": None,
            "error": f"未找到城市 '{city_clean}' 的行政区划代码",
            "summary": f"错误：未找到 '{city_clean}' 的行政区划代码，请检查城市名称是否正确。",
        }

    def _build_success(self, entry: dict) -> dict:
        """
        构建成功响应（防御性编程：所有字段使用 .get() 并校验）

        参数：
            entry: 城市数据条目（dict，必须含 name/adcode/province）

        返回值：
            统一格式的成功响应 dict
        """
        adcode = entry.get("adcode")
        city = entry.get("name")
        province = entry.get("province")
        level = entry.get("level", "unknown")

        # ---- 数据完整性校验：任一关键字段缺失则返回错误 ----
        if not adcode:
            err_msg = (
                f"CityResolver 内部错误：条目缺少 adcode 字段。"
                f"entry={entry}"
            )
            logger.error(f"[city_resolver] {err_msg}")
            return {
                "success": False,
                "result": None,
                "error": err_msg,
                "summary": f"错误：城市数据不完整，缺少 adcode",
            }

        if not city:
            err_msg = (
                f"CityResolver 内部错误：条目缺少 name 字段。"
                f"adcode={adcode}, entry={entry}"
            )
            logger.error(f"[city_resolver] {err_msg}")
            return {
                "success": False,
                "result": None,
                "error": err_msg,
                "summary": f"错误：城市数据不完整，缺少城市名",
            }

        return {
            "success": True,
            "result": {
                "adcode": adcode,
                "city": city,
                "province": province or "",
                "level": level,
            },
            "error": None,
            "summary": f"城市 '{city}' → adcode={adcode} ({province or '未知省份'})",
        }

    def validate_input(self, city: str, **kwargs: Any) -> None:
        """参数校验"""
        if not city or not city.strip():
            raise ValueError("城市名称不能为空")
