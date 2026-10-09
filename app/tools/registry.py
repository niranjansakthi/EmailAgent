from app.tools.search import SearchJobsTool
from app.tools.research import ResearchJobTool
from app.tools.scraper import ScrapJobTool
from app.tools.email import WriteEmailTool, SendEmailTool
from app.tools.base import BaseTool
from typing import Optional


class Toolregister:
    """Central registry that maps tool names to their instances."""

    def __init__(self):
        self.tools: dict[str, BaseTool] = {}
        self.register(SearchJobsTool())
        self.register(ResearchJobTool())
        self.register(ScrapJobTool())
        self.register(WriteEmailTool())
        self.register(SendEmailTool())

    def register(self, tool: BaseTool):
        self.tools[tool.name] = tool

    def get_tools(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)

    def list_tool_names(self) -> list[str]:
        return list(self.tools.keys())
