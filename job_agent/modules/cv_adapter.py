"""
CV Adapter — tailors your master CV for each specific job using Claude
"""

import anthropic
import shutil
import logging
from pathlib import Path
from datetime import datetime

log = logging.getLogger(__name__)


class CVAdapter:
    def __init__(self, config):
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def adapt(self, job: dict) -> tuple[Path, str]:
        """
        Creates a tailored CV for the job.
        Returns (cv_path, language) where language is "no" or "en".
        
        Strategy:
        - Detects job language and picks the matching CV (Norwegian or English)
        - If CV is PDF: copy as-is
        - If CV is DOCX: generate a tailored version
        - Always saves to the job's output folder
        """
        output_dir = self._get_job_folder(job)
        output_dir.mkdir(parents=True, exist_ok=True)

        lang = self._detect_language(job)
        cv_source = self.config.CV_PATH_NO if lang == "no" else self.config.CV_PATH_EN
        log.info(f"  Language detected: {lang} → using {cv_source.name}")

        if not cv_source.exists():
            raise FileNotFoundError(
                f"CV not found at {cv_source}. Set CV_PATH_NO / CV_PATH_EN in config.py"
            )

        # For PDF CVs: copy as-is
        if cv_source.suffix.lower() == ".pdf":
            output_cv = output_dir / f"CV_{self._safe_name(job)}.pdf"
            shutil.copy2(cv_source, output_cv)
            log.info(f"  CV copied (PDF): {output_cv.name}")
            return output_cv, lang

        # For DOCX CVs: generate a tailored version
        elif cv_source.suffix.lower() == ".docx":
            output_cv = output_dir / f"CV_{self._safe_name(job)}.docx"
            self._adapt_docx(cv_source, output_cv, job)
            return output_cv, lang

        else:
            ext = cv_source.suffix
            output_cv = output_dir / f"CV_{self._safe_name(job)}{ext}"
            shutil.copy2(cv_source, output_cv)
            return output_cv, lang

    def _detect_language(self, job: dict) -> str:
        """
        Detect job language. Default is Norwegian.
        Only returns 'en' if the JD is clearly in English with NO Norwegian present.
        If both languages appear, returns Norwegian.
        """
        text = f"{job.get('title', '')} {job.get('description', '')}".lower()

        no_keywords = [
            "stilling", "søknad", "erfaring", "ansvar", "arbeidsoppgaver",
            "kvalifikasjoner", "utdanning", "kompetanse", "stillingen",
            "vi søker", "om oss", "arbeidsgiver", "ledig stilling",
            "fast stilling", "tiltreding", "søknadsfrist", "norsk",
        ]
        en_keywords = [
            "requirements", "qualifications", "responsibilities",
            "we are looking for", "about us", "you will", "your role",
            "experience with", "apply now", "deadline", "english",
        ]

        no_hits = sum(1 for kw in no_keywords if kw in text)
        en_hits = sum(1 for kw in en_keywords if kw in text)

        # Any Norwegian detected → Norwegian (including when both are present)
        if no_hits >= 1:
            return "no"
        # Only English detected, no Norwegian → English
        if en_hits >= 2:
            return "en"
        # Default to Norwegian
        return "no"

    def _adapt_docx(self, source: Path, output: Path, job: dict):
        """
        Uses Claude to suggest CV tweaks, then applies them.
        For now: copies CV and generates a tailoring notes file.
        Extend this with python-docx for deeper editing.
        """
        shutil.copy2(source, output)

        # Generate tailoring suggestions
        try:
            suggestions = self._get_tailoring_suggestions(job)
            notes_path = output.parent / "cv_tailoring_notes.txt"
            notes_path.write_text(suggestions)
            log.info(f"  CV adapted (DOCX) with tailoring notes")
        except Exception as e:
            log.warning(f"  CV adaptation failed, using master CV: {e}")

        return output

    def _get_tailoring_suggestions(self, job: dict) -> str:
        prompt = f"""
You are a UX/UI Designer career coach. Given this job posting, suggest 3-5 specific 
ways to tailor the CV/resume. Be specific about what to emphasize or reorder.

JOB: {job['title']} at {job['company']}
DESCRIPTION: {job.get('description', '')[:1000]}

Provide brief, actionable suggestions. Focus on:
- Which skills to highlight more prominently
- Relevant projects to lead with
- Keywords from the JD to include
"""
        response = self.client.messages.create(
            model=self.config.AI_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def _get_job_folder(self, job: dict) -> Path:
        date_str = datetime.now().strftime("%Y-%m-%d")
        safe_company = "".join(c for c in job["company"] if c.isalnum() or c in " _-")[:30]
        safe_title = "".join(c for c in job["title"] if c.isalnum() or c in " _-")[:30]
        folder_name = f"{date_str}_{safe_company}_{safe_title}".replace(" ", "_")
        return self.config.OUTPUT_DIR / folder_name

    def _safe_name(self, job: dict) -> str:
        company = "".join(c for c in job["company"] if c.isalnum())[:20]
        return company
