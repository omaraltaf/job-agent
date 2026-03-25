"""
Cover Letter Generator — writes a tailored cover letter for each job using Claude
"""

import anthropic
import logging
from pathlib import Path
from datetime import datetime

log = logging.getLogger(__name__)


class CoverLetterGenerator:
    def __init__(self, config):
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def generate(self, job: dict, cv_path: Path, lang: str = "no") -> Path:
        from job_agent.modules.docx_utils import markdown_to_docx
        output_dir = cv_path.parent
        output_path = output_dir / f"CoverLetter_{self._safe_name(job)}.docx"

        try:
            letter = self._generate_letter(job, lang)
            markdown_to_docx(letter, str(output_path))
            log.info(f"  Cover letter generated ({lang}): {output_path.name}")
        except Exception as e:
            log.warning(f"  Cover letter generation failed: {e}")
            markdown_to_docx(self._fallback_letter(job), str(output_path))

        return output_path

    def _generate_letter(self, job: dict, lang: str = "no") -> str:
        today = datetime.now().strftime("%B %d, %Y")

        if lang == "no":
            lang_instruction = "Write the ENTIRE cover letter in Norwegian (bokmål). Use natural, professional Norwegian."
            greeting = 'Start with "Hei," or the hiring manager\'s name if mentioned in the JD.'
        else:
            lang_instruction = "Write the ENTIRE cover letter in English."
            greeting = 'Start with "Dear Hiring Team," or the hiring manager\'s name if mentioned in the JD.'

        prompt = f"""
Write a professional, concise cover letter for this job application.

APPLICANT BACKGROUND:
{self.config.BACKGROUND_SUMMARY}
Portfolio: {self.config.YOUR_PORTFOLIO}

JOB DETAILS:
Title: {job['title']}
Company: {job['company']}
Location: {job['location']}
Source: {job['source']}

JOB DESCRIPTION:
{job.get('description', 'Not available')[:2000]}

INSTRUCTIONS:
- {lang_instruction}
- 3 paragraphs maximum
- Opening: why this specific company/role is exciting
- Middle: 2-3 most relevant skills/experiences for this role
- Closing: call to action
- Professional but warm tone
- Do NOT use generic phrases
- Norwegian workplace culture: direct, humble, team-oriented
- Today's date: {today}

Write only the letter body (no subject line needed). {greeting}
"""

        response = self.client.messages.create(
            model=self.config.AI_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )

        letter = response.content[0].text.strip()

        header = f"{self.config.YOUR_NAME}\n{self.config.YOUR_EMAIL} | {self.config.YOUR_PHONE}\n{today}\n\n"
        return header + letter

    def _fallback_letter(self, job: dict) -> str:
        today = datetime.now().strftime("%B %d, %Y")
        return f"""{self.config.YOUR_NAME}
{self.config.YOUR_EMAIL} | {self.config.YOUR_PHONE}
{today}

Dear Hiring Team,

I am excited to apply for the {job['title']} position at {job['company']}.
With my background and experience, I believe I can contribute meaningfully to your team.

[Please personalise this cover letter before submitting]

Best regards,
{self.config.YOUR_NAME}
{self.config.YOUR_PORTFOLIO}
"""

    def _safe_name(self, job: dict) -> str:
        company = "".join(c for c in job["company"] if c.isalnum())[:20]
        return company
