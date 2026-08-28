# MikroTikBackup

A single Python tool for automating backups of MikroTik routers over SSH/SFTP: connects to each
router, saves a config backup, downloads it locally, and removes it from the router. Run it once
manually, on a daily cron job (Linux/macOS), or as a Windows service — all from one script.

### Prerequisites

    Python 3.x: Download Python
    Paramiko: For SSH connections.
    PyWin32: Only required if you want to run this as a Windows service.

### Installing

    git clone https://github.com/ericonasis/MikroTikBackup.git
    cd MikroTikBackup
    pip install -r requirements.txt

### Configuration

Copy `config.example.json` to `config.json` and fill in your router details:

    cp config.example.json config.json

`config.json` is git-ignored, so real router credentials never end up committed to the repo.

    {
      "routers": [
        {"name": "branch-office", "host": "192.168.88.1", "port": 22, "username": "admin", "password": "..."}
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

Settings:

    connect_retries / retry_delay: retry SSH connection this many times before giving up on a router.
    backup_ready_timeout: how long to poll the router for the backup file before failing the transfer
        (replaces a fixed blind wait).
    retention_days: local backups older than this are deleted automatically. Set to 0 to keep forever.
    backup_password: if set, backups are saved password-protected (`/system backup save password=...`).
    max_parallel: how many routers to back up concurrently. 1 = sequential (default). Raise this if you
        have many routers and want faster runs.
    export_config: if true, also saves a human-readable `.rsc` config export (via `/export`) alongside
        the binary `.backup` file. Unlike the binary backup, `.rsc` files are diffable/versionable — put
        `local_backup_path` under git if you want a history of config changes. Export failures don't
        affect the backup result.
    notify: optional failure notifications. Example:

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

        webhook_type: "slack", "discord", "ntfy", or "generic" (posts `{"text": message}` as JSON).
        Set webhook_url and/or email — both fire if both are set. on_failure_only (default true) skips
        notifying on fully-successful runs.

### Running once

    python mikrotik_backup.py run

Connects to each router, creates a backup, transfers it locally, and deletes it from the router.

### Running on a schedule (Linux/macOS)

    python mikrotik_backup.py install-cron              # daily at 02:00
    python mikrotik_backup.py install-cron --time 03:30  # or pick a time
    python mikrotik_backup.py uninstall-cron             # remove it

This adds a line to your user crontab that runs `mikrotik_backup.py run` daily, logging to
`logs/cron.log`.

### Running as a Windows service

    python mikrotik_backup.py service install
    python mikrotik_backup.py service start

Runs `run` once per day in the background. Logs go to a daily file in the `logs` directory next to
the script.

Manage it with:

    python mikrotik_backup.py service stop
    python mikrotik_backup.py service remove

### Contributing

Contributions are welcome! Please fork this repository and submit a pull request with your changes.
