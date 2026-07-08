"""
=============================================================================
聊天接口 — POST /api/v1/chat
=============================================================================
职责：
  1. 接收用户消息（ChatRequest）
  2. 参数校验（Pydantic 自动完成）
  3. 调用 ChatService 处理
  4. 返回统一的 JSON 响应

Agent 流程：
  用户输入 → ChatRequest 校验 → ChatService.send_message()
  → Agent 执行（理解→规划→工具调用→回答）
  → 返回 ChatResponse
=============================================================================
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.utils.logger import logger
from app.utils.response import success

# 创建路由器（prefix 在 router.py 中统一注册）
router = APIRouter(tags=["聊天"])


@router.post(
    "/chat",
    response_model=dict,
    summary="发送聊天消息",
    description=(
        "向天气与出行助手发送自然语言消息，Agent 会理解任务、制定计划、"
        "调用工具（天气、路线、计算器等），并返回最终回答和执行过程。"
    ),
    responses={
        200: {"description": "成功返回 Agent 回答和执行过程"},
        422: {"description": "参数校验失败（如消息为空）"},
        500: {"description": "Agent 执行失败"},
    },
)
async def chat(
    request: ChatRequest,
    fastapi_request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """
    聊天接口

    请求体示例：
        {
            "message": "明天北京天气怎么样？适合出门吗？",
            "conversation_id": null
        }

    响应示例：
        {
            "code": 200,
            "message": "ok",
            "data": {
                "conversation_id": "550e8400-...",
                "message": "明天北京晴转多云，18°C~26°C...",
                "agent_process": {
                    "plan": "先解析日期 → 查询天气 → 给出建议",
                    "steps": [...],
                    "tool_calls": [...]
                }
            }
        }
    """
    # ---- 提取客户端真实 IP ----
    client_ip = _extract_client_ip(fastapi_request)

    logger.info(
        f"收到聊天请求 | message=\"{request.message[:100]}\" | "
        f"conversation_id={request.conversation_id or '新会话'} | "
        f"client_ip={client_ip or '未知'}"
    )

    # 创建 Service 并处理
    service = ChatService(db)
    result: ChatResponse = await service.send_message(
        message=request.message,
        conversation_id=request.conversation_id,
        client_ip=client_ip,
    )

    # 返回统一格式
    return success(
        data=result.model_dump(),
        message="ok",
    )


def _extract_client_ip(request: Request) -> str:
    """
    从 FastAPI Request 中提取客户端真实 IP

    优先级：
      1. X-Forwarded-For 头（代理/负载均衡后的真实 IP，取第一个非私有IP）
      2. X-Real-IP 头（Nginx 等反向代理设置）
      3. request.client.host（直连时的对端 IP）

    自动过滤：
      - 127.0.0.1 / ::1（本地回环地址）
      - 私有地址段（10.x, 172.16-31.x, 192.168.x）不会被自动注入

    返回值：
        客户端 IP 字符串，无法获取或为本地地址时返回空字符串
    """
    # 1. X-Forwarded-For: "client, proxy1, proxy2"
    x_forwarded_for = request.headers.get("X-Forwarded-For", "")
    if x_forwarded_for:
        # 取第一个非私有 IP（跳过代理自身的内网 IP）
        for ip_candidate in x_forwarded_for.split(","):
            ip = ip_candidate.strip()
            if ip and not _is_local_ip(ip):
                return ip

    # 2. X-Real-IP（常用于 Nginx 反向代理）
    x_real_ip = request.headers.get("X-Real-IP", "")
    if x_real_ip and not _is_local_ip(x_real_ip.strip()):
        return x_real_ip.strip()

    # 3. 直连 IP
    if request.client and request.client.host:
        host = request.client.host
        if not _is_local_ip(host):
            return host

    # 4. 本地地址 — 开发环境，返回空，让 ip_location 自行处理
    return ""


def _is_local_ip(ip: str) -> bool:
    """
    判断 IP 是否为本地/私有地址（无法用于公网定位）

    过滤范围：
      - 127.0.0.0/8    (loopback)
      - ::1             (IPv6 loopback)
      - 10.0.0.0/8      (private)
      - 172.16.0.0/12   (private)
      - 192.168.0.0/16  (private)
      - 0.0.0.0         (invalid)
    """
    if not ip:
        return False  # 空字符串不是本地IP，是"未获取"
    if ip in ("0.0.0.0", "::1"):
        return True
    parts = ip.split(".")
    if len(parts) != 4:
        return True  # 非 IPv4，安全起见当作本地
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return True
    # loopback
    if a == 127:
        return True
    # 10.x.x.x
    if a == 10:
        return True
    # 172.16.x.x - 172.31.x.x
    if a == 172 and 16 <= b <= 31:
        return True
    # 192.168.x.x
    if a == 192 and b == 168:
        return True
    return False
