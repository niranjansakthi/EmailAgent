export function resolveApiBase(backendUrl) {
  const trimmed = (backendUrl || "").trim();
  if (trimmed) {
    return trimmed.replace(/\/+$/, "");
  }

  const fromEnv = import.meta.env.VITE_BACKEND_URL?.trim();
  if (fromEnv) {
    return fromEnv.replace(/\/+$/, "");
  }

  if (import.meta.env.DEV) {
    return "/api";
  }

  return "http://127.0.0.1:8000";
}

export function parseEmailDraft(finalAnswer) {
  if (!finalAnswer) {
    return { subject: "", body: "" };
  }

  const text = String(finalAnswer).trim();
  const subjectMatch = text.match(/^Subject:\s*(.+?)(?:\n\n|\n)/i);
  if (subjectMatch) {
    return {
      subject: subjectMatch[1].trim(),
      body: text.slice(subjectMatch[0].length).trim() || text,
    };
  }

  const lines = text.split("\n");
  if (lines[0] && lines[0].length < 120) {
    return {
      subject: lines[0].trim(),
      body: lines.slice(1).join("\n").trim(),
    };
  }

  return { subject: "Outreach draft", body: text };
}

export function normalizeAgentResponse(data) {
  if (!data) return null;

  const hasStructured = Boolean(data.subject && data.body);
  const parsed = hasStructured
    ? { subject: data.subject, body: data.body }
    : parseEmailDraft(data.final_answer);

  return {
    ...data,
    subject: parsed.subject,
    body: parsed.body,
  };
}
