import os
import requests
from bs4 import BeautifulSoup
from groq import Groq
from app.tools.base import BaseTool
from typing import Any, Dict


class webscrapper:
    """Fetches a URL, cleans the HTML, and uses Groq to extract relevant info."""

    def clean_html(self, html_content: str) -> str:
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "form", "button"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    def scrape_with_groq(self, url: str, prompt: str) -> str:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        cleaned_text = self.clean_html(response.text)

        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        model = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise web data extraction assistant. "
                        "Extract the requested information from the provided webpage text accurately."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Webpage Content:\n{cleaned_text[:15000]}\n\nTask: {prompt}",
                },
            ],
            temperature=0.1,
        )
        return completion.choices[0].message.content


class ScrapJobTool(BaseTool):
    name = "scrap_job"
    description = "Scrape a company website for relevant info. Arguments: {'url': '...', 'prompt': '...'}"

    _instance = webscrapper()

    def execute(self, arguments: Dict[str, Any]):
        url = arguments.get("url") or arguments.get("link") or arguments.get("website") or ""
        prompt = arguments.get("prompt", "Extract all company information relevant for a cold email.")
        if not url:
            return {"error": "scrap_job requires a 'url' argument"}
        return self._instance.scrape_with_groq(url=url, prompt=prompt)
