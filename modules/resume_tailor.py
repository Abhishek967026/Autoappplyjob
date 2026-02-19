"""AI-powered resume tailoring using Claude API.

Takes a base resume and job description, produces a tailored PDF resume.
"""

import os
import anthropic
import markdown
from datetime import datetime
from utils.logger import logger


class ResumeTailor:
    def __init__(self, config: dict):
        self.client = anthropic.Anthropic()
        self.base_resume = self._load_base_resume(config["resume"]["base_resume_path"])
        self.output_dir = config["resume"]["output_dir"]
        os.makedirs(self.output_dir, exist_ok=True)

    def _load_base_resume(self, path: str) -> str:
        try:
            with open(path, "r") as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Base resume not found at {path}")
            raise

    def tailor_resume(self, job: dict) -> str:
        """Tailor resume for a specific job. Returns path to output PDF."""
        company = job.get("Company", job.get("company", ""))
        role = job.get("Role", job.get("title", ""))
        description = job.get("Description", job.get("description", ""))

        logger.info(f"Tailoring resume for {role} at {company}")

        prompt = self._build_prompt(description, company, role)
        tailored_md = self._call_claude(prompt)
        pdf_path = self._generate_pdf(tailored_md, company, role)

        logger.info(f"Resume saved: {pdf_path}")
        return pdf_path

    def _build_prompt(self, jd: str, company: str, role: str) -> str:
        return f"""You are an expert resume writer specializing in PM and tech internships.

I am applying for the role of **{role}** at **{company}**.

## Job Description:
{jd}

## My Base Resume:
{self.base_resume}

## Instructions:
1. Fix ALL grammatical errors, typos, and awkward phrasing in my resume.
2. Reorder and emphasize experiences most relevant to this specific JD.
3. Incorporate keywords from the JD naturally into bullet points.
4. Quantify achievements where possible (use numbers from the original).
5. Keep the resume to exactly 1 page — be concise.
6. DO NOT fabricate any experiences, skills, or achievements.
7. DO NOT add skills or tools I haven't mentioned in my base resume.
8. Maintain a professional, clean format.

## Output Format:
Output the tailored resume in clean markdown with these sections:
# [My Name]
[Contact info from base resume]

## Education
## Experience
## Projects
## Skills

Use bullet points with strong action verbs. Keep it scannable."""

    def _call_claude(self, prompt: str) -> str:
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    def _generate_pdf(self, md_text: str, company: str, role: str) -> str:
        """Convert tailored markdown resume to PDF."""
        safe_name = lambda s: s.replace(" ", "_").replace("/", "_")[:30]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"resume_{safe_name(company)}_{safe_name(role)}_{timestamp}.pdf"
        filepath = os.path.join(self.output_dir, filename)

        html = self._markdown_to_styled_html(md_text)

        try:
            from weasyprint import HTML
            HTML(string=html).write_pdf(filepath)
        except ImportError:
            # Fallback: save as HTML if weasyprint not installed
            html_path = filepath.replace(".pdf", ".html")
            with open(html_path, "w") as f:
                f.write(html)
            logger.warning(f"weasyprint not installed, saved as HTML: {html_path}")
            return html_path

        return filepath

    def _markdown_to_styled_html(self, md_text: str) -> str:
        body = markdown.markdown(md_text)
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @page {{ margin: 0.5in; size: letter; }}
    body {{
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-size: 10.5pt;
        line-height: 1.4;
        color: #1a1a1a;
        margin: 0;
        padding: 0;
    }}
    h1 {{
        font-size: 18pt;
        margin: 0 0 4px 0;
        color: #111;
    }}
    h2 {{
        font-size: 11pt;
        text-transform: uppercase;
        letter-spacing: 1px;
        border-bottom: 1.5px solid #333;
        padding-bottom: 2px;
        margin: 12px 0 6px 0;
        color: #222;
    }}
    h3 {{
        font-size: 10.5pt;
        margin: 6px 0 2px 0;
        font-weight: 600;
    }}
    ul {{
        margin: 2px 0 6px 0;
        padding-left: 16px;
    }}
    li {{
        margin: 1px 0;
        font-size: 10pt;
    }}
    p {{
        margin: 2px 0;
    }}
    strong {{ font-weight: 600; }}
    a {{ color: #0066cc; text-decoration: none; }}
</style>
</head>
<body>
{body}
</body>
</html>"""
