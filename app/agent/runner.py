import os
from typing import List

from groq import Groq
from app.agent.agent import AgentRunner
from app.tools.registry import Toolregister


class GroqLLMClient:
    """Thin wrapper around the Groq SDK that satisfies the LLMClient Protocol."""

    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY is not set in environment variables.")
        self.client = Groq(api_key=api_key)

    def invoke(self, messages: List[dict]) -> str:
        model = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
        )
        return completion.choices[0].message.content


def build_agent(max_iterations: int = 8) -> AgentRunner:
    """Factory function – creates a fully wired AgentRunner ready to use."""
    llm = GroqLLMClient()
    registry = Toolregister()
    return AgentRunner(llm=llm, tool_registry=registry, max_iterations=max_iterations)


def print_agent_event(event_message: str):
    print(f"\n🤖 [AGENT]: {event_message}")


# ---------------------------------------------------------------------------
# CLI entry-point (kept for backward compat)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 Starting the Cold Mail Agent...")
    agent = build_agent()
    user_resume = input("Please type a brief summary of your background/resume:\n> ")
    user_goal = (
        f"Find an internship opportunity at a tech startup, "
        f"scrape their website, and write a cold email draft for me. "
        f"My background: {user_resume}"
    )
    print(f"🎯 Goal: {user_goal}\n" + "-" * 50)
    final_state = agent.run(goal=user_goal, on_event=print_agent_event)
    print("-" * 50)
    if final_state.status == "completed":
        print("✅ Mission Accomplished!")
    else:
        print(f"❌ Mission failed with status: {final_state.status}")
