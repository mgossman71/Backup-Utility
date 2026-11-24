# MountGuard Backup

A self-contained backup dashboard you run **on each Ubuntu server** and manage
from a **web UI**. Each host runs its own copy, sees its own filesystem, and runs
incremental `rsync` backups on the schedule you set.

- FastAPI + SQLite (jobs + run history) + APScheduler + `rsync`
- Web dashboard: create/edit/delete jobs, browse the file tree to pick sources,
  exclude paths, schedule in Central time (CST/CDT), watch run logs, restore files
- No database server, no agent fleet, no external services

> This app has **no built-in login**. It is meant for a trusted network. Keep it
> on a LAN/VPN or firewall port 8000 (see [Security](#security)).

---

## Requirements (Ubuntu / Debian)

- Ubuntu 20.04+/Debian 11+
- `rsync` and Python 3 (installed automatically by `install.sh`)

## Install on a server

```bash
git clone https://github.com/mgossman71/Backup-Utility.git backup-ui
cd backup-ui
sudo ./install.sh
```

That's it. The installer:

1. `apt-get` installs `rsync`, `python3`, `python3-venv`, `python3-pip`.
2. Creates a virtualenv and installs the Python requirements.
3. Writes `/etc/mountguard-backup.env` and a systemd unit, then starts the service.
4. Prints the dashboard URL, e.g. `http://<server-ip>:8000`.

Open that URL in a browser, click **Create Backup Job**, and you're backing up.

Manage the service:

```bash
systemctl status mountguard-backup     # health
journalctl -u mountguard-backup -f     # live service logs
sudo systemctl restart mountguard-backup
```

### Manual run (no systemd)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run.sh            # reads /etc/mountguard-backup.env if present
```

---

## Adding a backup job

1. **Name** the job.
2. **Source path** — type it or use **Browse Source** to walk the tree. Use the
   checkbox tree to **exclude** subfolders (they land in *Exclusions*).
3. **Destination path** — where the backup is written (Browse Destination). It may
   be a path that doesn't exist yet if its parent is writable (confirm to create it).
4. **Schedule** — pick a timezone and a cron expression (`0 2 * * *` = 02:00
   daily in that zone). The dashboard shows the next run time.
5. **Options** — metadata / checksum / delete-mode (mirror), then **Save Job**.
6. **Run Job Now** or wait for the schedule. Click a run for full `rsync` logs.

**Safety rails:** empty/unreadable sources and unwritable destinations are
rejected; a destination inside its own source, or enabling delete-mode, each
require an explicit confirmation checkbox. Deleting a job removes only its record —
never your source or backup files.

---

## Configuration

Everything lives in `/etc/mountguard-backup.env` (see `.env.example`). Key values:

| Variable | Default | Meaning |
|---|---|---|
| `BACKUP_UI_HOST` / `BACKUP_UI_PORT` | `0.0.0.0` / `8000` | bind address/port |
| `BACKUP_UI_STATE_DIR` | `/var/lib/backup-ui` | SQLite `backup.db` |
| `BACKUP_UI_LOG_DIR` | `/var/log/backup-ui` | per-run rsync logs |
| `BACKUP_UI_TIMEZONE` | `America/Chicago` | default job timezone |
| `BACKUP_UI_RSYNC` | `rsync` | rsync binary |
| `BACKUP_UI_MAX_RUNS` | `50` | run history kept per job |

Change the port (e.g. if 8000 is taken): edit `/etc/mountguard-backup.env`, then
`sudo systemctl restart mountguard-backup`.

---

## Security

There is no authentication — anyone who can reach the port can manage backups.
Choose one:

- Keep the server on a private network / VPN and open port 8000 only there, or
- Restrict with a firewall: `sudo ufw allow from 10.0.0.0/24 to any port 8000`, or
- Put it behind a reverse proxy with TLS + basic auth / mTLS.

The app does enforce CSRF + same-origin checks on all create/edit/delete/run actions.

---

## Updating

```bash
cd backup-ui && git pull
sudo ./install.sh        # re-runs cleanly; jobs/DB and logs are preserved
```

## Uninstalling

```bash
sudo ./uninstall.sh            # remove the service, keep jobs/logs
sudo ./uninstall.sh --purge    # also delete jobs DB and run logs
```

---

## Docker (optional)

A `Dockerfile` + `docker-compose.example.yml` exist, but the **native install
above is the recommended path.** Docker only sees folders you bind-mount, and on
**macOS Docker Desktop a folder must also be listed in Settings → Resources →
File Sharing** (which is why mounting `/opt` etc. fails there). For backing up a
server's own files, just run natively.
