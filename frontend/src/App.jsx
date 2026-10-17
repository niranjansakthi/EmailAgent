import { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { Toaster, toast } from "sonner";
import {
  Activity,
  ArrowRight,
  Terminal,
  Zap,
  Search,
  Globe2,
  Cpu,
  Send,
  Copy,
  Loader2,
  Mail,
  Sparkles,
  ChevronDown,
  CircleDot,
  Radio,
} from "lucide-react";
import { GlyphGlobe } from "@/components/GlyphGlobe";
import { normalizeAgentResponse, resolveApiBase } from "@/lib/api";

const MODELS = [
  { id: "llama-3.3-70b", label: "Groq · LLaMA-3.3 70B" },
  { id: "qwen-2.5-72b", label: "Groq · Qwen 2.5 72B" },
  { id: "local-fallback", label: "Local Fallback" },
];

const BOOT_MESSAGES = [
  "Initializing agent runtime…",
  "Registering tools: search_jobs, research_job, scrape_job, write_email…",
  "Querying Groq LLM — agent is reasoning…",
  "Searching the web and scraping target pages…",
];

const StatusPill = ({ status }) => {
  const map = {
    online: {
      c: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
      t: "Online",
      dot: "bg-emerald-400",
    },
    running: {
      c: "text-cyan-400 border-cyan-500/40 bg-cyan-500/10",
      t: "Running",
      dot: "bg-cyan-400",
    },
    checking: {
      c: "text-amber-400 border-amber-500/40 bg-amber-500/10",
      t: "Pinging",
      dot: "bg-amber-400",
    },
    offline: {
      c: "text-red-400 border-red-500/40 bg-red-500/10",
      t: "Offline",
      dot: "bg-red-400",
    },
  };
  const s = map[status] || map.checking;
  return (
    <span
      data-testid="backend-status-indicator"
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-mono uppercase tracking-widest ${s.c}`}
    >
      <span className="relative flex h-2 w-2">
        <span
          className={`absolute inline-flex h-full w-full rounded-full ${s.dot} opacity-70 ${status === "online" || status === "running" ? "animate-ping" : ""}`}
        />
        <span className={`relative inline-flex h-2 w-2 rounded-full ${s.dot}`} />
      </span>
      API {s.t}
    </span>
  );
};

const Field = ({ children }) => <div className="space-y-1.5">{children}</div>;
const labelCls = "text-[11px] font-mono uppercase tracking-widest text-emerald-400/80";
const inputCls =
  "w-full rounded-lg border border-slate-700/70 bg-slate-950/60 px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 outline-none transition focus:border-emerald-500/60 focus:ring-2 focus:ring-emerald-500/20";

function App() {
  const [backendUrl, setBackendUrl] = useState("");
  const apiBase = useMemo(() => resolveApiBase(backendUrl), [backendUrl]);

  const [status, setStatus] = useState("checking");
  const [model, setModel] = useState(MODELS[0].id);
  const [query, setQuery] = useState("AI startup backend engineer internship remote");
  const [resume, setResume] = useState(
    "Computer Science senior with 2 years building production systems in Python, FastAPI and React. Shipped ML features with PyTorch.",
  );
  const [companyUrl, setCompanyUrl] = useState("");
  const [iterations, setIterations] = useState(8);
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState([]);
  const [result, setResult] = useState(null);
  const [emailTo, setEmailTo] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [emailBody, setEmailBody] = useState("");
  const [senderEmail, setSenderEmail] = useState("");
  const [senderPassword, setSenderPassword] = useState("");
  const [showCredentials, setShowCredentials] = useState(false);
  const [sending, setSending] = useState(false);
  const timelineRef = useRef(null);
  const bootTimerRef = useRef(null);

  const headerStatus = running ? "running" : status;

  useEffect(() => {
    let active = true;
    const ping = async () => {
      if (running) return;
      try {
        const r = await axios.get(`${apiBase}/`, { timeout: 8000 });
        if (active) setStatus(r.data?.status === "ok" ? "online" : "offline");
      } catch {
        if (active) setStatus("offline");
      }
    };
    ping();
    const id = setInterval(ping, 15000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [apiBase, running]);

  useEffect(() => {
    if (timelineRef.current) {
      timelineRef.current.scrollTop = timelineRef.current.scrollHeight;
    }
  }, [events]);

  useEffect(() => {
    return () => {
      if (bootTimerRef.current) clearInterval(bootTimerRef.current);
    };
  }, []);

  const scrollToWorkspace = () => {
    document.getElementById("workspace")?.scrollIntoView({ behavior: "smooth" });
    setTimeout(() => document.querySelector('[data-testid="input-job-query"]')?.focus(), 650);
  };

  const startBootStream = () => {
    let idx = 0;
    setEvents([{ text: BOOT_MESSAGES[0], ts: Date.now(), boot: true }]);
    idx = 1;
    bootTimerRef.current = setInterval(() => {
      if (idx >= BOOT_MESSAGES.length) return;
      setEvents((prev) => [...prev, { text: BOOT_MESSAGES[idx], ts: Date.now(), boot: true }]);
      idx += 1;
    }, 2800);
  };

  const stopBootStream = () => {
    if (bootTimerRef.current) {
      clearInterval(bootTimerRef.current);
      bootTimerRef.current = null;
    }
  };

  const runAgent = async () => {
    if (!query.trim()) {
      toast.error("Enter a search query to launch the agent.");
      return;
    }
    if (!resume.trim() || resume.trim().length < 20) {
      toast.error("Resume summary must be at least 20 characters.");
      return;
    }

    setRunning(true);
    setEvents([]);
    setResult(null);
    startBootStream();

    const effectiveQuery = companyUrl.trim()
      ? `${query.trim()} (prioritize company site: ${companyUrl.trim()})`
      : query.trim();

    try {
      const res = await axios.post(
        `${apiBase}/query`,
        {
          query: effectiveQuery,
          resume: resume.trim(),
          max_iterations: iterations,
        },
        { timeout: 600000 },
      );

      stopBootStream();
      const normalized = normalizeAgentResponse(res.data);
      const evs = normalized?.events || [];

      for (let i = 0; i < evs.length; i++) {
        await new Promise((r) => setTimeout(r, 420));
        setEvents((prev) => [...prev, { text: evs[i], ts: Date.now() }]);
      }

      setResult(normalized);
      setEmailSubject(normalized.subject || "");
      setEmailBody(normalized.body || "");
      toast.success(
        `Draft ready · ${normalized.status} · ${normalized.iterations_used ?? "?"} steps`,
      );
    } catch (e) {
      stopBootStream();
      const detail = e.response?.data?.detail;
      const message = detail || e.message || "Unknown error";
      toast.error("Agent run failed. Is the backend reachable?");
      setEvents((prev) => [...prev, { text: `Error: ${message}`, ts: Date.now(), err: true }]);
    } finally {
      setRunning(false);
    }
  };

  const copyEmail = () => {
    const text = `Subject: ${emailSubject}\n\n${emailBody}`;
    navigator.clipboard.writeText(text);
    toast.success("Email copied to clipboard");
  };

  const sendEmail = async () => {
    if (!emailTo.trim()) {
      toast.error("Add a recipient email address.");
      return;
    }
    setSending(true);
    try {
      const payload = {
        to_email: emailTo.trim(),
        subject: emailSubject,
        body: emailBody,
      };
      if (senderEmail.trim()) {
        payload.sender_email = senderEmail.trim();
      }
      if (senderPassword.trim()) {
        payload.sender_password = senderPassword.trim();
      }
      const r = await axios.post(`${apiBase}/send-email`, payload);
      toast.success(r.data?.message || "Email sent successfully.");
    } catch (e) {
      const detail = e.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Send failed.", {
        duration: 8000,
      });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="dark min-h-screen bg-[#080B11] font-sans text-slate-100 antialiased selection:bg-emerald-500/30">
      <Toaster theme="dark" position="top-right" richColors />

      <header className="sticky top-0 z-40 border-b border-slate-800/70 bg-[#080B11]/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <div className="grid h-8 w-8 place-items-center rounded-lg border border-emerald-500/30 bg-emerald-500/10">
              <Mail className="h-4 w-4 text-emerald-400" />
            </div>
            <span className="font-display text-base font-bold tracking-tight">
              ColdMail<span className="text-emerald-400">Agent</span>
            </span>
          </div>
          <div className="flex items-center gap-3">
            <StatusPill status={headerStatus} />
            <button
              type="button"
              data-testid="nav-enter-btn"
              onClick={scrollToWorkspace}
              className="hidden items-center gap-1.5 rounded-lg border border-slate-700 px-3.5 py-1.5 text-sm font-medium text-slate-200 transition hover:border-emerald-500/50 hover:text-emerald-400 sm:inline-flex"
            >
              Workspace <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </header>

      <section className="cma-grid-bg relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(16,185,129,0.12),transparent_55%)]" />
        <div className="mx-auto grid max-w-[1600px] items-center gap-10 px-5 py-16 lg:grid-cols-2 lg:py-24">
          <div className="cma-rise">
            <span className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/5 px-3 py-1 text-xs font-mono uppercase tracking-widest text-emerald-400">
              <Sparkles className="h-3.5 w-3.5" /> Autonomous Outreach Engine
            </span>
            <h1 className="mt-6 font-display text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
              Cold emails that
              <span className="block bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
                write themselves.
              </span>
            </h1>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-400">
              An AI agent that searches the web for opportunities, scrapes the target company,
              matches your resume, and drafts a personalized cold outreach email — end to end.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <button
                type="button"
                data-testid="enter-now-cta"
                onClick={scrollToWorkspace}
                className="group inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 text-sm font-semibold text-[#06281f] shadow-[0_0_30px_rgba(16,185,129,0.35)] transition hover:bg-emerald-400 hover:shadow-[0_0_40px_rgba(16,185,129,0.5)] focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:ring-offset-2 focus:ring-offset-[#080B11]"
              >
                Enter Now
                <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
              </button>
              <a
                href="#workspace"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-5 py-3.5 text-sm font-medium text-slate-300 transition hover:border-slate-500"
              >
                <Terminal className="h-4 w-4 text-emerald-400" /> View live agent
              </a>
            </div>
            <div className="mt-10 flex flex-wrap gap-6 text-sm text-slate-500">
              {[["Search", Search], ["Scrape", Globe2], ["Reason", Cpu], ["Draft", Mail]].map(
                ([t, Icon], i) => (
                  <div key={t} className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-emerald-400/70" />
                    <span className="font-mono text-xs uppercase tracking-wider">
                      {i + 1}. {t}
                    </span>
                  </div>
                ),
              )}
            </div>
          </div>

          <div className="cma-rise" style={{ animationDelay: "0.12s" }}>
            <div className="relative flex h-[380px] w-full items-center justify-center overflow-hidden rounded-2xl border border-emerald-500/20 bg-slate-950/60 shadow-[0_0_60px_rgba(16,185,129,0.1)] md:h-[480px]">
              <GlyphGlobe />
              <div className="pointer-events-none absolute bottom-4 left-4 rounded-lg border border-slate-700/60 bg-slate-950/70 px-3 py-2 font-mono text-[11px] text-slate-400 backdrop-blur">
                <span className={running ? "text-cyan-400" : "text-emerald-400"}>●</span> agent.core
                — {running ? "running" : status}
              </div>
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={scrollToWorkspace}
          className="mx-auto mb-6 flex items-center gap-1.5 text-xs font-mono uppercase tracking-widest text-slate-500 transition hover:text-emerald-400"
        >
          Scroll to workspace <ChevronDown className="h-4 w-4 animate-bounce" />
        </button>
      </section>

      <section id="workspace" className="border-t border-slate-800/70 bg-[#080B11]">
        <div className="mx-auto max-w-[1600px] px-4 py-10 sm:px-6">
          <div className="mb-6 flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-4 backdrop-blur md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3">
              <Activity className="h-5 w-5 text-emerald-400" />
              <div>
                <h2 className="font-display text-lg font-bold">Agent Workspace</h2>
                <p className="text-xs text-slate-500">Autonomous search → scrape → draft pipeline</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950/60 px-2.5 py-1.5">
                <Cpu className="h-4 w-4 text-cyan-400" />
                <select
                  data-testid="model-selector"
                  value={model}
                  onChange={(e) => {
                    setModel(e.target.value);
                    toast.message(
                      `UI model: ${MODELS.find((m) => m.id === e.target.value)?.label} (server uses GROQ_MODEL in .env)`,
                    );
                  }}
                  className="bg-transparent text-sm text-slate-200 outline-none"
                >
                  {MODELS.map((m) => (
                    <option key={m.id} value={m.id} className="bg-slate-900">
                      {m.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-1.5 font-mono text-xs text-slate-400">
                <Zap className="h-3.5 w-3.5 text-amber-400" /> ~
                {result ? 180 + (result.iterations_used || 0) * 24 : 0} tok/s
              </div>
              <StatusPill status={headerStatus} />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            <div
              data-testid="agent-input-form"
              className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur lg:col-span-4"
            >
              <div className="flex items-center gap-2">
                <Radio className="h-4 w-4 text-emerald-400" />
                <h3 className="font-display text-base font-semibold">Mission Control</h3>
              </div>
              <Field>
                <label className={labelCls} htmlFor="backend-url">
                  API Base URL (optional)
                </label>
                <input
                  id="backend-url"
                  data-testid="input-backend-url"
                  className={inputCls}
                  value={backendUrl}
                  onChange={(e) => setBackendUrl(e.target.value)}
                  placeholder=""
                />
                <p className="text-[11px] text-slate-500">
                  Leave blank to use the local proxy ({import.meta.env.DEV ? "/api → :8000" : "127.0.0.1:8000"}).
                </p>
              </Field>
              <Field>
                <label className={labelCls} htmlFor="job-query">
                  Target Opportunity Query
                </label>
                <input
                  id="job-query"
                  data-testid="input-job-query"
                  className={inputCls}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g. AI startup backend internship remote"
                />
              </Field>
              <Field>
                <label className={labelCls} htmlFor="resume-text">
                  Your Resume / Summary
                </label>
                <textarea
                  id="resume-text"
                  data-testid="input-resume-text"
                  rows={5}
                  className={`${inputCls} resize-none`}
                  value={resume}
                  onChange={(e) => setResume(e.target.value)}
                  placeholder="Paste a short resume summary..."
                />
              </Field>
              <Field>
                <label className={labelCls} htmlFor="company-url">
                  Target Company URL (optional)
                </label>
                <input
                  id="company-url"
                  data-testid="input-company-url"
                  className={inputCls}
                  value={companyUrl}
                  onChange={(e) => setCompanyUrl(e.target.value)}
                  placeholder="https://company.com"
                />
              </Field>
              <Field>
                <label className={labelCls} htmlFor="max-iterations">
                  Max Iterations · {iterations}
                </label>
                <input
                  id="max-iterations"
                  data-testid="input-max-iterations"
                  type="range"
                  min={3}
                  max={15}
                  value={iterations}
                  onChange={(e) => setIterations(Number(e.target.value))}
                  className="w-full accent-emerald-500"
                />
              </Field>
              <button
                type="button"
                data-testid="launch-agent-button"
                onClick={runAgent}
                disabled={running}
                className="group inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-[#06281f] shadow-[0_0_24px_rgba(16,185,129,0.3)] transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {running ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> Running agent…
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4" /> Run Autonomous Agent
                  </>
                )}
              </button>
            </div>

            <div
              data-testid="agent-event-timeline"
              className="rounded-2xl border border-slate-800 bg-slate-900/40 backdrop-blur lg:col-span-8"
            >
              <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
                <div className="flex items-center gap-2">
                  <Terminal className="h-4 w-4 text-cyan-400" />
                  <h3 className="font-display text-base font-semibold">Execution Timeline</h3>
                </div>
                <span className="font-mono text-xs text-slate-500">{events.length} events</span>
              </div>
              <div
                ref={timelineRef}
                className="h-[360px] overflow-y-auto p-5 font-mono text-[13px] leading-relaxed"
              >
                {events.length === 0 && !running && (
                  <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-slate-600">
                    <CircleDot className="h-8 w-8 text-slate-700" />
                    <p>Agent idle. Launch a mission to stream live execution logs.</p>
                  </div>
                )}
                {running && events.length === 0 && (
                  <div className="flex items-center gap-2 text-emerald-400">
                    <Loader2 className="h-4 w-4 animate-spin" /> Booting agent runtime…
                  </div>
                )}
                <ul className="space-y-2.5">
                  {events.map((e, i) => (
                    <li key={`${e.ts}-${i}`} className="cma-rise flex gap-3">
                      <span className="shrink-0 text-slate-600">{String(i + 1).padStart(2, "0")}</span>
                      <span
                        className={
                          e.err
                            ? "text-red-400"
                            : e.boot
                              ? "text-slate-400 italic"
                              : e.text.startsWith("Executing tool")
                                ? "text-amber-300"
                                : e.text.startsWith("Tool Output")
                                  ? "text-cyan-300"
                                  : e.text.startsWith("Final Answer")
                                    ? "text-emerald-400"
                                    : "text-slate-300"
                        }
                      >
                        {e.text}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div
              data-testid="email-result-viewer"
              className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur lg:col-span-7"
            >
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-emerald-400" />
                  <h3 className="font-display text-base font-semibold">Cold Email Draft</h3>
                </div>
                <button
                  type="button"
                  data-testid="copy-email-button"
                  onClick={copyEmail}
                  disabled={!result}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-emerald-500/50 hover:text-emerald-400 disabled:opacity-40"
                >
                  <Copy className="h-3.5 w-3.5" /> Copy
                </button>
              </div>
              {result ? (
                <div className="space-y-3">
                  <div className="font-mono text-[11px] uppercase tracking-widest text-slate-500">
                    Agent status{" "}
                    <span className="text-emerald-400">{result.status}</span>
                    {result.iterations_used != null && (
                      <span> · {result.iterations_used} iterations</span>
                    )}
                  </div>
                  <div
                    data-testid="generated-subject"
                    className="rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2.5 text-sm"
                  >
                    <span className="font-mono text-[11px] uppercase tracking-widest text-slate-500">
                      Subject
                    </span>
                    <p className="mt-0.5 font-medium text-slate-100">{result.subject}</p>
                  </div>
                  <pre
                    data-testid="generated-body"
                    className="max-h-[260px] overflow-y-auto whitespace-pre-wrap rounded-lg border border-slate-700 bg-slate-950/60 px-4 py-3 text-sm leading-relaxed text-slate-300"
                  >
                    {result.body}
                  </pre>
                </div>
              ) : (
                <div className="flex h-[300px] flex-col items-center justify-center gap-3 text-center text-slate-600">
                  <Sparkles className="h-8 w-8 text-slate-700" />
                  <p className="text-sm">Your personalized draft will appear here after a run.</p>
                </div>
              )}
            </div>

            <div
              data-testid="send-email-panel"
              className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur lg:col-span-5"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Send className="h-4 w-4 text-cyan-400" />
                  <h3 className="font-display text-base font-semibold">Dispatch</h3>
                </div>
                <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-widest text-amber-400">
                  SMTP
                </span>
              </div>
              <Field>
                <label className={labelCls} htmlFor="email-to">
                  To
                </label>
                <input
                  id="email-to"
                  data-testid="email-to-input"
                  className={inputCls}
                  value={emailTo}
                  onChange={(e) => setEmailTo(e.target.value)}
                  placeholder="recruiting@company.com"
                />
              </Field>
              <Field>
                <label className={labelCls} htmlFor="email-subject">
                  Subject
                </label>
                <input
                  id="email-subject"
                  data-testid="email-subject-input"
                  className={inputCls}
                  value={emailSubject}
                  onChange={(e) => setEmailSubject(e.target.value)}
                  placeholder="Subject line"
                />
              </Field>
              <Field>
                <label className={labelCls} htmlFor="email-body">
                  Body
                </label>
                <textarea
                  id="email-body"
                  data-testid="email-body-input"
                  rows={6}
                  className={`${inputCls} resize-none`}
                  value={emailBody}
                  onChange={(e) => setEmailBody(e.target.value)}
                  placeholder="Email body"
                />
              </Field>

              <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-3">
                <button
                  type="button"
                  onClick={() => setShowCredentials(!showCredentials)}
                  className="flex w-full items-center justify-between text-left font-mono text-[11px] uppercase tracking-wider text-slate-400 hover:text-slate-200"
                >
                  <span>Custom Sender / App Password (Optional)</span>
                  <span className="text-cyan-400">{showCredentials ? "− Hide" : "+ Expand"}</span>
                </button>
                {showCredentials && (
                  <div className="mt-3 space-y-3 border-t border-slate-800/60 pt-3">
                    <Field>
                      <label className={labelCls} htmlFor="sender-email">
                        Sender Gmail
                      </label>
                      <input
                        id="sender-email"
                        className={inputCls}
                        value={senderEmail}
                        onChange={(e) => setSenderEmail(e.target.value)}
                        placeholder="your_email@gmail.com"
                      />
                    </Field>
                    <Field>
                      <label className={labelCls} htmlFor="sender-password">
                        16-Character App Password
                      </label>
                      <input
                        id="sender-password"
                        type="password"
                        className={inputCls}
                        value={senderPassword}
                        onChange={(e) => setSenderPassword(e.target.value)}
                        placeholder="abcd efgh ijkl mnop"
                      />
                    </Field>
                    <p className="text-[10px] text-slate-500">
                      Generate from Google Account &gt; Security &gt; App passwords.
                    </p>
                  </div>
                )}
              </div>

              <button
                type="button"
                data-testid="send-email-button"
                onClick={sendEmail}
                disabled={sending}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-cyan-500/40 bg-cyan-500/10 px-5 py-3 text-sm font-semibold text-cyan-300 transition hover:bg-cyan-500/20 disabled:opacity-60"
              >
                {sending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> Sending…
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4" /> Send Cold Email
                  </>
                )}
              </button>
              <p className="text-[11px] leading-relaxed text-slate-500">
                If custom credentials above are blank, the backend automatically uses SENDER_EMAIL and SENDER_PASSWORD from .env.
              </p>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-slate-800/70 py-6 text-center">
        <p className="font-mono text-xs text-slate-600">
          Cold Mail Agent · FastAPI backend · {apiBase}
        </p>
      </footer>
    </div>
  );
}

export default App;
