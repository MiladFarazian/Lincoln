"""Resume crafting service using Anthropic Claude API."""

import os
import logging

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert resume writer. Your task is to tailor a candidate's resume to match a specific job posting.

Rules:
- Reorder, rephrase, and emphasize existing experience to align with the job requirements
- Incorporate relevant keywords and phrases from the job description naturally
- Adjust the professional summary/objective to target this specific role
- Highlight matching skills and relevant achievements
- NEVER fabricate skills, experience, companies, or credentials the candidate does not have
- Keep the same general format and structure as the original resume
- Output the tailored resume as clean, well-formatted plain text ready to copy/paste
- Do not include any commentary, explanations, or notes — only output the resume itself"""


def craft_resume(base_resume: str, job_description: str, job_title: str, company: str) -> str:
    """Call Claude to tailor a resume for a specific job posting."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

    client = anthropic.Anthropic(api_key=api_key)

    # Truncate very long descriptions to stay within reasonable token limits
    if len(job_description) > 8000:
        job_description = job_description[:8000] + "\n[truncated]"

    user_message = f"""## Job Posting
**Title:** {job_title}
**Company:** {company}

**Description:**
{job_description}

---

## My Current Resume
{base_resume}

---

Please tailor my resume for this specific job posting."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return message.content[0].text
