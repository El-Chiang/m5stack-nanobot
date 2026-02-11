"""中继服务入口 — 桥接 M5Stack 与 nanobot agent"""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

from nanobot.config.loader import load_config
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.bus.queue import MessageBus
from nanobot.session.manager import SessionManager
from nanobot.agent.loop import AgentLoop


# ---------------------------------------------------------------------------
# Globals (initialized in lifespan)
# ---------------------------------------------------------------------------
agent: AgentLoop | None = None


def _make_provider(config):
    """Create LiteLLMProvider from config (mirrors nanobot CLI pattern)."""
    p = config.get_provider()
    model = config.agents.defaults.model
    if not (p and p.api_key) and not model.startswith("bedrock/"):
        raise RuntimeError(
            "No API key configured. Set one in ~/.nanobot/config.json"
        )
    return LiteLLMProvider(
        api_key=p.api_key if p else None,
        api_base=config.get_api_base(),
        default_model=model,
        extra_headers=p.extra_headers if p else None,
        provider_name=config.get_provider_name(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load config → create provider → create AgentLoop → start MCP."""
    global agent

    config = load_config()
    provider = _make_provider(config)
    bus = MessageBus()
    sessions = SessionManager(config.workspace_path)

    mcp_servers = (
        {n: c for n, c in config.mcp.servers.items() if c.enabled} or None
    )

    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=config.agents.defaults.model,
        brave_api_key=config.tools.web.search.api_key or None,
        exec_config=config.tools.exec,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        session_manager=sessions,
        mcp_servers=mcp_servers,
    )

    await agent.start_mcp()
    logger.info("Agent ready — model: {}", config.agents.defaults.model)

    yield

    await agent.stop_mcp()
    logger.info("Agent stopped")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Nanobot Relay Server", lifespan=lifespan)


@app.get("/api/health")
async def health():
    return {"status": "ok", "agent": agent is not None}


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    message = body.get("message", "")
    session_id = body.get("session_id") or str(uuid.uuid4())

    if not message:
        return JSONResponse(
            {"error": "message is required"}, status_code=400
        )

    try:
        reply = await agent.process_direct(
            content=message,
            session_key=f"m5stack:{session_id}",
            channel="m5stack",
            chat_id=session_id,
        )
    except Exception as e:
        logger.exception("process_direct failed")
        return JSONResponse({"error": str(e)}, status_code=500)

    return JSONResponse({"reply": reply, "session_id": session_id})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
