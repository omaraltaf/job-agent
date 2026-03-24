"""
Job Applicator — detects ATS system and applies accordingly
Supported: Lever, FINN Easy Apply, Reachmee, Webcruiter, Teamtailor, ContactRH, Greenhouse
Fallback: opens browser for manual review
"""

import logging
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

log = logging.getLogger(__name__)


class JobApplicator:
    def __init__(self, config):
        self.config = config

    def apply(self, job: dict, cv_path: Path, cover_letter_path: Path) -> dict:
        system = self._detect_system(job)
        job["ats_system"] = system
        log.info(f"  ATS system: {system}")

        if system == "lever":
            return self._apply_lever(job, cv_path, cover_letter_path)
        elif system == "finn_easy_apply":
            return self._apply_finn_easy(job, cv_path, cover_letter_path)
        elif system == "reachmee":
            return self._apply_reachmee(job, cv_path, cover_letter_path)
        elif system == "webcruiter":
            return self._apply_webcruiter(job, cv_path, cover_letter_path)
        elif system == "teamtailor":
            return self._apply_teamtailor(job, cv_path, cover_letter_path)
        elif system == "contactrh":
            return self._apply_contactrh(job, cv_path, cover_letter_path)
        elif system == "greenhouse":
            return self._apply_greenhouse(job, cv_path, cover_letter_path)
        else:
            return self._apply_manual_assist(job, cv_path, cover_letter_path)

    def _detect_system(self, job: dict) -> str:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                page.goto(job["url"], timeout=20000)
                page.wait_for_load_state("networkidle", timeout=15000)

                links = page.eval_on_selector_all(
                    "a[href]",
                    "els => els.map(el => el.href)"
                )

                for href in links:
                    href_lower = href.lower()
                    if "lever.co" in href_lower:
                        job["apply_url"] = href
                        browser.close()
                        return "lever"
                    elif "webcruiter" in href_lower:
                        job["apply_url"] = href
                        browser.close()
                        return "webcruiter"
                    elif "reachmee" in href_lower:
                        job["apply_url"] = href
                        browser.close()
                        return "reachmee"
                    elif "jobbnorge" in href_lower:
                        job["apply_url"] = href
                        browser.close()
                        return "jobbnorge"
                    elif "contactrh" in href_lower:
                        job["apply_url"] = href
                        browser.close()
                        return "contactrh"
                    elif "teamtailor" in href_lower:
                        job["apply_url"] = href
                        browser.close()
                        return "teamtailor"
                    elif "greenhouse.io" in href_lower:
                        job["apply_url"] = href
                        browser.close()
                        return "greenhouse"
                    elif "finn.no/job/apply" in href_lower:
                        job["apply_url"] = href
                        browser.close()
                        return "finn_easy_apply"

                browser.close()
                return "unknown"

            except Exception as e:
                log.warning(f"  Could not detect ATS: {e}")
                try:
                    browser.close()
                except Exception:
                    pass
                return "unknown"

    def _apply_lever(self, job, cv_path, cover_letter_path) -> dict:
        apply_url = job.get("apply_url", job["url"])
        cover_letter_text = self._read_file(cover_letter_path)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config.HEADLESS_BROWSER)
            page = browser.new_page()

            try:
                page.goto(apply_url, timeout=20000)
                page.wait_for_load_state("networkidle", timeout=15000)

                self._try_fill(page,
                    "input[name='name'], input[placeholder*='name' i], input[placeholder*='navn' i]",
                    self.config.YOUR_NAME)
                self._try_fill(page,
                    "input[name='email'], input[type='email']",
                    self.config.YOUR_EMAIL)
                self._try_fill(page,
                    "input[name='phone'], input[type='tel']",
                    self.config.YOUR_PHONE)
                self._try_fill(page,
                    "input[name='org'], input[placeholder*='company' i], input[placeholder*='current' i]",
                    "KvikAI AS")
                self._try_fill(page,
                    "input[name='urls[LinkedIn]'], input[placeholder*='linkedin' i]",
                    self.config.YOUR_LINKEDIN)
                self._try_fill(page,
                    "input[name='urls[Portfolio]'], input[placeholder*='portfolio' i], input[placeholder*='website' i]",
                    self.config.YOUR_PORTFOLIO)
                self._upload_file(page, "input[type='file']", cv_path)
                self._try_fill(page,
                    "textarea[name='comments'], textarea[placeholder*='cover' i], textarea[placeholder*='letter' i], textarea[placeholder*='additional' i]",
                    cover_letter_text)

                if self.config.AUTO_SUBMIT:
                    submitted = self._submit(page)
                    if not submitted:
                        browser.close()
                        return {"success": False, "reason": "Could not find submit button"}

                browser.close()
                return {"success": True, "system": "lever"}

            except PlaywrightTimeout:
                browser.close()
                return {"success": False, "reason": "Lever page timeout"}
            except Exception as e:
                browser.close()
                return {"success": False, "reason": f"Lever error: {e}"}

    def _apply_finn_easy(self, job, cv_path, cover_letter_path) -> dict:
        apply_url = job.get("apply_url", job["url"])
        cover_letter_text = self._read_file(cover_letter_path)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config.HEADLESS_BROWSER)
            context = browser.new_context()
            self._load_cookies(context, "cookies/finn_cookies.json")
            page = context.new_page()

            try:
                page.goto(apply_url, timeout=20000)
                page.wait_for_load_state("networkidle", timeout=15000)

                self._try_fill(page, "input[name='name'], #name", self.config.YOUR_NAME)
                self._try_fill(page, "input[type='email'], #email", self.config.YOUR_EMAIL)
                self._try_fill(page, "input[type='tel'], #phone", self.config.YOUR_PHONE)
                self._upload_file(page, "input[type='file']", cv_path)
                self._try_fill(page, "textarea", cover_letter_text)

                if self.config.AUTO_SUBMIT:
                    self._submit(page)

                browser.close()
                return {"success": True, "system": "finn_easy_apply"}

            except Exception as e:
                browser.close()
                return {"success": False, "reason": f"FINN Easy Apply error: {e}"}

    def _apply_reachmee(self, job, cv_path, cover_letter_path) -> dict:
        apply_url = job.get("apply_url", job["url"])
        cover_letter_text = self._read_file(cover_letter_path)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config.HEADLESS_BROWSER)
            page = browser.new_page()

            try:
                page.goto(apply_url, timeout=20000)
                page.wait_for_load_state("networkidle", timeout=15000)

                self._try_fill(page,
                    "input[name*='first' i], input[id*='first' i]",
                    self.config.YOUR_NAME.split()[0])
                self._try_fill(page,
                    "input[name*='last' i], input[id*='last' i]",
                    self.config.YOUR_NAME.split()[-1])
                self._try_fill(page, "input[type='email']", self.config.YOUR_EMAIL)
                self._try_fill(page, "input[type='tel']", self.config.YOUR_PHONE)
                self._upload_file(page, "input[type='file']", cv_path)
                self._try_fill(page, "textarea", cover_letter_text)

                if self.config.AUTO_SUBMIT:
                    self._submit(page)

                browser.close()
                return {"success": True, "system": "reachmee"}

            except Exception as e:
                browser.close()
                return {"success": False, "reason": f"Reachmee error: {e}"}

    def _apply_webcruiter(self, job, cv_path, cover_letter_path) -> dict:
        apply_url = job.get("apply_url", job["url"])
        cover_letter_text = self._read_file(cover_letter_path)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config.HEADLESS_BROWSER)
            page = browser.new_page()

            try:
                page.goto(apply_url, timeout=20000)
                page.wait_for_load_state("networkidle", timeout=15000)

                self._try_fill(page,
                    "#FirstName, [name='FirstName']",
                    self.config.YOUR_NAME.split()[0])
                self._try_fill(page,
                    "#LastName, [name='LastName']",
                    self.config.YOUR_NAME.split()[-1])
                self._try_fill(page,
                    "#Email, [name='Email'], [type='email']",
                    self.config.YOUR_EMAIL)
                self._try_fill(page,
                    "#Phone, [name='Phone'], [type='tel']",
                    self.config.YOUR_PHONE)
                self._upload_file(page, "input[type='file']", cv_path)
                self._try_fill(page,
                    "textarea[name*='cover'], textarea[name*='motivation']",
                    cover_letter_text)
                self._try_fill(page, "[name*='linkedin' i]", self.config.YOUR_LINKEDIN)
                self._try_fill(page, "[name*='portfolio' i]", self.config.YOUR_PORTFOLIO)

                if self.config.AUTO_SUBMIT:
                    self._submit(page)

                browser.close()
                return {"success": True, "system": "webcruiter"}

            except Exception as e:
                browser.close()
                return {"success": False, "reason": f"Webcruiter error: {e}"}

    def _apply_teamtailor(self, job, cv_path, cover_letter_path) -> dict:
        apply_url = job.get("apply_url", job["url"])
        cover_letter_text = self._read_file(cover_letter_path)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config.HEADLESS_BROWSER)
            page = browser.new_page()

            try:
                page.goto(apply_url, timeout=20000)
                page.wait_for_load_state("networkidle", timeout=15000)

                self._try_fill(page,
                    "input[name*='first' i]",
                    self.config.YOUR_NAME.split()[0])
                self._try_fill(page,
                    "input[name*='last' i]",
                    self.config.YOUR_NAME.split()[-1])
                self._try_fill(page, "input[type='email']", self.config.YOUR_EMAIL)
                self._try_fill(page, "input[type='tel']", self.config.YOUR_PHONE)
                self._try_fill(page,
                    "input[name*='linkedin' i], input[placeholder*='linkedin' i]",
                    self.config.YOUR_LINKEDIN)
                self._upload_file(page, "input[type='file']", cv_path)
                self._try_fill(page, "textarea", cover_letter_text)

                if self.config.AUTO_SUBMIT:
                    self._submit(page)

                browser.close()
                return {"success": True, "system": "teamtailor"}

            except Exception as e:
                browser.close()
                return {"success": False, "reason": f"Teamtailor error: {e}"}

    def _apply_contactrh(self, job, cv_path, cover_letter_path) -> dict:
        apply_url = job.get("apply_url", job["url"])
        cover_letter_text = self._read_file(cover_letter_path)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config.HEADLESS_BROWSER)
            page = browser.new_page()

            try:
                page.goto(apply_url, timeout=20000)
                page.wait_for_load_state("networkidle", timeout=15000)

                self._try_fill(page,
                    "input[name*='first' i], input[id*='first' i]",
                    self.config.YOUR_NAME.split()[0])
                self._try_fill(page,
                    "input[name*='last' i], input[id*='last' i]",
                    self.config.YOUR_NAME.split()[-1])
                self._try_fill(page, "input[type='email']", self.config.YOUR_EMAIL)
                self._try_fill(page, "input[type='tel']", self.config.YOUR_PHONE)
                self._upload_file(page, "input[type='file']", cv_path)
                self._try_fill(page, "textarea", cover_letter_text)

                if self.config.AUTO_SUBMIT:
                    self._submit(page)

                browser.close()
                return {"success": True, "system": "contactrh"}

            except Exception as e:
                browser.close()
                return {"success": False, "reason": f"ContactRH error: {e}"}

    def _apply_greenhouse(self, job, cv_path, cover_letter_path) -> dict:
        apply_url = job.get("apply_url", job["url"])
        cover_letter_text = self._read_file(cover_letter_path)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config.HEADLESS_BROWSER)
            page = browser.new_page()

            try:
                page.goto(apply_url, timeout=20000)
                page.wait_for_load_state("networkidle", timeout=15000)

                self._try_fill(page, "#first_name", self.config.YOUR_NAME.split()[0])
                self._try_fill(page, "#last_name", self.config.YOUR_NAME.split()[-1])
                self._try_fill(page, "#email", self.config.YOUR_EMAIL)
                self._try_fill(page, "#phone", self.config.YOUR_PHONE)
                self._try_fill(page,
                    "#job_application_linkedin_profile_url, input[name*='linkedin' i]",
                    self.config.YOUR_LINKEDIN)
                self._try_fill(page,
                    "#job_application_website, input[name*='website' i]",
                    self.config.YOUR_PORTFOLIO)
                self._upload_file(page, "input[type='file']", cv_path)
                self._try_fill(page, "textarea[name*='cover' i]", cover_letter_text)

                if self.config.AUTO_SUBMIT:
                    self._submit(page)

                browser.close()
                return {"success": True, "system": "greenhouse"}

            except Exception as e:
                browser.close()
                return {"success": False, "reason": f"Greenhouse error: {e}"}

    def _apply_manual_assist(self, job, cv_path, cover_letter_path) -> dict:
        import subprocess
        cover_letter_text = self._read_file(cover_letter_path)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            try:
                page.goto(job["url"], timeout=20000)
                page.wait_for_load_state("networkidle", timeout=15000)

                self._try_fill(page, "input[type='email']", self.config.YOUR_EMAIL)
                self._try_fill(page, "input[type='tel']", self.config.YOUR_PHONE)
                self._upload_file(page, "input[type='file']", cv_path)

                job_title = job["title"]
                job_company = job["company"]
                dialog = (
                    'display dialog "Review and submit: '
                    + job_title
                    + ' at '
                    + job_company
                    + '" buttons {"OK"} default button "OK"'
                )
                subprocess.run(["osascript", "-e", dialog], check=False)

                log.info("  Browser open for manual review")
                time.sleep(300)
                browser.close()
                return {"success": True, "system": "manual_assist"}

            except Exception as e:
                browser.close()
                return {"success": False, "reason": f"Manual assist error: {e}"}

    def _try_fill(self, page, selector: str, value: str):
        if not value:
            return
        try:
            el = page.query_selector(selector)
            if el:
                el.fill(value)
                log.debug(f"  Filled: {selector[:40]}")
        except Exception:
            pass

    def _upload_file(self, page, selector: str, file_path: Path):
        if not file_path or not file_path.exists():
            return
        try:
            el = page.query_selector(selector)
            if el:
                el.set_input_files(str(file_path))
                log.debug(f"  Uploaded: {file_path.name}")
        except Exception:
            pass

    def _submit(self, page) -> bool:
        selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit')",
            "button:has-text('Send application')",
            "button:has-text('Apply')",
            "button:has-text('Send søknad')",
            "button:has-text('Søk nå')",
            "button:has-text('Send inn')",
        ]
        for sel in selectors:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    page.wait_for_load_state("networkidle", timeout=8000)
                    log.info("  Form submitted")
                    return True
            except Exception:
                continue
        return False

    def _read_file(self, path: Path) -> str:
        if path and path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _load_cookies(self, context, cookie_file: str):
        import json
        try:
            cookie_path = Path(cookie_file)
            if cookie_path.exists():
                context.add_cookies(json.loads(cookie_path.read_text()))
        except Exception:
            pass
