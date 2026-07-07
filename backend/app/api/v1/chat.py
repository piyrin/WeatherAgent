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

from fastapi import APIRouter, Depends
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
    logger.info(
        f"收到聊天请求 | message=\"{request.message[:100]}\" | "
        f"conversation_id={request.conversation_id or '新会话'}"
    )

    # 创建 Service 并处理
    service = ChatService(db)
    result: ChatResponse = await service.send_message(
        message=request.message,
        conversation_id=request.conversation_id,
    )

    # 返回统一格式（对齐前端期望的字段结构）
    result_data = result.model_dump()
    result_data["answer"] = result_data["message"]
    result_data["steps"] = result_data.get("agent_process", {}).get("steps", [])
    result_data["tools"] = result_data.get("agent_process", {}).get("tool_calls", [])
    
    return success(
        data=result_data,
        message="ok",
    )
