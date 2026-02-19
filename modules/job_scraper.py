"""Job scraping via SerpAPI Google Jobs engine.

Aggregates results from LinkedIn, Indeed, Glassdoor, etc. without
direct scraping (legal and reliable).
"""

from serpapi import GoogleSearch
from utils.logger import logger
from utils.rate_limiter import rate_limit


class JobScraper:
    def __init__(self, api_key: str, config: dict):
        self.api_key = api_key
        self.roles = config["search"]["roles"]
        self.locations = config["search"]["locations"]
        self.date_posted = config["search"].get("date_posted", "week")
        self.max_pages = config["scraping"].get("max_pages", 3)

    def search_jobs(self) -> list[dict]:
        """Search all configured roles across all locations."""
        all_jobs = []
        seen_ids = set()

        for role in self.roles:
            for location in self.locations:
                logger.info(f"Searching: '{role}' in '{location}'")
                jobs = self._search_google_jobs(role, location)
                for job in jobs:
                    jid = job.get("job_id", job.get("url", ""))
                    if jid and jid not in seen_ids:
                        seen_ids.add(jid)
                        all_jobs.append(job)

        logger.info(f"Total unique jobs found: {len(all_jobs)}")
        return all_jobs

    @rate_limit(seconds=5)
    def _search_google_jobs(self, query: str, location: str) -> list[dict]:
        """Query SerpAPI Google Jobs endpoint."""
        all_results = []

        for page in range(self.max_pages):
            params = {
                "engine": "google_jobs",
                "q": query,
                "location": location,
                "chips": f"date_posted:{self.date_posted}",
                "start": page * 10,
                "api_key": self.api_key,
            }

            try:
                search = GoogleSearch(params)
                results = search.get_dict()
                jobs = results.get("jobs_results", [])

                if not jobs:
                    break

                parsed = self._parse_results(jobs, query)
                all_results.extend(parsed)
                logger.info(f"  Page {page + 1}: {len(jobs)} results")

            except Exception as e:
                logger.error(f"SerpAPI error for '{query}' page {page}: {e}")
                break

        return all_results

    def _parse_results(self, raw_jobs: list, search_query: str) -> list[dict]:
        """Normalize raw SerpAPI results into standard job dicts."""
        jobs = []
        for job in raw_jobs:
            apply_options = job.get("apply_options", [])
            apply_url = apply_options[0].get("link", "") if apply_options else ""

            extensions = job.get("detected_extensions", {})

            jobs.append({
                "title": job.get("title", ""),
                "company": job.get("company_name", ""),
                "location": job.get("location", ""),
                "description": job.get("description", ""),
                "url": apply_url,
                "source": job.get("via", ""),
                "date_posted": extensions.get("posted_at", ""),
                "job_id": job.get("job_id", ""),
                "search_query": search_query,
                "salary": extensions.get("salary", ""),
                "schedule": extensions.get("schedule_type", ""),
            })
        return jobs
