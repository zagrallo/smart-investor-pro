from fastapi import FastAPI, Depends, HTTPException, Response, Request, APIRouter, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from config import settings
from agents import InvestmentAgent
from compliance import ComplianceEngine
from reports import generate_pdf
import logging
import json as json_lib
import time
import asyncio
import uuid
import uvicorn


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
        }
        if hasattr(record, "corr_id"):
            log_entry["corr_id"] = record.corr_id
        if record.exc_info and record.exc_info[0]:
            log_entry["exc"] = self.formatException(record.exc_info)
        return json_lib.dumps(log_entry, default=str)


_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter())
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL), handlers=[_handler])
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    await compliance_engine.init_db()
    logger.info("Started", extra={"version": settings.VERSION, "mock": settings.USE_MOCK_DATA, "env": settings.APP_ENV})
    yield
    try:
        await compliance_engine.close()
        logger.info("Graceful shutdown complete")
    except Exception as e:
        logger.error("Shutdown error", extra={"error": str(e)})


app = FastAPI(title="Smart Investor Pro", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

v1 = APIRouter(prefix="/v1")

security = HTTPBearer()
agent = InvestmentAgent()
compliance_engine = ComplianceEngine()

BETA_USERS = {
    "beta-investor-1": {"role": "analyst", "name": "Demo Investor"}
}

def reset_rate_limits():
    global _request_log
    _request_log = {}

_request_log: dict[str, list[float]] = {}

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_access_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(creds.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id not in BETA_USERS:
            raise HTTPException(status_code=401, detail="User not authorized for beta access")
        return {"id": user_id, "role": BETA_USERS[user_id]["role"], "name": BETA_USERS[user_id]["name"]}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)
    client_ip = request.client.host
    now = time.time()
    _request_log[client_ip] = [t for t in _request_log.get(client_ip, []) if now - t < 60]
    if len(_request_log[client_ip]) >= settings.MAX_REQUESTS_PER_MINUTE:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please wait 60 seconds before retrying."}
        )
    _request_log.setdefault(client_ip, []).append(now)
    return await call_next(request)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    corr_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4())[:8])
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = corr_id
    return response


class AnalyzeRequest(BaseModel):
    idea: str = "Analyze Tesla Inc. (TSLA) as a long-term investment opportunity."


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    import os
    path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    with open(path, encoding="utf-8") as f:
        return f.read()

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "provider": "llm" if (settings.LLM_API_KEY or settings.DEEPSEEK_API_KEY) else "mock",
        "compliance": "EU/DE",
        "mock_mode": settings.USE_MOCK_DATA,
        "env": settings.APP_ENV
    }


@app.post("/auth/token", response_model=TokenResponse)
async def login():
    token = create_access_token({"sub": "beta-investor-1", "role": "analyst"})
    return TokenResponse(access_token=token)


@v1.post("/analyze")
async def analyze_v1(
    request: AnalyzeRequest,
    user: dict = Depends(get_current_user)
):
    logger.info("Analysis request", extra={"user": user["id"], "idea": request.idea[:80]})
    result = await agent.run_analysis(request.idea, user["id"])
    return {"status": "success", "data": result}


@v1.post("/upload")
async def upload_analysis_v1(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    if not file.filename or not file.filename.lower().endswith(".md"):
        raise HTTPException(400, "Nur .md Dateien werden unterstützt.")
    content = (await file.read()).decode("utf-8", errors="replace")
    idea = f"Analysiere die folgende Markdown-Datei '{file.filename}':\n\n{content[:4000]}"
    logger.info("Upload analysis", extra={"user": user["id"], "file": file.filename, "size": len(content)})
    result = await agent.run_analysis(idea, user["id"])
    return {"status": "success", "data": result, "file": file.filename}

@v1.get("/report/pdf")
async def pdf_report_v1(
    idea: str = "Analyze Tesla Inc. (TSLA)",
    user: dict = Depends(get_current_user)
):
    logger.info("PDF report request", extra={"user": user["id"]})
    result = await agent.run_analysis(idea, user["id"])
    pdf_bytes = await asyncio.to_thread(generate_pdf, result["memo"])
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={result['memo']['company_name'].replace(' ', '_')}_memo.pdf"
        }
    )


@v1.get("/audit")
async def audit_trail_v1(user: dict = Depends(get_current_user)):
    entries = await compliance_engine.get_audit_trail(user["id"])
    return {"user_id": user["id"], "total_analyses": len(entries), "entries": entries}


app.include_router(v1)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
