# 🤖 Cold Mail Agent API

A streamlined AI agent backend built with **FastAPI** and **Groq (LLaMA/Qwen)**. It autonomously searches the web for job/internship opportunities, researches the target company, scrapes their website, and drafts a personalized cold outreach email tailored to your resume.

---

## ⚡ Streamlined Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Health check & connectivity verification |
| `POST` | `/query` | Main AI agent endpoint: search, scrape, and draft cold email |
| `POST` | `/send-email` | Optional email sender via SMTP (.env or user credentials) |

---

## 🚀 Backend Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the FastAPI server
uvicorn main:app --reload --port 8000
```

- **Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **API Base URL**: `http://127.0.0.1:8000`

---

## 📡 Frontend Integration Guide

### Base URL & CORS
- **Base URL**: `http://127.0.0.1:8000`
- **CORS**: Fully enabled (`allow_origins=["*"]`), allowing requests from `http://localhost:3000`, `http://localhost:5173`, or file origins.

### 1. Connection Check (`GET /`)
Check if the backend server is reachable.
```javascript
const res = await fetch("http://127.0.0.1:8000/");
const data = await res.json();
console.log(data.status); // "ok"
```

### 2. Generate Cold Email (`POST /query`)
Send your search query and resume. The agent searches Google/Bing, scrapes relevant pages, and generates a personalized draft.

**Request**:
```javascript
const response = await fetch("http://127.0.0.1:8000/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    query: "AI startup software engineer internship remote",
    resume: "Computer Science senior with 2 years of experience in Python, PyTorch, and FastAPI.",
    max_iterations: 8 // optional (default: 8)
  })
});
const result = await response.json();
```

**Response Format**:
```json
{
  "status": "completed",
  "iterations_used": 4,
  "final_answer": "Subject: Python Backend Engineer + Stripe Scale\n\nDear Hiring Team...",
  "events": [
    "LLM Response: ...",
    "Executing tool: search_jobs with args: ...",
    "Tool Output: [...]"
  ]
}
```

### 3. Send Email (`POST /send-email`)
Send the generated email directly to the recipient.

**Request (Private / Local Mode - credentials stored in server .env)**:
```javascript
await fetch("http://127.0.0.1:8000/send-email", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    to_email: "recruiting@targetcompany.com",
    subject: "Software Engineer Internship Inquiry",
    body: "Dear Hiring Team,\n\nI am reaching out..."
  })
});
```

**Request (Public Mode - caller supplies their Gmail & App Password)**:
```javascript
await fetch("http://127.0.0.1:8000/send-email", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    to_email: "recruiting@targetcompany.com",
    subject: "Software Engineer Internship Inquiry",
    body: "Dear Hiring Team,\n\nI am reaching out...",
    sender_email: "user@gmail.com",
    sender_password: "16_char_app_password"
  })
});
```

---

## 🧪 Run Tests

```bash
pytest tests/test_api.py -v
```
