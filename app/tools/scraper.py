import os
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from groq import Groq
from app.tools.base import BaseTool
from typing import Any, Dict


class webscrapper:
    """Fetches a URL, cleans the HTML, extracts contact emails, and uses Groq to extract relevant info."""

    def extract_emails(self, html_content: str, domain: str = "") -> list:
        emails = []
        soup = BeautifulSoup(html_content, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.lower().startswith("mailto:"):
                clean = href[7:].split("?")[0].strip().lower()
                if clean and "@" in clean:
                    emails.append(clean)

        found_in_text = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html_content)
        for em in found_in_text:
            em_clean = em.strip().lower().rstrip(".")
            if not em_clean.endswith((".png", ".jpg", ".svg", ".webp", ".js", ".css")):
                emails.append(em_clean)

        unique_emails = list(dict.fromkeys(emails))
        hiring_emails = [e for e in unique_emails if any(k in e for k in ["career", "job", "hiring", "recruit", "talent", "hr", "contact", "info", "hello"])]
        if hiring_emails:
            return hiring_emails[:5]
        if unique_emails:
            return unique_emails[:5]

        if domain:
            base_domain = domain.lower().replace("www.", "").split(":")[0]
            if "." in base_domain:
                return [f"careers@{base_domain}", f"recruiting@{base_domain}"]
        return []

    def clean_html(self, html_content: str) -> str:
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "form", "button"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    def scrape_with_groq(self, url: str, prompt: str) -> str:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        domain = urllib.parse.urlparse(url).netloc
        extracted_emails = self.extract_emails(response.text, domain=domain)
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
                        "Extract the requested company information, mission, and culture. "
                        "Identify the best recruiter, careers, or hiring email address to reach out to."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Webpage Content:\n{cleaned_text[:12000]}\n\n"
                        f"Detected Contact/Recruiter Emails: {extracted_emails}\n\n"
                        f"Task: {prompt}\n"
                        "Be sure to specify the best recruiter email (or standard careers@/jobs@ email) to contact."
                    ),
                },
            ],
            temperature=0.1,
        )
        content = completion.choices[0].message.content
        if extracted_emails and not any(em in content for em in extracted_emails):
            content += f"\n\nRecruiter/Contact Emails found: {', '.join(extracted_emails)}"
        return content


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
