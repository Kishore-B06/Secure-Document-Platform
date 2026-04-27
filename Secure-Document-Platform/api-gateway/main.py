from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests
import os


load_dotenv()

AUTH_SERVICE = os.getenv("AUTH_SERVICE_URL")
DOC_SERVICE = os.getenv("DOCUMENT_SERVICE_URL")
SIM_SERVICE = os.getenv("SIMILARITY_SERVICE_URL")
VER_SERVICE = os.getenv("VERIFICATION_SERVICE_URL")
REP_SERVICE = os.getenv("REPORT_SERVICE_URL")

app = FastAPI(title="Secure Document Platform - API Gateway")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================
# CORE PROXY FUNCTION
# ==========================

async def proxy(service_url: str, path: str, request: Request):
    url = f"{service_url}{path}"

    try:
        body = await request.body()

        response = requests.request(
            method=request.method,              # 🔥 preserves GET/POST/DELETE
            url=url,
            headers=dict(request.headers),      # forward headers
            data=body,                          # forward body
            params=request.query_params,        # forward query params
        )

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )

    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Service unavailable")


# ==========================
# ROUTES
# ==========================

@app.api_route("/auth/{path:path}", methods=["GET", "POST"])
async def auth_proxy(path: str, request: Request):
    return await proxy(AUTH_SERVICE, f"/{path}", request)


@app.api_route("/documents/{path:path}", methods=["GET", "POST", "DELETE"])
async def document_proxy(path: str, request: Request):
    return await proxy(DOC_SERVICE, f"/{path}", request)


@app.api_route("/similarity/{path:path}", methods=["GET", "POST"])
async def similarity_proxy(path: str, request: Request):
    return await proxy(SIM_SERVICE, f"/{path}", request)


@app.api_route("/verification/{path:path}", methods=["GET"])
async def verification_proxy(path: str, request: Request):
    return await proxy(VER_SERVICE, f"/{path}", request)


@app.api_route("/report/{path:path}", methods=["GET"])
async def report_proxy(path: str, request: Request):
    return await proxy(REP_SERVICE, f"/{path}", request)