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

        while state.Iteration < self.max_iterations:
            state.Iteration += 1

            tool_descriptions = "\n".join(
                f"- {name}: {tool.description}"
                for name, tool in self.tool_registry.tools.items()
            )
            system_instruction = (
                f"Your Goal: {state.goal}\n\n"
                f"Available Tools and Schemas:\n{tool_descriptions}\n\n"
                "You MUST respond in pure JSON (no markdown fences, no extra text).\n"
                "To call a tool:  {\"tool\": \"tool_name\", \"arguments\": {\"param_name\": \"value\"}}\n"
                "When done:       {\"answer\": \"your final response with the personalized email draft\"}\n"
            )

            messages_for_llm = [{"role": "system", "content": system_instruction}]
            messages_for_llm.extend(
                [{"role": m.role, "content": m.content} for m in state.message]
            )

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

                    if on_event:
                        on_event(f"Executing tool: {tool_name} with args: {args}")

                    tool = self.tool_registry.get_tools(tool_name)
                    if tool:
                        result = tool.execute(args)
                        state.message.append(
                            ChatMessage(role="system", content=f"Tool Output: {str(result)}")
                        )
                    else:
                        state.message.append(
                            ChatMessage(
                                role="system",
                                content=f"Error: Tool '{tool_name}' not found in registry.",
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
                state.message.append(ChatMessage(role="system", content=error_msg))
                if on_event:
                    on_event(error_msg)
                break

        if state.status == IterationStatus.RUNNING:
            state.status = IterationStatus.ERROR
            if on_event:
                on_event("Agent hit max iterations without finishing.")

        return state