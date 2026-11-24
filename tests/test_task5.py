"""Task 5 acceptance tests: approved copy is used verbatim."""

from __future__ import annotations

from app import copy as copy_module

# Canonical approved strings from brand-and-copy.md.
EXPECTED = {
    "hero_headline": "Unix Backup Jobs You Can Trust",
    "hero_subhead": (
        "Select folders, deselect what to exclude, schedule rsync-backed jobs, "
        "and restore files to their original or alternate location."
    ),
    "dashboard": "Dashboard",
    "backup_jobs": "Backup Jobs",
    "create_backup_job": "Create Backup Job",
    "edit_backup_job": "Edit Backup Job",
    "job_details": "Job Details",
    "source_selection": "Source Selection",
    "exclusions": "Exclusions",
    "schedule": "Schedule",
    "destination_settings": "Destination Settings",
    "run_history": "Run History",
    "restore": "Restore",
    "settings": "Settings",
    "cta_create_backup_job": "Create Backup Job",
    "cta_save_job": "Save Job",
    "cta_run_job_now": "Run Job Now",
    "cta_edit_job": "Edit Job",
    "cta_delete_job": "Delete Job",
    "cta_restore_files": "Restore Files",
    "cta_save_schedule": "Save Schedule",
    "cta_browse_source": "Browse Source",
    "cta_browse_destination": "Browse Destination",
    "cta_save_restore_settings": "Save Restore Settings",
    "cta_confirm_job_deletion": "Confirm Job Deletion",
    "cta_confirm_delete_mode": "Confirm Delete Mode",
    "cta_cancel": "Cancel",
    "cta_back_to_jobs": "Back to Jobs",
    "cta_back_to_run": "Back to Run",
    "cta_clear_filters": "Clear Filters",
    "cta_refresh_logs": "Refresh Logs",
    "status_scheduled": "Scheduled",
    "status_running": "Running",
    "status_success": "Success",
    "status_failure": "Failure",
    "status_skipped": "Skipped",
    "status_no_runs": "No Runs",
    "status_running_now": "Running now",
    "status_last_run": "Last run",
    "contact_line": "Contact: Your system administration team.",
    "pricing_line": "Pricing: Self-hosted with no license fee.",
}


def test_copy_deck_matches_approved_strings_verbatim():
    for key, value in EXPECTED.items():
        assert copy_module.COPY[key] == value, f"mismatch for {key}"


def test_no_placeholder_or_marketing_copy():
    all_text = " ".join(copy_module.COPY.values()).lower()
    for bad in ["lorem", "ipsum", "coming soon", "todo", "placeholder"]:
        assert bad not in all_text


def test_hero_and_section_labels_render(client):
    html = client.get("/").text
    assert copy_module.COPY["hero_headline"] in html
    assert copy_module.COPY["hero_subhead"] in html
    assert copy_module.COPY["dashboard"] in html
    assert copy_module.COPY["backup_jobs"] in html
    assert copy_module.COPY["create_backup_job"] in html  # nav label
    assert copy_module.COPY["settings"] in html
    assert copy_module.COPY["contact_line"] in html
    assert copy_module.COPY["pricing_line"] in html
