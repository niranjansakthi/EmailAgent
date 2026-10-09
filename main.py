"""
FastAPI backend for the Cold Mail Agent.

Endpoints:
----------
GET  /           – Health check & backend connection verification
POST /query      – Run the AI agent to search, scrape, and draft outreach email
POST /send-email – Send the drafted email via SMTP (using .env or request credentials)
"""

import os
import json as _json
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

# Load .env FIRST so environment variables are available everywhere
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing from .env / environment.")
    print(f"GROQ_API_KEY loaded (starts with: {api_key[:10]}...)")
    yield
    print("Shutting down Cold Mail Agent API.")


from app.agent.runner import build_agent

app = FastAPI(
    title="Cold Mail Agent API",
    description=(
        "Autonomous AI agent that searches for job/internship opportunities, "
        "researches company websites, and generates personalized cold emails using Groq."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS so any frontend (React, Vite, Next.js, plain HTML) can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Pydantic Request Schemas with Input Validation
# ─────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=300,
        description="What to search for (e.g. 'AI startup software engineer internship remote')",
    )
    resume: str = Field(
        ...,
        min_length=20,
        max_length=5000,
        description="Your background or resume summary",
    )
    max_iterations: int = Field(
        default=8,
        ge=3,
        le=15,
        description="Maximum agent reasoning steps (default: 8)",
    )

    @field_validator("query", "resume")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be blank or whitespace only")
        return v.strip()


class SendEmailRequest(BaseModel):
    to_email: str = Field(
        ...,
        description="Recipient email address (e.g. hiring@company.com)",
    )
    subject: str = Field(..., min_length=2, max_length=200, description="Email subject line")
    body: str = Field(..., min_length=10, max_length=10000, description="Full email body text")
    sender_email: Optional[str] = Field(
        default=None,
        description="Optional sender email (falls back to backend .env SENDER_EMAIL if not provided)",
    )
    sender_password: Optional[str] = Field(
        default=None,
        description="Optional Gmail App Password (falls back to backend .env SENDER_PASSWORD if not provided)",
    )

    @field_validator("to_email")
    @classmethod
    def validate_email_address(cls, v: str) -> str:
        v = v.strip()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("to_email must be a valid address (e.g. user@domain.com)")
        return v.lower()

    @field_validator("subject", "body")
    @classmethod
    def not_blank_fields(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be blank")
        return v.strip()


# ─────────────────────────────────────────────
# Global Exception Handler
# ─────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def health_check():
    """
    Health check & connectivity verification endpoint.
    Used by frontend to check if backend server is online.
    """
    return {
        "status": "ok",
        "service": "Cold Mail Agent API",
        "version": "1.0.0",
        "endpoints": {
            "query": "POST /query",
            "send_email": "POST /send-email",
            "docs": "/docs",
        },
    }


@app.post("/query", tags=["Agent"])
@app.post("/run-agent", tags=["Agent"], include_in_schema=False)
async def run_cold_mail_agent(body: QueryRequest):
    """
    Run the autonomous AI agent.

    1. Searches the web based on your query.
    2. Identifies and researches the most relevant company/role.
    3. Scrapes the company website.
    4. Generates a personalized outreach email draft tailored to your resume.

    Returns the email draft, agent reasoning events, and execution status.
    """
    events: list[str] = []

    def capture_event(msg: str):
        events.append(msg)

    try:
        agent = build_agent(max_iterations=body.max_iterations)
        goal = (
            f"Find an internship or job opportunity matching: '{body.query}'. "
            "Search the web, pick the most relevant opportunity, scrape the company website, "
            "and write a high-impact personalized cold outreach email. "
            f"Candidate background / resume summary: {body.resume}"
        )
        final_state = agent.run(goal=goal, on_event=capture_event)

        # Parse final answer
        answer = None
        for msg in reversed(final_state.message):
            if msg.role == "assistant":
                try:
                    parsed = _json.loads(msg.content)
                    if "answer" in parsed:
                        answer = parsed["answer"]
                        break
                except Exception:
                    answer = msg.content
                    break

        return {
            "status": final_state.status.value if hasattr(final_state.status, "value") else str(final_state.status),
            "iterations_used": final_state.Iteration,
            "final_answer": answer,
            "events": events,
        }

    except EnvironmentError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


@app.post("/send-email", tags=["Email"])
async def send_email_endpoint(body: SendEmailRequest):
    """
    Send an email via SMTP.

    - **Private / Local Mode**: Leave sender_email and sender_password blank.
      Credentials will be read automatically from backend .env.
    - **Public Mode**: Pass sender_email and sender_password (Gmail App Password)
      in the request body.
    """
    sender_email = (body.sender_email or os.environ.get("SENDER_EMAIL", "")).strip()
    sender_pass = (body.sender_password or os.environ.get("SENDER_PASSWORD", "")).strip()

    if not sender_email or sender_email == "your_gmail@gmail.com":
        raise HTTPException(
            status_code=503,
            detail=(
                "Sender email is not configured. Either provide 'sender_email' in the request "
                "or set SENDER_EMAIL in the backend .env file."
            ),
        )
    if not sender_pass or sender_pass == "your_app_password_here":
        raise HTTPException(
            status_code=503,
            detail=(
                "Sender password is not configured. Either provide 'sender_password' (App Password) "
                "in the request or set SENDER_PASSWORD in the backend .env file."
            ),
        )

    from app.tools.email import emailsender

    try:
        sender = emailsender()
        result_str = sender.send_email(
            to_email=body.to_email,
            subject=body.subject,
            body=body.body,
            sender_email=sender_email,
            sender_password=sender_pass,
        )
        result = _json.loads(result_str)
        if result.get("status") == "error":
            raise HTTPException(status_code=502, detail=f"SMTP error: {result.get('error')}")
        return {
            "status": "success",
            "message": f"Email successfully sent to {body.to_email}",
            "subject": body.subject,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Send failed: {str(e)}")
