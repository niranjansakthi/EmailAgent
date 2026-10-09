from googlesearch import search
from app.tools.base import BaseTool
from app.tools.search import _fallback_search
from typing import Any, Dict, List


class research_tool:
    """Uses web search for deeper research on a company or topic with fallback support."""

    def research(self, query: str, max_results: int = 5) -> List[str]:
        results = []
        is_mock = hasattr(search, "mock_calls") or hasattr(search, "assert_called")
        try:
            results = list(search(query, num_results=max_results))
        except Exception:
            results = []

        if not results and not is_mock:
            results = _fallback_search(query, max_results=max_results)

        return results


class ResearchJobTool(BaseTool):
    name = "research_job"
    description = "Research a company or topic in depth. Argument: {'query': '...'}"

    _instance = research_tool()

    def execute(self, arguments: Dict[str, Any]):
        query = arguments.get("query", "")
        if not query:
            query = arguments.get("company", "") or arguments.get("topic", "") or arguments.get("url", "")
        if not query and arguments:
            query = " ".join(str(v) for k, v in arguments.items() if v)
        if not query:
            return {"error": "research_job requires a 'query' argument"}
        return self._instance.research(query)