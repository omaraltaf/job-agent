"""
CV Adapter — generates a tailored CV for each job using Claude.
Reads your master CV, sends it to Claude with the job description,
and generates a customised version.
"""

import anthropic
import shutil
import logging
from pathlib import Path
from datetime import datetime

log = logging.getLogger(__name__)


def _extract_text_from_pdf(path: Path) -> str:
    """Extract text content from a PDF file."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        log.warning(f"Could not extract PDF text: {e}")
        return ""


def _extract_text_from_docx(path: Path) -> str:
    """Extract text content from a DOCX file."""
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(str(path)) as z:
            with z.open("word/document.xml") as f:
                tree = ET.parse(f)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = tree.findall(".//w:p", ns)
        text = "\n".join(
            "".join(node.text or "" for node in p.findall(".//w:t", ns))
            for p in paragraphs
        )
        return text.strip()
    except Exception as e:
        log.warning(f"Could not extract DOCX text: {e}")
        return ""


class CVAdapter:
    def __init__(self, config):
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def adapt(self, job: dict) -> tuple[Path, str]:
        """
        Creates a tailored CV for the job.
        Returns (cv_path, language) where language is "no" or "en".

        Strategy:
        - Detects job language and picks the matching master CV
        - Extracts text from the master CV
        - Sends to Claude with the JD to generate a tailored version
        - Saves as a .txt file in the job's output folder
        - Also copies the original CV alongside for reference
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

        # Extract text from the master CV
        if cv_source.suffix.lower() == ".pdf":
            cv_text = _extract_text_from_pdf(cv_source)
        elif cv_source.suffix.lower() == ".docx":
            cv_text = _extract_text_from_docx(cv_source)
        else:
            cv_text = cv_source.read_text(encoding="utf-8")

        if not cv_text:
            # Fallback: just copy the CV as-is
            log.warning("  Could not extract CV text, copying original")
            ext = cv_source.suffix
            output_cv = output_dir / f"CV_{self._safe_name(job)}{ext}"
            shutil.copy2(cv_source, output_cv)
            return output_cv, lang

        # Copy original for reference
        original_copy = output_dir / f"CV_original{cv_source.suffix}"
        shutil.copy2(cv_source, original_copy)

        # Generate tailored CV
        from job_agent.modules.docx_utils import markdown_to_docx
        output_cv = output_dir / f"CV_{self._safe_name(job)}.docx"
        try:
            tailored = self._tailor_cv(cv_text, job, lang)
            markdown_to_docx(tailored, str(output_cv))
            log.info(f"  CV tailored for {job['company']}: {output_cv.name}")
        except Exception as e:
            log.warning(f"  CV tailoring failed, copying original: {e}")
            ext = cv_source.suffix
            output_cv = output_dir / f"CV_{self._safe_name(job)}{ext}"
            shutil.copy2(cv_source, output_cv)

        return output_cv, lang

    def _tailor_cv(self, cv_text: str, job: dict, lang: str) -> str:
        """Use Claude to generate a tailored CV based on master CV + job description."""
        embellish = getattr(self.config, "CV_EMBELLISH", False)

        if embellish:
            honesty_instruction = """
EMBELLISHMENT ALLOWED: You may add plausible skills, tools, or experience 
that the candidate could reasonably have, even if not explicitly stated in 
the original CV. Make the candidate look as strong as possible for this role.
"""
        else:
            honesty_instruction = """
STRICT HONESTY: You must ONLY use information that exists in the original CV.
You may reorder sections, emphasise certain skills, adjust wording, and 
highlight the most relevant experience — but do NOT invent, fabricate, or 
add any skills, tools, certifications, or experience that are not present 
in the original CV. Every claim must be traceable to the source CV.
"""

        if lang == "no":
            lang_instruction = "Write the CV in Norwegian (bokmål)."
        else:
            lang_instruction = "Write the CV in English."

        prompt = f"""
You are an expert CV writer. Tailor this CV for the specific job below.

ORIGINAL CV:
{cv_text[:4000]}

JOB DETAILS:
Title: {job['title']}
Company: {job['company']}
Location: {job['location']}

JOB DESCRIPTION:
{job.get('description', 'Not available')[:2000]}

RULES:
{honesty_instruction}

FORMATTING:
- {lang_instruction}
- Use a clean, professional text format
- Include: Name, Contact Info, Professional Summary, Key Skills, Experience, Education
- Lead with the most relevant skills and experience for THIS specific role
- Use keywords from the job description where they genuinely match the candidate's skills
- Keep it to 1-2 pages worth of text
- Professional Summary should be 2-3 sentences tailored to this specific role

OUTPUT:
Write the complete tailored CV below. No explanations or notes, just the CV content.
"""

        response = self.client.messages.create(
            model=self.config.AI_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text.strip()

    def _detect_language(self, job: dict) -> str:
        """
        Detect job language. Default is Norwegian.
        Only returns 'en' if the JD is clearly in English with NO Norwegian present.
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

        if no_hits >= 1:
            return "no"
        if en_hits >= 2:
            return "en"
        return "no"

    def _get_job_folder(self, job: dict) -> Path:
        date_str = datetime.now().strftime("%Y-%m-%d")
        safe_company = "".join(c for c in job["company"] if c.isalnum() or c in " _-")[:30]
        safe_title = "".join(c for c in job["title"] if c.isalnum() or c in " _-")[:30]
        folder_name = f"{date_str}_{safe_company}_{safe_title}".replace(" ", "_")
        return self.config.OUTPUT_DIR / folder_name

    def _safe_name(self, job: dict) -> str:
        company = "".join(c for c in job["company"] if c.isalnum())[:20]
        return company
