"""Google Sheets integration for job tracking.

Manages a spreadsheet with job listings, status tracking, and dedup.
"""

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from utils.logger import logger
from utils.dedup import normalize_url


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COLUMNS = [
    "Job ID", "Company", "Role", "Location", "URL", "Source",
    "Status", "Recruiter Name", "Recruiter Email",
    "Date Found", "Date Applied", "Resume Version",
    "Description", "Notes",
]

# Status flow: New → Email Found → Resume Tailored → Email Sent → Applied → Replied/Rejected


class SheetsTracker:
    def __init__(self, credentials_path: str, sheet_id: str):
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        client = gspread.authorize(creds)
        self.sheet = client.open_by_key(sheet_id).sheet1
        self._ensure_headers()
        self._url_cache = None

    def _ensure_headers(self):
        """Create header row if sheet is empty."""
        try:
            existing = self.sheet.row_values(1)
            if not existing:
                self.sheet.append_row(COLUMNS)
                logger.info("Created header row in Google Sheet")
        except Exception as e:
            logger.error(f"Failed to check/create headers: {e}")

    def add_job(self, job: dict) -> bool:
        """Add a job if it's not a duplicate. Returns True if added."""
        if self._is_duplicate(job.get("url", "")):
            return False

        row = [
            job.get("job_id", ""),
            job.get("company", ""),
            job.get("title", ""),
            job.get("location", ""),
            job.get("url", ""),
            job.get("source", ""),
            "New",
            "",  # Recruiter Name
            "",  # Recruiter Email
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            "",  # Date Applied
            "",  # Resume Version
            job.get("description", "")[:500],  # Truncate for sheet
            "",  # Notes
        ]

        try:
            self.sheet.append_row(row, value_input_option="USER_ENTERED")
            self._url_cache = None  # Invalidate cache
            return True
        except Exception as e:
            logger.error(f"Failed to add job to sheet: {e}")
            return False

    def get_all_job_urls(self) -> set[str]:
        """Get all tracked URLs for dedup. Cached per run."""
        if self._url_cache is not None:
            return self._url_cache

        try:
            col_index = COLUMNS.index("URL") + 1
            urls = self.sheet.col_values(col_index)[1:]  # Skip header
            self._url_cache = {normalize_url(u) for u in urls if u}
            return self._url_cache
        except Exception as e:
            logger.error(f"Failed to get URLs from sheet: {e}")
            return set()

    def _is_duplicate(self, url: str) -> bool:
        if not url:
            return False
        return normalize_url(url) in self.get_all_job_urls()

    def get_jobs_by_status(self, status: str) -> list[dict]:
        """Get all jobs with a given status as list of dicts with row index."""
        try:
            records = self.sheet.get_all_records()
            result = []
            for i, record in enumerate(records):
                if record.get("Status") == status:
                    record["_row_index"] = i + 2  # +2 for header + 0-index
                    result.append(record)
            return result
        except Exception as e:
            logger.error(f"Failed to get jobs by status '{status}': {e}")
            return []

    def update_job(self, row_index: int, updates: dict):
        """Update specific columns for a job row.

        Args:
            row_index: 1-based row index in the sheet.
            updates: Dict mapping column names to new values.
        """
        try:
            batch = []
            for col_name, value in updates.items():
                if col_name in COLUMNS:
                    col_index = COLUMNS.index(col_name) + 1
                    batch.append({
                        "range": gspread.utils.rowcol_to_a1(row_index, col_index),
                        "values": [[value]],
                    })

            if batch:
                self.sheet.batch_update(batch, value_input_option="USER_ENTERED")

        except Exception as e:
            logger.error(f"Failed to update row {row_index}: {e}")

    def invalidate_cache(self):
        """Force URL cache refresh on next check."""
        self._url_cache = None
