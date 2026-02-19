"""Recruiter/hiring manager email discovery via Hunter.io API."""

import requests
from utils.logger import logger
from utils.rate_limiter import rate_limit

HUNTER_BASE = "https://api.hunter.io/v2"


class EmailFinder:
    def __init__(self, api_key: str, config: dict):
        self.api_key = api_key
        self.max_lookups = config["email_finder"].get("max_lookups_per_run", 20)
        self._lookup_count = 0

    def find_recruiter_email(self, company: str, role_title: str) -> dict | None:
        """Find recruiter/hiring manager email for a company.

        Returns {"email": ..., "name": ..., "confidence": ..., "position": ...}
        or None if not found or limit reached.
        """
        if self._lookup_count >= self.max_lookups:
            logger.warning("Email lookup limit reached for this run")
            return None

        self._lookup_count += 1

        # Try HR/recruiting department first, then management
        for department in ["hr", "management", None]:
            result = self._domain_search(company, department=department)
            if result:
                best = self._pick_best_contact(result, role_title)
                if best:
                    logger.info(f"Found email for {company}: {best['email']}")
                    return best

        logger.info(f"No email found for {company}")
        return None

    @rate_limit(seconds=2)
    def _domain_search(self, company: str, department: str = None) -> list[dict]:
        """Search Hunter.io for emails at a company."""
        params = {
            "company": company,
            "api_key": self.api_key,
            "limit": 10,
        }
        if department:
            params["department"] = department

        try:
            resp = requests.get(f"{HUNTER_BASE}/domain-search", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json().get("data", {})
            return data.get("emails", [])
        except requests.RequestException as e:
            logger.error(f"Hunter.io API error for '{company}': {e}")
            return []

    def _pick_best_contact(self, emails: list, role_title: str) -> dict | None:
        """Prioritize contacts: recruiter > talent > HR > hiring manager."""
        priority_keywords = ["recruit", "talent", "hiring", "people", "hr", "university"]

        for keyword in priority_keywords:
            for e in emails:
                position = (e.get("position") or "").lower()
                if keyword in position:
                    return self._format_contact(e)

        # Fallback: highest confidence email
        if emails:
            best = max(emails, key=lambda e: e.get("confidence", 0))
            if best.get("confidence", 0) >= 50:
                return self._format_contact(best)

        return None

    def _format_contact(self, email_data: dict) -> dict:
        first = email_data.get("first_name", "")
        last = email_data.get("last_name", "")
        return {
            "email": email_data["value"],
            "name": f"{first} {last}".strip() or "Hiring Manager",
            "confidence": email_data.get("confidence", 0),
            "position": email_data.get("position", ""),
        }

    def verify_email(self, email: str) -> bool:
        """Verify if an email address is deliverable."""
        try:
            resp = requests.get(f"{HUNTER_BASE}/email-verifier", params={
                "email": email,
                "api_key": self.api_key,
            }, timeout=10)
            data = resp.json().get("data", {})
            return data.get("result") in ("deliverable", "risky")
        except requests.RequestException:
            return True  # Assume valid on error

    def reset_counter(self):
        """Reset the per-run lookup counter."""
        self._lookup_count = 0
