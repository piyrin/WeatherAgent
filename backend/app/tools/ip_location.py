"""
=============================================================================
IP 定位工具 — 调用高德 IP 定位 API 查询 IP 地址的地理位置
=============================================================================
职责：
  1. 接收 IP 地址（可选，不传则取请求方 IP）
  2. 调用高德 IP 定位 API：https://restapi.amap.com/v3/ip
  3. 返回省份、城市、adcode、矩形区域

API 说明：
  - 基础 URL：https://restapi.amap.com/v3/ip
  - 参数：
      key  — API Key（从 .env 读取）
      ip   — IP 地址（可选，不填取请求方 IP）
  - 仅支持 IPv4 国内 IP，国外/非法 IP 返回空
  - 返回格式：JSON

统一返回格式：
  成功: {"success": true, "result": {"province": "...", "city": "...",
         "adcode": "...", "rectangle": "..."}, "summary": "..."}
  失败: {"success": false, "error": "...", "message": "...", "raw": {...}}

依赖链：
  IP定位 → 获取城市 → CityResolver(本地) → adcode → WeatherTool
  IP定位 → 获取城市 → 用于路径规划的默认起点城市

使用示例：
    tool = IPLocationTool()
    result = await tool.run(ip="114.247.50.2")
    # → {"province": "北京市", "city": "北京市", "adcode": "110000", ...}
=============================================================================
"""

from typing import Any

import requests

from app.core.config import settings
from app.tools.base import BaseTool
from app.utils.logger import logger


class IPLocationTool(BaseTool):
    """
    IP 定位工具

    调用高德 IP 定位 API，根据 IP 地址获取地理位置信息。
    不传 IP 则自动定位请求方 IP。
    """

    @property
    def name(self) -> str:
        return "ip_location"

    @property
    def description(self) -> str:
        return (
            "根据 IP 地址获取地理位置信息（省份、城市、行政区划代码）。"
            "用于当用户询问'我在哪里'、'当前城市天气'等需要确定用户位置的场景。"
            "也用于路径规划时确定默认起点城市。"
            "参数：ip（IP 地址，可选。不传则自动定位请求方 IP）"
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ip": {
                    "type": "string",
                    "description": "需要定位的 IP 地址。不传则自动使用请求方 IP。仅支持国内 IPv4 地址。",
                },
            },
            "required": [],
        }

    async def _execute(self, ip: str = "", **kwargs: Any) -> dict:
        """
        执行 IP 定位查询

        参数：
            ip: IP 地址（可选，不传则取请求方 IP）

        返回值：
            统一格式的地理位置数据 dict
        """
        ip_param = ip.strip() if ip else ""
        logger.info(
            f"[ip_location] 查询 IP 定位 | ip={ip_param or '(自动获取请求方IP)'}"
        )

        # ---- 检查 API Key ----
        api_key = settings.AMAP_API_KEY
        if not api_key:
            return self._build_error(
                ip=ip_param,
                error="AMAP_API_KEY 未配置",
                message="请在 .env 文件中配置 AMAP_API_KEY",
            )

        # ---- 调用高德 IP 定位 API ----
        url = f"{settings.AMAP_BASE_URL}/v3/ip"
        params: dict[str, str] = {
            "key": api_key,
            "output": "JSON",
        }
        if ip_param:
            params["ip"] = ip_param

        try:
            resp = requests.get(url, params=params, timeout=10)
            logger.debug(
                f"[ip_location] 高德响应 | status={resp.status_code} | "
                f"耗时={resp.elapsed.total_seconds() if hasattr(resp, 'elapsed') else 'N/A'}s"
            )
        except requests.Timeout:
            return self._build_error(
                ip=ip_param,
                error="API_TIMEOUT",
                message="高德 IP 定位 API 请求超时",
            )
        except requests.ConnectionError as exc:
            return self._build_error(
                ip=ip_param,
                error=f"ConnectionError: {exc}",
                message="无法连接到高德 IP 定位 API",
            )

        if resp.status_code != 200:
            return self._build_error(
                ip=ip_param,
                error=f"HTTP {resp.status_code}",
                message=f"高德 API 返回 HTTP {resp.status_code}",
                raw={"status_code": resp.status_code, "body": resp.text[:500]},
            )

        # ---- 解析 JSON ----
        try:
            data = resp.json()
        except Exception as exc:
            return self._build_error(
                ip=ip_param,
                error=f"JSONDecodeError: {exc}",
                message="高德 API 返回了非 JSON 格式的数据",
                raw={"body": resp.text[:500]},
            )

        # ---- 检查 API 状态 ----
        if data.get("status") != "1":
            info = data.get("info", "未知错误")
            return self._build_error(
                ip=ip_param,
                error=f"AMapError: {info}",
                message=f"高德 IP 定位 API 返回错误: {info}",
                raw=data,
            )

        # ---- 解析返回数据 ----
        province = data.get("province", "") or ""
        city = data.get("city", "") or ""
        adcode = data.get("adcode", "") or ""
        rectangle = data.get("rectangle", "") or ""

        # 检查是否为局域网或非法 IP
        if province == "局域网" or (not province and not city):
            ip_label = ip_param or "(自动探测)"
            logger.warning(
                f"[ip_location] IP 定位结果为空 | ip={ip_label} | 可能是局域网/国外IP"
            )
            # 1. 明显的本地/私有地址（127.x, 192.168.x 等）
            if ip_param and self._is_local_ip(ip_param):
                return {
                    "success": False,
                    "result": None,
                    "error": "LOCAL_IP",
                    "message": (
                        f"检测到本地私有 IP（{ip_param}），无法进行公网 IP 定位。"
                        f"开发环境中无法自动定位，请直接说出你所在的城市，"
                        f"例如：'查询北京天气'。"
                    ),
                    "summary": (
                        f"IP 定位失败：检测到本地私有 IP（{ip_param}），"
                        f"无法自动定位。请直接说出你所在的城市名称。"
                    ),
                    "raw": data,
                }
            # 2. 无 IP 或外部 IP 但定位失败（服务器不在国内等）
            return {
                "success": False,
                "result": None,
                "error": "IP_LOCATION_FAILED",
                "message": (
                    f"无法自动定位{'该IP(' + ip_param + ')' if ip_param else '您的位置'}，"
                    f"可能是非国内网络环境。请直接说出你所在的城市名称。"
                ),
                "summary": (
                    f"IP 定位失败：{'IP ' + ip_param + ' ' if ip_param else ''}"
                    f"无法定位。请直接说出你所在的城市名称。"
                ),
                "raw": data,
            }

        summary = (
            f"IP 定位成功：{province}{city}（adcode={adcode}）"
            if city and city != province
            else f"IP 定位成功：{province}（adcode={adcode}）"
        )

        return {
            "success": True,
            "result": {
                "province": province,
                "city": city if city else province,
                "adcode": adcode,
                "rectangle": rectangle,
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
        ip: str,
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
            "summary": f"IP 定位失败: {message}",
            "raw": raw or {},
        }

    def validate_input(self, ip: str = "", **kwargs: Any) -> None:
        """参数校验 — IP 格式基本检查"""
        if ip and ip.strip():
            ip_clean = ip.strip()
            # 基本 IPv4 格式检查（不做严格校验，高德 API 会自行判断）
            parts = ip_clean.split(".")
            if len(parts) != 4:
                logger.warning(
                    f"[ip_location] IP 格式可能不合法: {ip_clean!r}，"
                    f"将直接传给 API 处理"
                )

    @staticmethod
    def _is_local_ip(ip: str) -> bool:
        """
        判断 IP 是否为本地/私有地址

        过滤：127.x.x.x、10.x.x.x、172.16-31.x.x、192.168.x.x、::1、0.0.0.0
        注意：空字符串不算本地IP，表示"未获取到IP"
        """
        if not ip:
            return False  # 空字符串不是本地IP，是"未获取"
        if ip in ("0.0.0.0", "::1"):
            return True
        parts = ip.split(".")
        if len(parts) != 4:
            return True
        try:
            a, b = int(parts[0]), int(parts[1])
        except ValueError:
            return True
        if a == 127 or a == 10:
            return True
        if a == 172 and 16 <= b <= 31:
            return True
        if a == 192 and b == 168:
            return True
        return False
