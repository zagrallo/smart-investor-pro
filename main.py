from fastapi import FastAPI, Depends, HTTPException, Response, Request, APIRouter, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from config import settings
from agents import InvestmentAgent
from startup_dd import StartupAgent
from compliance import ComplianceEngine
from reports import generate_pdf
from startup_dd.reports import generate_startup_pdf
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
    logger.info("Started", extra={"version": settings.VERSION, "mock": settings.USE_MOCK_DATA, "env": settings.APP_ENV, "cache_enabled": settings.CACHE_ENABLED})
    yield
    try:
        from startup_dd.cache import get_cache
        await get_cache().close()
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
startup_agent = StartupAgent()
compliance_engine = ComplianceEngine()

BETA_USERS = {
    "beta-investor-1": {"role": "analyst", "name": "Demo Investor"}
}

def reset_rate_limits():
    global _request_log
    _request_log = {}

_request_log: dict[str, dict] = {}

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
    tokens = _request_log.get(client_ip)
    if tokens is None:
        _request_log[client_ip] = {"tokens": settings.MAX_REQUESTS_PER_MINUTE - 1, "last_refill": now}
        return await call_next(request)
    elapsed = now - tokens["last_refill"]
    tokens["tokens"] = min(settings.MAX_REQUESTS_PER_MINUTE, tokens["tokens"] + elapsed * (settings.MAX_REQUESTS_PER_MINUTE / 60))
    tokens["last_refill"] = now
    if tokens["tokens"] < 1:
        wait = int((1 - tokens["tokens"]) * 60 / settings.MAX_REQUESTS_PER_MINUTE) + 1
        return JSONResponse(
            status_code=429,
            content={"detail": f"Too many requests. Retry in {wait}s."}
        )
    tokens["tokens"] -= 1
    return await call_next(request)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    corr_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4())[:8])
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = corr_id
    return response


class AnalyzeRequest(BaseModel):
    idea: str = "Analyze Tesla Inc. (TSLA) as a long-term investment opportunity."

class StartupAnalyzeRequest(BaseModel):
    company: str
    document: str


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    import os
    path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    with open(path, encoding="utf-8") as f:
        return f.read()

@app.get("/health")
async def health():
    from startup_dd.cache import get_cache
    cache = get_cache()
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "provider": "llm" if (settings.LLM_API_KEY or settings.DEEPSEEK_API_KEY) else "mock",
        "compliance": "EU/DE",
        "mock_mode": settings.USE_MOCK_DATA,
        "env": settings.APP_ENV,
        "multi_llm": agent.llm.health(),
        "parallel": settings.PARALLEL_ANALYSIS,
        "rate_limiter": "token_bucket",
        "rate_limit": f"{settings.MAX_REQUESTS_PER_MINUTE}/min",
        "cache": cache.summary(),
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
    idea = f"Analysiere die folgende Markdown-Datei '{file.filename}':\n\n{content[:32000]}"
    logger.info("Upload analysis", extra={"user": user["id"], "file": file.filename, "size": len(content)})
    result = await agent.run_analysis(idea, user["id"])
    return {"status": "success", "data": result, "file": file.filename}

@v1.get("/report/pdf")
async def pdf_report_v1(
    idea: str = "Analyze Tesla Inc. (TSLA)",
    user: dict = Depends(get_current_user)
):
    logger.info("PDF report request", extra={"user": user["id"]})
    try:
        result = await agent.run_analysis(idea, user["id"])
        if not result or "memo" not in result:
            raise HTTPException(status_code=500, detail="Analysis returned no memo")
        pdf_bytes = await asyncio.to_thread(generate_pdf, result["memo"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error("PDF report failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
    company = result["memo"].get("company_name", "Investment")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={company.replace(' ', '_')}_memo.pdf"
        }
    )


class StartupPdfRequest(BaseModel):
    memo: dict

@v1.post("/report/startup-pdf")
async def startup_pdf_report_v1(
    request: StartupPdfRequest,
    user: dict = Depends(get_current_user)
):
    memo = request.memo
    if not memo or not memo.get("company_name"):
        raise HTTPException(status_code=400, detail="Memo must contain at least 'company_name'")
    logger.info("Startup PDF report request", extra={"user": user["id"], "company": memo.get("company_name")})
    try:
        pdf_bytes = await asyncio.to_thread(generate_startup_pdf, memo)
    except Exception as e:
        logger.error("Startup PDF generation failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
    company = memo.get("company_name", "Startup")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={company.replace(' ', '_')}_memo.pdf"
        }
    )

@v1.post("/analyze/startup")
async def analyze_startup_v1(
    request: StartupAnalyzeRequest,
    user: dict = Depends(get_current_user)
):
    logger.info("Startup DD request", extra={"user": user["id"], "company": request.company})
    result = await startup_agent.analyze(request.company, request.document, session_id=user["id"])
    return {"status": "success", "data": result, "mode": "startup_dd"}


@v1.post("/upload/startup")
async def upload_startup_v1(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    if not file.filename or not file.filename.lower().endswith(".md"):
        raise HTTPException(400, "Nur .md Dateien werden unterstützt.")
    content = (await file.read()).decode("utf-8", errors="replace")
    company_name = file.filename.replace("-INVESTOR-DOKUMENT.md", "").replace(".md", "").strip()
    logger.info("Startup DD upload", extra={"user": user["id"], "file": file.filename, "size": len(content)})
    result = await startup_agent.analyze(company_name, content, session_id=user["id"])
    return {"status": "success", "data": result, "file": file.filename, "mode": "startup_dd"}


@v1.post("/cache/clear")
async def clear_cache_v1(user: dict = Depends(get_current_user)):
    from startup_dd.cache import get_cache
    await get_cache().clear()
    return {"status": "cache_cleared"}


@v1.get("/cost")
async def session_cost_v1(user: dict = Depends(get_current_user)):
    from startup_dd.cache import get_cache
    cost = agent.llm.get_session_cost(user["id"])
    startup_cost = startup_agent.llm.get_session_cost(user["id"])
    return {
        "user_id": user["id"],
        "investment_agent_cost": round(cost, 6),
        "startup_dd_cost": round(startup_cost, 6),
        "total_cost": round(cost + startup_cost, 6),
        "budget": settings.LLM_COST_BUDGET,
        "budget_remaining": round(settings.LLM_COST_BUDGET - cost - startup_cost, 6),
        "parallel_mode": settings.PARALLEL_ANALYSIS,
        "cache": get_cache().summary(),
    }


@v1.get("/audit")
async def audit_trail_v1(user: dict = Depends(get_current_user)):
    entries = await compliance_engine.get_audit_trail(user["id"])
    return {"user_id": user["id"], "total_analyses": len(entries), "entries": entries}


app.include_router(v1)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
