#!/usr/bin/env python3
"""Single entrypoint for MikroTik backups.

Usage:
    python mikrotik_backup.py run                    # back up everything once, right now
    python mikrotik_backup.py install-cron            # Linux/macOS: run daily via cron
    python mikrotik_backup.py uninstall-cron
    python mikrotik_backup.py service install|start|stop|remove   # Windows service
"""
import argparse
import logging
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
CRON_MARKER = "# mikrotik-backup (managed by mikrotik_backup.py)"

sys.path.insert(0, SCRIPT_DIR)


def _require_config():
    if not os.path.exists(CONFIG_PATH):
        print(
            f"Config file not found at {CONFIG_PATH}.\n"
            "Copy config.example.json to config.json and fill in your router details.",
            file=sys.stderr,
        )
        sys.exit(1)


def _console_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    return logging.getLogger("MikroTikBackup")


def cmd_run(args):
    from mikrotik_backup_lib import load_config, run_backups

    _require_config()
    logger = _console_logger()
    config = load_config(CONFIG_PATH)
    success, fails = run_backups(config, logger)
    sys.exit(1 if fails and not success else 0)


def cmd_service(args):
    if sys.platform != "win32":
        print("'service' mode is Windows-only. Use 'install-cron' on Linux/macOS instead.", file=sys.stderr)
        sys.exit(1)
    try:
        import win32serviceutil
    except ImportError:
        print("pywin32 is required for service mode: pip install pywin32", file=sys.stderr)
        sys.exit(1)

    from windows_service import MikroTikBackupService

    win32serviceutil.HandleCommandLine(MikroTikBackupService, argv=[sys.argv[0], args.action])


def cmd_install_cron(args):
    _require_config()
    try:
        hour_str, minute_str = args.time.split(":")
        hour, minute = int(hour_str), int(minute_str)
        assert 0 <= hour < 24 and 0 <= minute < 60
    except (ValueError, AssertionError):
        print(f"Invalid --time '{args.time}', expected HH:MM (24h)", file=sys.stderr)
        sys.exit(1)

    os.makedirs(LOG_DIR, exist_ok=True)
    cron_log = os.path.join(LOG_DIR, "cron.log")
    cron_line = (
        f"{minute} {hour} * * * cd {SCRIPT_DIR} && "
        f"{sys.executable} {os.path.abspath(__file__)} run >> {cron_log} 2>&1 {CRON_MARKER}"
    )

    existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    lines = existing.stdout.splitlines() if existing.returncode == 0 else []
    lines = [line for line in lines if CRON_MARKER not in line]
    lines.append(cron_line)

    proc = subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True)
    if proc.returncode == 0:
        print(f"Cron job installed: runs daily at {args.time}. Logs: {cron_log}")
    else:
        print("Failed to install cron job (is 'crontab' available?).", file=sys.stderr)
        sys.exit(1)


def cmd_uninstall_cron(args):
    existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if existing.returncode != 0:
        print("No crontab found.")
        return
    lines = [line for line in existing.stdout.splitlines() if CRON_MARKER not in line]
    subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True)
    print("Cron job removed (if it existed).")


def main():
    parser = argparse.ArgumentParser(description="MikroTik router backup tool")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run", help="Back up all configured routers once, right now")

    svc = sub.add_parser("service", help="Windows service control")
    svc.add_argument("action", choices=["install", "start", "stop", "remove"])

    cron = sub.add_parser("install-cron", help="Install a daily cron job (Linux/macOS)")
    cron.add_argument("--time", default="02:00", help="Daily run time, HH:MM 24h (default 02:00)")

    sub.add_parser("uninstall-cron", help="Remove the cron job installed by install-cron")

    args = parser.parse_args()

    {
        "run": cmd_run,
        "service": cmd_service,
        "install-cron": cmd_install_cron,
        "uninstall-cron": cmd_uninstall_cron,
    }[args.command](args)


if __name__ == "__main__":
    main()
