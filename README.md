# MikroTikBackup

A Python tool for automating backups of MikroTik routers over SSH/SFTP. For every router it lists,
it connects over SSH, saves a config backup, downloads it locally, and deletes it from the router —
so backups never pile up on router storage.

One script, three ways to run it: on demand, on a daily cron job (Linux/macOS), or as a Windows
service.

## Features

- **Binary + text backups** — the standard `.backup` file, plus an optional diffable `.rsc` config
  export you can version in git.
- **Password-protected backups** — optional, via RouterOS's own backup encryption.
- **Resilient transfers** — retries failed SSH connections with backoff, and polls for the backup
  file to actually exist on the router instead of guessing with a fixed delay.
- **Parallel runs** — back up many routers concurrently instead of one at a time.
- **Local retention** — automatically prune backups older than N days.
- **Failure notifications** — Slack, Discord, ntfy, a generic webhook, or email.
- **Credentials stay out of git** — router details live in a `config.json` that's git-ignored by
  default; only an example template is committed.

## Requirements

- Python 3.x
- [paramiko](https://www.paramiko.org/) for SSH/SFTP
- [pywin32](https://github.com/mhammond/pywin32) — only needed if you run this as a Windows service

## Installation

```sh
git clone https://github.com/ericonasis/MikroTikBackup.git
cd MikroTikBackup
pip install -r requirements.txt
```

## Configuration

Copy the example config and fill in your routers:

```sh
cp config.example.json config.json
```

`config.json` is listed in `.gitignore`, so real router credentials never end up committed.

```json
{
  "routers": [
    {
      "name": "branch-office",
      "host": "192.168.88.1",
      "port": 22,
      "username": "admin",
      "password": "your-router-password"
    }
  ],
  "settings": {
    "local_backup_path": "C:\\MikroTikBackups",
    "connection_timeout": 10,
    "connect_retries": 3,
    "retry_delay": 5,
    "backup_ready_timeout": 60,
    "retention_days": 30,
    "backup_password": null,
    "max_parallel": 1,
    "export_config": false,
    "notify": null
  }
}
```

Add one entry to `routers` per device. `name` is optional — if the SSH connection succeeds, the
backup is named after the router's actual RouterOS identity instead.

### Settings reference

| Setting | Default | Meaning |
|---|---|---|
| `local_backup_path` | — | Where backups are saved locally. Created automatically if missing. |
| `connection_timeout` | `10` | Seconds to wait for a single SSH connection attempt. |
| `connect_retries` | `3` | How many times to retry a failed connection before giving up on a router. |
| `retry_delay` | `5` | Seconds to wait between connection retries. |
| `backup_ready_timeout` | `60` | Seconds to poll the router for the backup file before failing the transfer. |
| `retention_days` | `30` | Delete local backups older than this. `0` keeps everything forever. |
| `backup_password` | `null` | If set, backups are saved password-protected (`/system backup save password=...`). |
| `max_parallel` | `1` | Routers to back up concurrently. `1` = sequential; raise it for large fleets. |
| `export_config` | `false` | Also save a human-readable `.rsc` export via `/export`, alongside the binary backup. |
| `notify` | `null` | Failure notifications — see below. |

**`export_config`**: binary `.backup` files aren't diffable. With this on, each run also saves a
plain-text `.rsc` script export next to it — put `local_backup_path` under its own git repo if you
want a real history of config changes over time. Export failures are logged but don't affect the
backup's success/failure result.

**`notify`**: sends an alert when routers fail (or every run, if you want). Any combination of a
webhook and email:

```json
"notify": {
  "on_failure_only": true,
  "webhook_url": "https://hooks.slack.com/services/...",
  "webhook_type": "slack",
  "email": {
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "username": "alerts@example.com",
    "password": "...",
    "from": "alerts@example.com",
    "to": ["you@example.com"]
  }
}
```

- `webhook_type`: `"slack"`, `"discord"`, `"ntfy"`, or `"generic"` (posts `{"text": message}` as JSON).
- `on_failure_only` (default `true`): skip notifying when every router backs up successfully.
- Set `webhook_url` and/or `email` — both fire if both are present.

## Usage

### Run once

```sh
python mikrotik_backup.py run
```

Backs up every router in `config.json`, right now, and prints progress to the console.

### Schedule it (Linux/macOS)

```sh
python mikrotik_backup.py install-cron               # daily at 02:00
python mikrotik_backup.py install-cron --time 03:30   # or pick a time
python mikrotik_backup.py uninstall-cron              # remove it
```

Adds a single line to your user crontab that runs `run` daily, logging to `logs/cron.log`. Only that
one managed line is touched — the rest of your crontab is left alone.

### Run as a Windows service

```sh
python mikrotik_backup.py service install
python mikrotik_backup.py service start
```

Runs a backup once per day in the background. Logs go to a daily file in the `logs` directory next
to the script, and `config.json` is reloaded on every run — no restart needed after adding a router.

```sh
python mikrotik_backup.py service stop
python mikrotik_backup.py service remove
```

## How it works

For each router: connect over SSH (retrying on failure) → run `/system backup save` (and
`/export`, if `export_config` is on) → poll until the file appears → download it over SFTP → delete
it from the router. Local files past `retention_days` are pruned at the end of the run, and a
notification fires if configured.

## Project layout

| File | Purpose |
|---|---|
| `mikrotik_backup.py` | CLI entrypoint — `run`, `install-cron`/`uninstall-cron`, `service`. |
| `mikrotik_backup_lib.py` | Core backup logic shared by every run mode. |
| `windows_service.py` | Windows service wrapper (only relevant with pywin32 installed). |
| `notifications.py` | Webhook and email senders for failure notifications. |
| `config.example.json` | Template — copy to `config.json` and fill in real router details. |

## Security notes

- `config.json` holds plaintext router credentials — keep it out of version control (already
  git-ignored) and restrict its file permissions on shared machines.
- Unknown SSH host keys are auto-accepted (`paramiko.AutoAddPolicy`) so first-time connections don't
  require manual intervention. This trades off some MITM protection for convenience; on a hostile
  network, pin host keys instead.
- Use `backup_password` if backup files themselves need to be protected at rest — a MikroTik
  `.backup` file contains the full router configuration, including other stored credentials.

## Contributing

Contributions are welcome — fork the repo and submit a pull request.
