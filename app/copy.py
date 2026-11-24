"""Approved brand and operational copy.

Every string in :data:`COPY` comes from the approved brand-and-copy document and
must be rendered verbatim. Do not paraphrase, re-case, or punctuate differently.
"""

from __future__ import annotations

BRAND_NAME = "MountGuard Backup"

# The full copy deck is exposed as a flat, stable mapping so templates can use
# ``copy.hero_headline`` style lookups. Values are VERBATIM approved strings.
COPY = {
    # Hero
    "hero_headline": "Unix Backup Jobs You Can Trust",
    "hero_subhead": (
        "Select folders, deselect what to exclude, schedule rsync-backed jobs, "
        "and restore files to their original or alternate location."
    ),
    # Section headings
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
    # Primary CTA labels
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
    # Secondary CTA labels
    "cta_cancel": "Cancel",
    "cta_back_to_jobs": "Back to Jobs",
    "cta_back_to_run": "Back to Run",
    "cta_clear_filters": "Clear Filters",
    "cta_refresh_logs": "Refresh Logs",
    # Status labels
    "status_scheduled": "Scheduled",
    "status_running": "Running",
    "status_success": "Success",
    "status_failure": "Failure",
    "status_skipped": "Skipped",
    "status_no_runs": "No Runs",
    "status_running_now": "Running now",
    "status_last_run": "Last run",
    # Footer lines
    "contact_line": "Contact: Your system administration team.",
    "pricing_line": "Pricing: Self-hosted with no license fee.",
    # Field labels (job editor)
    "field_job_name": "Job Name",
    "field_source_path": "Source Path",
    "field_destination_path": "Destination Path",
    "field_dest_subfolder": "Destination Subfolder (optional)",
    "field_schedule_cron": "Schedule (Cron)",
    "field_timezone": "Time Zone",
    "field_next_run": "Next Scheduled Run",
    "field_run_history": "Run History",
    # Toggle / confirmation labels
    "label_enabled": "Enable Job",
    "label_delete_mode": "Delete Mode",
    "label_checksum_mode": "Verify Checksums",
    "label_metadata_mode": "Preserve Metadata",
    "label_confirm_missing_destination": "Create this missing destination on the next run",
    "label_confirm_dest_inside_source": "Destination is inside the source — I understand the risk",
    "label_confirm_delete_mode": "Confirm Delete Mode",
    # Field helpers
    "help_source_path": "The folder to back up.",
    "help_destination_path": "Where the backup is written.",
    "help_dest_subfolder": "Optional subfolder name created under the destination.",
    "help_schedule_cron": "Five-field cron, for example: 0 2 * * * (02:00 every day).",
    "help_exclusions": "One path or glob per line. Deselect folders in the tree to exclude them.",
    "help_delete_mode": "Mirror the source by removing files that no longer exist in the source.",
    "help_checksum_mode": "Compare checksums instead of modification times.",
    "help_metadata_mode": "Preserve permissions, ownership, and timestamps.",
    # Dashboard / detail labels
    "empty_jobs_title": "No backup jobs yet",
    "empty_jobs_body": "Create your first backup job to start protecting a folder.",
    "label_total_jobs": "Total Jobs",
    "label_scheduled": "Scheduled",
    "label_running_now": "Running Now",
    "label_last_runs": "Recent Runs",
    "label_source": "Source",
    "label_destination": "Destination",
    "label_duration": "Duration",
    "label_status": "Status",
    "label_schedule": "Schedule",
    "no_schedule_set": "No schedule set",
    "nav_new_job": "New",
}
