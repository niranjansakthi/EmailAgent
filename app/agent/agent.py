import json
from typing import List, Any, Callable, Optional, Protocol

from app.tools.registry import Toolregister
from app.agent.models import Agentstate, IterationStatus, ChatMessage


class LLMClient(Protocol):
    def invoke(self, messages: List[dict]) -> str:
        ...


class AgentRunner:
    """ReAct-style agentic loop that orchestrates LLM + tools."""

    def __init__(
        self,
        llm: LLMClient,
        tool_registry: Toolregister,
        max_iterations: int = 8,
    ) -> None:
        self.llm = llm
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations

    def run(
        self,
        goal: str,
        on_event: Optional[Callable[[str], Any]] = None,
    ) -> Agentstate:
        state = Agentstate(goal=goal, status=IterationStatus.RUNNING)
        state.message.append(ChatMessage(role="user", content=goal))
        seen_calls = set()

        tool_descriptions = "\n".join(
            f"- {name}: {tool.description}"
            for name, tool in self.tool_registry.tools.items()
        )

        system_instruction = (
            f"Your Goal: {state.goal}\n\n"
            f"Available Tools:\n{tool_descriptions}\n\n"
            "RESPONSE FORMAT (Strict pure JSON, no markdown code fences, no extra text):\n"
            "To call a tool:  {\"tool\": \"tool_name\", \"arguments\": {\"param_name\": \"value\"}}\n"
            "When done:       {\n"
            "  \"answer\": \"Recipient: <recruiter_email>\\nSubject: <subject>\\n\\nDear <Hiring Team/Name>,\\n\\n<Email Body>\",\n"
            "  \"recipient_email\": \"careers@company.com\",\n"
            "  \"subject\": \"<Subject Line>\",\n"
            "  \"body\": \"<Email Body>\"\n"
            "}\n\n"
            "CRITICAL RULES ON RECRUITER EMAIL:\n"
            "- It is YOUR JOB to extract or infer the recruiter/careers email from the company website (e.g. careers@company.com or recruiting@company.com).\n"
            "- NEVER ASK THE USER FOR THE RECRUITER EMAIL!\n"
            "- Always include the recipient_email in your final response.\n\n"
            "WORKFLOW GUIDELINES (Complete in 3 fast steps):\n"
            "1. Search once with 'search_jobs' to find opportunities.\n"
            "2. Pick the best URL from the search results and scrape it ONCE with 'scrap_job'.\n"
            "3. Immediately write the cold email draft and return your final answer.\n\n"
            "RULES:\n"
            "- Never call 'search_jobs' more than once.\n"
            "- Never repeat the exact same tool call.\n"
            "- Once you have scraped company info, do NOT do more research. Immediately return your final answer."
        )

        while state.Iteration < self.max_iterations:
            state.Iteration += 1

            messages_for_llm = [{"role": "system", "content": system_instruction}]
            messages_for_llm.extend(
                [{"role": m.role, "content": m.content} for m in state.message]
            )

            # If approaching iteration limit, nudge agent to finish
            if state.Iteration >= self.max_iterations - 1:
                messages_for_llm.append({
                    "role": "user",
                    "content": (
                        "Time limit approaching. Please stop calling tools and immediately "
                        "return your final personalized cold outreach email draft in {\"answer\": \"...\"}."
                    ),
                })

            try:
                response_str = self.llm.invoke(messages_for_llm)
                state.message.append(ChatMessage(role="assistant", content=response_str))

                if on_event:
                    on_event(f"LLM Response: {response_str}")

                # Strip markdown code fences if the LLM wraps JSON in them
                clean = response_str.strip()
                if clean.startswith("```"):
                    clean = clean.split("```")[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                clean = clean.strip()

                try:
                    parsed = json.loads(clean)
                except json.JSONDecodeError:
                    # Non-JSON final answer — treat as completed
                    state.status = IterationStatus.COMPLETED
                    if on_event:
                        on_event(f"Non-JSON response treated as final: {response_str}")
                    break

                if "tool" in parsed:
                    tool_name = parsed["tool"]
                    args = parsed.get("arguments", {})
                    call_sig = f"{tool_name}:{json.dumps(args, sort_keys=True)}"

                    if on_event:
                        on_event(f"Executing tool: {tool_name} with args: {args}")

                    # Anti-loop guard: prevent repeating identical tool call
                    if call_sig in seen_calls:
                        warning_msg = (
                            f"Observation: You already called '{tool_name}' with these exact arguments. "
                            "Do NOT repeat the same call. Please proceed to scrape a target website "
                            "or write the personalized outreach email and return {\"answer\": \"...\"}."
                        )
                        state.message.append(ChatMessage(role="user", content=warning_msg))
                        continue

                    seen_calls.add(call_sig)

                    tool = self.tool_registry.get_tools(tool_name)
                    if tool:
                        result = tool.execute(args)
                        # Observation as user role with guidance for next step
                        obs_content = (
                            f"Observation / Tool Output from '{tool_name}':\n{str(result)}\n\n"
                            "Now proceed: if you have search results, scrape the target URL. "
                            "If you have company info, immediately write the cold outreach email and return {\"answer\": \"...\"}."
                        )
                        state.message.append(ChatMessage(role="user", content=obs_content))
                    else:
                        state.message.append(
                            ChatMessage(
                                role="user",
                                content=f"Error: Tool '{tool_name}' not found. Please choose an available tool or return final answer.",
                            )
                        )

                elif "answer" in parsed:
                    state.status = IterationStatus.COMPLETED
                    if on_event:
                        on_event(f"Final Answer: {parsed['answer']}")
                    break

            except Exception as e:
                state.status = IterationStatus.ERROR
                error_msg = f"Agent error: {str(e)}"
                state.message.append(ChatMessage(role="user", content=error_msg))
                if on_event:
                    on_event(error_msg)
                break

        # Graceful fallback: If max iterations reached, synthesize the collected info into final email
        if state.status == IterationStatus.RUNNING:
            try:
                fallback_prompt = [
                    {"role": "system", "content": system_instruction},
                    *[{"role": m.role, "content": m.content} for m in state.message],
                    {
                        "role": "user",
                        "content": (
                            "Based on all the research and candidate profile above, "
                            "please write the final high-impact personalized cold outreach email draft now. "
                            "Return in JSON: {\"answer\": \"<email subject and body>\"}"
                        ),
                    },
                ]
                final_res = self.llm.invoke(fallback_prompt)
                clean_final = final_res.strip()
                if clean_final.startswith("```"):
                    clean_final = clean_final.split("```")[1]
                    if clean_final.startswith("json"):
                        clean_final = clean_final[4:]
                clean_final = clean_final.strip()

                try:
                    parsed_final = json.loads(clean_final)
                    answer_text = parsed_final.get("answer", clean_final)
                except Exception:
                    answer_text = clean_final

                state.message.append(
                    ChatMessage(role="assistant", content=json.dumps({"answer": answer_text}))
                )
                state.status = IterationStatus.COMPLETED
                if on_event:
                    on_event(f"Graceful completion: {answer_text[:120]}...")
            except Exception:
                state.status = IterationStatus.ERROR
                if on_event:
                    on_event("Agent hit max iterations without finishing.")

        return state