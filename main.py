"""Job Application Agent — Main Pipeline Orchestrator.

Runs the full pipeline:
  1. Scrape jobs via SerpAPI
  2. Add new jobs to Google Sheet
  3. Find recruiter emails via Hunter.io
  4. Tailor resume for each job via Claude AI
  5. Send outreach emails via Gmail
  6. Auto-apply where possible (Greenhouse/Lever)
"""

import os
import sys
import yaml
from datetime import datetime
from dotenv import load_dotenv

from modules.job_scraper import JobScraper
from modules.sheets_tracker import SheetsTracker
from modules.email_finder import EmailFinder
from modules.resume_tailor import ResumeTailor
from modules.email_sender import EmailSender
from modules.auto_applier import AutoApplier
from modules.notifier import Notifier
from utils.logger import logger


def load_config(path="config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def run_pipeline():
    """Execute the full job application pipeline."""
    load_dotenv()
    config = load_config()

    logger.info("=" * 60)
    logger.info(f"Pipeline started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    stats = {
        "jobs_found": 0,
        "new_jobs_added": 0,
        "emails_found": 0,
        "resumes_tailored": 0,
        "emails_sent": 0,
        "auto_applied": 0,
    }

    # Initialize modules
    notifier = Notifier(config)

    try:
        tracker = SheetsTracker(
            os.getenv("GOOGLE_CREDENTIALS_PATH"),
            os.getenv("GOOGLE_SHEETS_ID"),
        )
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        notifier.notify_error(f"Google Sheets connection failed: {e}")
        return

    # --- Step 1: Scrape Jobs ---
    logger.info("Step 1: Scraping jobs...")
    try:
        scraper = JobScraper(os.getenv("SERPAPI_API_KEY"), config)
        all_jobs = scraper.search_jobs()
        stats["jobs_found"] = len(all_jobs)

        added_jobs = []
        for job in all_jobs:
            if tracker.add_job(job):
                added_jobs.append(job)
        stats["new_jobs_added"] = len(added_jobs)

        logger.info(f"Found {len(all_jobs)} jobs, {len(added_jobs)} new")
        if added_jobs:
            notifier.notify_new_jobs(added_jobs)

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        notifier.notify_error(f"Scraping failed: {e}")

    # --- Step 2: Find Recruiter Emails ---
    logger.info("Step 2: Finding recruiter emails...")
    try:
        finder = EmailFinder(os.getenv("HUNTER_API_KEY"), config)
        new_jobs = tracker.get_jobs_by_status("New")

        for job_row in new_jobs:
            result = finder.find_recruiter_email(
                job_row["Company"], job_row["Role"]
            )
            if result:
                tracker.update_job(job_row["_row_index"], {
                    "Status": "Email Found",
                    "Recruiter Name": result["name"],
                    "Recruiter Email": result["email"],
                })
                stats["emails_found"] += 1

        logger.info(f"Found emails for {stats['emails_found']} jobs")

    except Exception as e:
        logger.error(f"Email finding failed: {e}")
        notifier.notify_error(f"Email finding failed: {e}")

    # --- Step 3: Tailor Resumes ---
    logger.info("Step 3: Tailoring resumes...")
    try:
        tailor = ResumeTailor(config)
        email_found_jobs = tracker.get_jobs_by_status("Email Found")

        for job_row in email_found_jobs:
            try:
                pdf_path = tailor.tailor_resume(job_row)
                tracker.update_job(job_row["_row_index"], {
                    "Status": "Resume Tailored",
                    "Resume Version": os.path.basename(pdf_path),
                })
                stats["resumes_tailored"] += 1
            except Exception as e:
                logger.error(f"Resume tailoring failed for {job_row['Company']}: {e}")

        logger.info(f"Tailored {stats['resumes_tailored']} resumes")

    except Exception as e:
        logger.error(f"Resume tailor init failed: {e}")
        notifier.notify_error(f"Resume tailoring failed: {e}")

    # --- Step 4: Send Outreach Emails ---
    if config["email_outreach"]["enabled"]:
        logger.info("Step 4: Sending outreach emails...")
        try:
            sender = EmailSender(config)
            ready_jobs = tracker.get_jobs_by_status("Resume Tailored")

            for job_row in ready_jobs:
                resume_file = job_row.get("Resume Version", "")
                resume_path = os.path.join(config["resume"]["output_dir"], resume_file)

                if not os.path.exists(resume_path):
                    logger.warning(f"Resume not found: {resume_path}")
                    continue

                success = sender.send_outreach(
                    {"email": job_row["Recruiter Email"], "name": job_row["Recruiter Name"]},
                    job_row,
                    resume_path,
                )
                if success:
                    tracker.update_job(job_row["_row_index"], {
                        "Status": "Email Sent",
                        "Date Applied": datetime.now().strftime("%Y-%m-%d"),
                    })
                    stats["emails_sent"] += 1

                if sender.sends_remaining <= 0:
                    logger.info("Daily email limit reached, stopping sends")
                    break

            logger.info(f"Sent {stats['emails_sent']} outreach emails")

        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            notifier.notify_error(f"Email sending failed: {e}")
    else:
        logger.info("Step 4: Email outreach disabled in config, skipping")

    # --- Step 5: Auto-Apply ---
    logger.info("Step 5: Auto-applying where possible...")
    try:
        applier = AutoApplier(applicant_info={
            "first_name": config["email_outreach"]["from_name"].split()[0],
            "last_name": config["email_outreach"]["from_name"].split()[-1],
            "email": os.getenv("GMAIL_SENDER_EMAIL", ""),
        })

        sent_jobs = tracker.get_jobs_by_status("Email Sent")
        for job_row in sent_jobs:
            url = job_row.get("URL", "")
            ats = applier.can_auto_apply(url)
            if ats:
                resume_file = job_row.get("Resume Version", "")
                resume_path = os.path.join(config["resume"]["output_dir"], resume_file)
                if applier.apply(url, resume_path):
                    tracker.update_job(job_row["_row_index"], {"Status": "Applied"})
                    stats["auto_applied"] += 1

        logger.info(f"Auto-applied to {stats['auto_applied']} jobs")

    except Exception as e:
        logger.error(f"Auto-apply failed: {e}")

    # --- Summary ---
    logger.info("-" * 40)
    logger.info("Pipeline Summary:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    logger.info("=" * 60)

    notifier.notify_summary(stats)
    return stats


def main():
    """Entry point with basic arg handling."""
    if "--dry-run" in sys.argv:
        logger.info("DRY RUN MODE — no emails will be sent")
        load_dotenv()
        config = load_config()
        config["email_outreach"]["enabled"] = False

        scraper = JobScraper(os.getenv("SERPAPI_API_KEY"), config)
        jobs = scraper.search_jobs()
        for job in jobs[:5]:
            print(f"  {job['title']} at {job['company']} — {job['url'][:60]}")
        print(f"\nTotal: {len(jobs)} jobs found")
    else:
        run_pipeline()


if __name__ == "__main__":
    main()
