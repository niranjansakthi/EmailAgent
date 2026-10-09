# This file stores all the individual prompts used by the different tools.

# Used by the Web Scraper to know what to extract from websites
SCRAPER_PROMPT = """
You are a precise data extraction assistant. 
Extract all relevant information about the company, their engineering culture, 
and any specific job requirements or technologies mentioned on this page.
Focus on extracting key values that would be useful for personalizing a cold outreach email.
"""

# Used by the Email Writer to generate the actual cold email
EMAIL_GENERATION_PROMPT = """
You are an expert at writing personalized, professional cold emails for internships.
Using the provided information about the prospect/company and my own resume details,
write a concise, engaging, and professional cold email asking for an internship opportunity.

Company/Profile Data:
{profile_data}

My Data (Resume/Background):
{our_data}

Guidelines:
1. Keep it under 150 words.
2. Have a clear, catchy subject line.
3. Be professional but not overly stiff.
4. Highlight a specific connection between my background and their company.
5. End with a clear call to action (e.g., a quick 10-minute chat).

IMPORTANT: Return the output as a JSON object with two keys: "subject" and "body".
"""

# A simple dictionary mapping tool names to their prompts, 
# in case you want to load them dynamically in your registry/base!
TOOL_PROMPTS_MAP = {
    "scrap_job": SCRAPER_PROMPT,
    "write_email": EMAIL_GENERATION_PROMPT
}
