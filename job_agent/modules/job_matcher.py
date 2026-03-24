"""
Job Matcher — scores jobs against your professional profile using Claude
"""

import anthropic
import json
import logging

log = logging.getLogger(__name__)


class JobMatcher:
    def __init__(self, config):
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def score(self, job: dict) -> int:
        """Score a job 1-10 against the professional profile"""

        # Quick pre-filter: exclude obvious non-matches
        title_lower = job["title"].lower()
        for kw in self.config.EXCLUDE_KEYWORDS:
            if kw.lower() in title_lower:
                return 0

        # Use Claude to score
        try:
            prompt = f"""
You are evaluating a job posting for a candidate.

CANDIDATE PROFILE:
{self.config.PROFESSIONAL_PROFILE}

JOB POSTING:
Title: {job['title']}
Company: {job['company']}
Location: {job['location']}
Description:
{job.get('description', 'No description available')[:1500]}

Score how well this job matches the candidate profile on a scale of 1-10.
- 9-10: Perfect match, must apply
- 7-8: Strong match, should apply  
- 5-6: Moderate match, worth considering
- 3-4: Weak match
- 1-2: Not a match

Respond ONLY with a JSON object like:
{{"score": 8, "reason": "Strong UX role at a product company, Figma required"}}
"""

            response = self.client.messages.create(
                model=self.config.AI_MODEL,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )

            text = response.content[0].text.strip()
            result = json.loads(text)
            score = int(result.get("score", 0))
            log.debug(f"  Score {score}/10 for '{job['title']}': {result.get('reason', '')}")
            return score

        except Exception as e:
            log.warning(f"Scoring failed for '{job['title']}': {e}")
            # Fallback: keyword-based scoring
            return self._keyword_score(job)

    def _keyword_score(self, job: dict) -> int:
        """Simple keyword fallback scorer"""
        text = (job["title"] + " " + job.get("description", "")).lower()
        score = 0

        high_match = ["ux designer", "ui designer", "ux/ui", "product designer", "interaction designer"]
        medium_match = ["designer", "figma", "user experience", "user interface", "wireframe"]

        for kw in high_match:
            if kw in text:
                score += 3

        for kw in medium_match:
            if kw in text:
                score += 1

        return min(score, 10)
