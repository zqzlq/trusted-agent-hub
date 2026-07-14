"""TrustedAgentHub API — FastAPI application entry point.

Mounts the consumer router (分发侧) at /api/v0 and configures CORS so
the frontend and CLI tools can call the API from any origin during
development.
"""

from __future__ import annotations

from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .consumer_router import router as consumer_router
from .routers.trust import router as trust_router

app = FastAPI(
    title="Trusted Agent Hub API",
    version="0.1.0",
    description="Backend API for the TrustedAgentHub package registry — Consumer endpoints (分发侧).",
)

# ---------------------------------------------------------------------------
# CORS — permissive for local development; tighten before production.
# ---------------------------------------------------------------------------
# 关键：allow_credentials=False 时 allow_origins 才能用 ["*"]
# 本地开发不需要跨域携带 cookie，所以这是正确的配置。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(consumer_router, prefix="/api/v0")
app.include_router(trust_router, prefix="/api/v0")


# 显式兜底：对所有 OPTIONS 请求直接返回 200 + CORS 头
# 确保浏览器预检请求不会被 FastAPI 路由层拦截返回 405
@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str) -> Response:
    """CORS preflight catch-all — 返回空 200 响应，由 CORSMiddleware 注入头部。"""
    print(f"\n{'='*60}")
    print(f"[TAH-main] >>> OPTIONS preflight 到达")
    print(f"[TAH-main]     origin = {request.headers.get('origin', 'N/A')}")
    print(f"[TAH-main]     path   = /{rest_of_path}")
    print(f"{'='*60}\n")
    return Response(status_code=200)


@app.get("/", include_in_schema=False)
def root() -> Dict[str, str]:
    """Health-check / welcome endpoint."""
    print("[TAH-main] >>> GET / 健康检查 被调用")
    return {"service": "Trusted Agent Hub API", "version": "0.1.0"}


# 启动日志
print("\n" + "=" * 60)
print("[TAH-main] Trusted Agent Hub API 启动中...")
print(f"[TAH-main] CORS: allow_origins=['*'], allow_credentials=False")
print(f"[TAH-main] routers: consumer_router + trust_router 已注册")
print(f"[TAH-main] OPTIONS catch-all 已注册")
print("=" * 60 + "\n")