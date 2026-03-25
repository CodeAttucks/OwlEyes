from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .auth import require_auth_if_enabled
from .routers import projects, fiber, reports, uploads, ml, base44_proxy, ai

app = FastAPI(dependencies=[Depends(require_auth_if_enabled)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bead-it.base44.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(fiber.router)
app.include_router(reports.router)
app.include_router(uploads.router)
app.include_router(ml.router)
app.include_router(base44_proxy.router)
app.include_router(ai.router)