"""
Focused test suite for the streamlined Cold Mail Agent FastAPI backend.

Endpoints covered:
- GET  /           – Health check
- POST /query      – Autonomous AI agent query (with /run-agent alias)
- POST /send-email – Email sender (private .env or public caller credentials)

Run with:
    pytest tests/test_api.py -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

# Ensure root directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Patch env var before importing main (so the lifespan check passes)
os.environ.setdefault("GROQ_API_KEY", "test_fake_key_for_testing")

from main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


def _mock_groq(text: str):
    mock_msg = MagicMock()
    mock_msg.content = text
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    return mock_completion


# ─────────────────────────────────────────────
# 1. GET / (Health Check)
# ─────────────────────────────────────────────
class TestHealthCheck:
    def test_returns_200(self):
        r = client.get("/")
        assert r.status_code == 200

    def test_returns_ok_status(self):
        r = client.get("/")
        assert r.json()["status"] == "ok"
        assert "endpoints" in r.json()


# ─────────────────────────────────────────────
# 2. POST /query (Validation)
# ─────────────────────────────────────────────
class TestQueryValidation:
    def test_missing_all_fields_returns_422(self):
        r = client.post("/query", json={})
        assert r.status_code == 422

    def test_query_too_short_returns_422(self):
        r = client.post("/query", json={
            "query": "ab",
            "resume": "Software engineer with 2 years Python and machine learning background.",
        })
        assert r.status_code == 422

    def test_resume_too_short_returns_422(self):
        r = client.post("/query", json={
            "query": "AI startup internship",
            "resume": "short",
        })
        assert r.status_code == 422

    def test_blank_query_returns_422(self):
        r = client.post("/query", json={
            "query": "    ",
            "resume": "Software engineer with 2 years Python and machine learning background.",
        })
        assert r.status_code == 422

    def test_max_iterations_out_of_bounds_returns_422(self):
        r = client.post("/query", json={
            "query": "AI startup internship",
            "resume": "Software engineer with 2 years Python and machine learning background.",
            "max_iterations": 25,
        })
        assert r.status_code == 422


# ─────────────────────────────────────────────
# 3. POST /query (Execution & Alias)
# ─────────────────────────────────────────────
class TestQueryExecution:
    @patch("app.tools.search.search")
    @patch("app.tools.scraper.requests.get")
    @patch("app.tools.scraper.Groq")
    @patch("app.tools.email.Groq")
    @patch("app.agent.runner.Groq")
    def test_query_completes_successfully(
        self, mock_runner_groq, mock_email_groq, mock_scraper_groq, mock_requests, mock_search
    ):
        mock_search.return_value = iter(["https://example.com"])
        mock_requests.return_value = MagicMock(text="<html><body>Tech startup</body></html>")
        mock_scraper_groq.return_value.chat.completions.create.return_value = _mock_groq("Company info")
        mock_email_groq.return_value.chat.completions.create.return_value = _mock_groq("Draft")
        mock_runner_groq.return_value.chat.completions.create.return_value = _mock_groq(
            '{"answer": "Dear Hiring Team, here is my outreach email..."}'
        )

        r = client.post("/query", json={
            "query": "AI engineering internship",
            "resume": "Python and deep learning developer with open source contributions.",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "completed"
        assert "Dear Hiring Team" in data["final_answer"]
        assert len(data["events"]) > 0

    @patch("app.tools.search.search")
    @patch("app.agent.runner.Groq")
    def test_run_agent_alias_works(self, mock_runner_groq, mock_search):
        mock_search.return_value = iter([])
        mock_runner_groq.return_value.chat.completions.create.return_value = _mock_groq(
            '{"answer": "Done!"}'
        )
        r = client.post("/run-agent", json={
            "query": "Robotics startup",
            "resume": "Mechanical and firmware engineer with ROS experience.",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "completed"


# ─────────────────────────────────────────────
# 4. POST /send-email (Validation & Credentials)
# ─────────────────────────────────────────────
class TestSendEmail:
    def test_missing_fields_returns_422(self):
        r = client.post("/send-email", json={})
        assert r.status_code == 422

    def test_invalid_recipient_email_returns_422(self):
        r = client.post("/send-email", json={
            "to_email": "invalid-address",
            "subject": "Internship Inquiry",
            "body": "Hello hiring team, please consider my profile.",
        })
        assert r.status_code == 422

    def test_missing_credentials_returns_503(self):
        with patch.dict(os.environ, {"SENDER_EMAIL": "your_gmail@gmail.com", "SENDER_PASSWORD": "your_app_password_here"}):
            r = client.post("/send-email", json={
                "to_email": "hiring@company.com",
                "subject": "Internship Inquiry",
                "body": "Hello hiring team, please consider my profile.",
            })
            assert r.status_code == 503
            assert "Sender email is not configured" in r.json()["detail"]

    @patch("app.tools.email.emailsender.send_email")
    def test_public_user_credentials_in_request(self, mock_send):
        import json as _json
        mock_send.return_value = _json.dumps({"status": "success", "message": "Email sent"})

        r = client.post("/send-email", json={
            "to_email": "hiring@company.com",
            "subject": "Internship Application",
            "body": "Dear Team, I am reaching out to express my interest in the role.",
            "sender_email": "caller@mycompany.com",
            "sender_password": "app_specific_password_123",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "success"

    @patch("app.tools.email.emailsender.send_email")
    def test_smtp_error_returns_502(self, mock_send):
        import json as _json
        mock_send.return_value = _json.dumps({
            "status": "error",
            "error": "Authentication failed",
        })
        r = client.post("/send-email", json={
            "to_email": "hiring@company.com",
            "subject": "Internship Application",
            "body": "Dear Team, I am reaching out to express my interest in the role.",
            "sender_email": "caller@mycompany.com",
            "sender_password": "app_specific_password_123",
        })
        assert r.status_code == 502
        assert "SMTP error" in r.json()["detail"]


# ─────────────────────────────────────────────
# 5. Edge cases
# ─────────────────────────────────────────────
class TestEdgeCases:
    def test_wrong_content_type_returns_422(self):
        r = client.post(
            "/query",
            data="query=AI startup",
            headers={"Content-Type": "text/plain"},
        )
        assert r.status_code == 422

    def test_sql_injection_payload_in_query(self):
        with patch("app.tools.search.search") as mock_search, patch("app.agent.runner.Groq") as mock_groq_llm:
            mock_search.return_value = iter([])
            mock_groq_llm.return_value.chat.completions.create.return_value = _mock_groq('{"answer": "handled"}')
            r = client.post("/query", json={
                "query": "'; DROP TABLE users; --",
                "resume": "Python engineer with strong database security background.",
            })
            assert r.status_code == 200

    def test_xss_payload_in_query(self):
        with patch("app.tools.search.search") as mock_search, patch("app.agent.runner.Groq") as mock_groq_llm:
            mock_search.return_value = iter([])
            mock_groq_llm.return_value.chat.completions.create.return_value = _mock_groq('{"answer": "handled"}')
            r = client.post("/query", json={
                "query": "<script>alert('xss')</script>",
                "resume": "Frontend engineer with web application security background.",
            })
            assert r.status_code == 200

    def test_unsupported_method_returns_405(self):
        r = client.put("/query", json={"query": "AI startup"})
        assert r.status_code == 405

    def test_removed_endpoints_return_404(self):
        assert client.post("/search", json={"query": "AI"}).status_code == 404
        assert client.post("/research", json={"query": "AI"}).status_code == 404
        assert client.post("/scrape", json={"url": "http://x.com"}).status_code == 404
        assert client.get("/tools").status_code == 404
