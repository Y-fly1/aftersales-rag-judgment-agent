import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agents.graph import init_after_sales_graph
from app.core.config import settings
from app.core.exceptions import ApplicationError
from app.core.logging import configure_logging, get_logger
from app.infra.checkpointer import close_checkpointer, init_checkpointer
from app.modules.chat.router import router as chat_router
from app.modules.chat_thread.router import router as chat_thread_router
from app.modules.order.router import router as order_router
from app.modules.policy.router import router as policy_router
from app.modules.ticket.router import router as ticket_router

configure_logging(settings.logging.level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"【{settings.app.name}】应用启动中...")
    from app.infra.database import check_database, close_database
    from app.rag import close_rag

    await check_database()

    checkpointer = await init_checkpointer()
    app.state.agent = init_after_sales_graph(checkpointer)
    yield

    close_rag()
    await close_database()
    await close_checkpointer()


app = FastAPI(
    title=settings.app.name,
    debug=settings.app.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(policy_router)
app.include_router(order_router)
app.include_router(ticket_router)
app.include_router(chat_thread_router)
app.include_router(chat_router)


@app.get("/health", summary="健康检测接口")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(ApplicationError)
async def handle_application_error(request: Request, exc: ApplicationError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=False,
        loop="asyncio:SelectorEventLoop" if sys.platform == "win32" else "auto",
    )
