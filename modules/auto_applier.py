"""Auto-apply to jobs via ATS APIs (Greenhouse, Lever).

Only applies to jobs hosted on supported ATS platforms.
All others are opened in browser for manual application.
"""

import re
import os
import requests
import webbrowser
from utils.logger import logger


class AutoApplier:
    SUPPORTED_ATS = {
        "greenhouse": r"boards\.greenhouse\.io",
        "lever": r"jobs\.lever\.co",
    }

    def __init__(self, applicant_info: dict = None):
        """
        Args:
            applicant_info: Dict with keys: first_name, last_name, email,
                           phone, linkedin_url
        """
        self.applicant = applicant_info or {}

    def can_auto_apply(self, job_url: str) -> str | None:
        """Check if auto-apply is possible. Returns ATS name or None."""
        for ats, pattern in self.SUPPORTED_ATS.items():
            if re.search(pattern, job_url):
                return ats
        return None

    def apply(self, job_url: str, resume_path: str) -> bool:
        """Attempt to auto-apply. Returns True if successful."""
        ats = self.can_auto_apply(job_url)

        if ats == "greenhouse":
            return self._apply_greenhouse(job_url, resume_path)
        elif ats == "lever":
            return self._apply_lever(job_url, resume_path)
        else:
            return False

    def open_in_browser(self, job_url: str):
        """Fallback: open application URL in default browser."""
        logger.info(f"Opening in browser for manual apply: {job_url}")
        webbrowser.open(job_url)

    def _apply_greenhouse(self, job_url: str, resume_path: str) -> bool:
        """Submit via Greenhouse public application API.

        URL format: https://boards.greenhouse.io/company/jobs/12345
        API: POST https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{id}/applications
        """
        match = re.search(r"boards\.greenhouse\.io/(\w+)/jobs/(\d+)", job_url)
        if not match:
            logger.warning(f"Could not parse Greenhouse URL: {job_url}")
            return False

        board_token, job_id = match.groups()
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}/applications"

        try:
            with open(resume_path, "rb") as resume_file:
                data = {
                    "first_name": self.applicant.get("first_name", ""),
                    "last_name": self.applicant.get("last_name", ""),
                    "email": self.applicant.get("email", ""),
                    "phone": self.applicant.get("phone", ""),
                }
                files = {"resume": (os.path.basename(resume_path), resume_file, "application/pdf")}
                resp = requests.post(api_url, data=data, files=files, timeout=30)

            if resp.status_code in (200, 201):
                logger.info(f"Greenhouse auto-apply successful: {job_url}")
                return True
            else:
                logger.warning(f"Greenhouse apply failed ({resp.status_code}): {resp.text[:200]}")
                return False

        except Exception as e:
            logger.error(f"Greenhouse apply error: {e}")
            return False

    def _apply_lever(self, job_url: str, resume_path: str) -> bool:
        """Submit via Lever postings API.

        URL format: https://jobs.lever.co/company/posting-id
        API: POST https://api.lever.co/v0/postings/{company}/{id}/apply
        """
        match = re.search(r"jobs\.lever\.co/([\w-]+)/([\w-]+)", job_url)
        if not match:
            logger.warning(f"Could not parse Lever URL: {job_url}")
            return False

        company, posting_id = match.groups()
        api_url = f"https://api.lever.co/v0/postings/{company}/{posting_id}/apply"

        try:
            name = f"{self.applicant.get('first_name', '')} {self.applicant.get('last_name', '')}".strip()
            with open(resume_path, "rb") as resume_file:
                data = {
                    "name": name,
                    "email": self.applicant.get("email", ""),
                    "phone": self.applicant.get("phone", ""),
                    "urls[LinkedIn]": self.applicant.get("linkedin_url", ""),
                }
                files = {"resume": (os.path.basename(resume_path), resume_file, "application/pdf")}
                resp = requests.post(api_url, data=data, files=files, timeout=30)

            if resp.status_code in (200, 201):
                logger.info(f"Lever auto-apply successful: {job_url}")
                return True
            else:
                logger.warning(f"Lever apply failed ({resp.status_code}): {resp.text[:200]}")
                return False

        except Exception as e:
            logger.error(f"Lever apply error: {e}")
            return False
