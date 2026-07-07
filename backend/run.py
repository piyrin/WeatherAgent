"""
=============================================================================
项目启动入口 — 一行命令启动整个后端服务
=============================================================================
用法：
    python run.py

等效于：
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

注意：
    运行前请确保：
      1. 已在 backend/ 目录下（或通过 cd backend 切换）
      2. 已安装依赖：pip install -r requirements.txt
      3. 已配置 .env 文件（至少填写 LLM_API_KEY）
=============================================================================
"""

import sys
from pathlib import Path

import uvicorn

# 确保 backend/ 目录在 Python 路径中
# 这样 `from app.xxx import xxx` 才能正常工作
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"  启动地址: http://{settings.APP_HOST}:{settings.APP_PORT}")
    print(f"  API 文档: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,       # 开发环境自动重载
        log_level=settings.LOG_LEVEL.lower(),
    )
