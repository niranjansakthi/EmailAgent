import json
from typing import List, Any, Callable, Optional, Protocol
from pydantic import BaseModel

# Adjust these imports based on where your files actually are
from app.tools.registry import Toolregister
from .models import Agentstate, IterationStatus, ChatMessage

class LLMClient(Protocol):
    def invoke(self, messages: List[dict]) -> str:
        pass

class AgentRunner:
    def __init__(self, llm: LLMClient, tool_registry: Toolregister, max_iterations: int = 5) -> None:
        self.llm = llm
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations

    def run(self, goal: str, on_event: Optional[Callable[[str], Any]] = None):
        # 1. Initialize State
        state = Agentstate(
            goal=goal,
            status=IterationStatus.RUNNING,
        )
        
        state.message.append(ChatMessage(role="user", content=goal))

        # 2. Start the ReAct Loop
        while state.Iteration < self.max_iterations:
            state.Iteration += 1

            # Build the system prompt. Injecting the available tools dynamically!
            tool_names = list(self.tool_registry.tools.keys())
            system_instruction = (
                f"Your Goal: {state.goal}\n"
                f"Available Tools: {tool_names}\n\n"
                "You must respond in pure JSON format.\n"
                "If you need to use a tool, respond exactly like this: {'tool': 'tool_name', 'arguments': {'url': '...', 'prompt': '...'}}\n"
                "If you have achieved the goal, respond exactly like this: {'answer': 'your final answer here'}"
            )
            
            # Format messages exactly how the LLM API expects them
            messages_for_llm = [{"role": "system", "content": system_instruction}]
            messages_for_llm.extend([{"role": m.role, "content": m.content} for m in state.message])

            try:
                # 3. Call the LLM
                response_str = self.llm.invoke(messages_for_llm)
                
                # We save what the assistant said so it remembers its thought process
                state.message.append(ChatMessage(role="assistant", content=response_str))
                
                if on_event:
                    on_event(f"LLM Response: {response_str}")

                # 4. Parse the JSON response
                try:
                    parsed = json.loads(response_str)
                    
                    if "tool" in parsed:
                        tool_name = parsed["tool"]
                        args = parsed.get("arguments", {})
                        
                        if on_event:
                            on_event(f"Executing tool: {tool_name} with args: {args}")
                            
                        # 5. Execute the Tool!
                        tool = self.tool_registry.get_tools(tool_name)
                        if tool:
                            result = tool.execute(args)
                            # Append the tool's result to the messages so the LLM sees it on the next loop
                            state.message.append(ChatMessage(role="system", content=f"Tool Output: {str(result)}"))
                        else:
                            state.message.append(ChatMessage(role="system", content=f"Error: Tool '{tool_name}' not found in registry."))
                            
                    elif "answer" in parsed:
                        # 6. We got the final answer!
                        state.status = IterationStatus.COMPLETED
                        if on_event:
                            on_event(f"Final Answer: {parsed['answer']}")
                        break
                        
                except json.JSONDecodeError:
                    # If the LLM didn't return JSON, it messed up. We just store the raw text and stop.
                    state.status = IterationStatus.COMPLETED
                    if on_event:
                        on_event(f"LLM did not return JSON. Raw text: {response_str}")
                    break
                    
            except Exception as e:
                state.status = IterationStatus.ERROR
                error_msg = f"Error occurred: {str(e)}"
                state.message.append(ChatMessage(role="system", content=error_msg))
                if on_event:
                    on_event(error_msg)
                break

        # If it hits max_iterations without finishing
        if state.status == IterationStatus.RUNNING:
            state.status = IterationStatus.ERROR
            if on_event:
                on_event("Agent hit max iterations without finishing.")

        return state
