from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import init_logging
from app.core.errors import api_error_handler, ApiError
from app.api.v1.routes import router as v1_router

app = FastAPI(title="Common Investor API", version="0.1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_logging(app)
app.include_router(v1_router, prefix="/api/v1")
app.add_exception_handler(ApiError, api_error_handler)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}