"""Windows service wrapper around mikrotik_backup_lib. Windows-only (needs pywin32).

Normally driven via `python mikrotik_backup.py service install|start|stop|remove`,
but can also be run directly (`python windows_service.py install`) if needed.
"""
import logging
import os
import time

import win32event
import win32service
import win32serviceutil

from mikrotik_backup_lib import load_config, run_backups

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
RUN_INTERVAL_SECONDS = 86400  # once per day


class MikroTikBackupService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MikroTikBackupService"
    _svc_display_name_ = "MikroTik Backup Service"
    _svc_description_ = "Service to automate backups of MikroTik routers"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

        os.makedirs(LOG_DIR, exist_ok=True)
        log_file = os.path.join(LOG_DIR, time.strftime("%d-%m-%Y") + ".log")
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("MikroTikBackupService")

    def SvcStop(self):
        self.logger.info("Stopping service...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        self.logger.info("Service started.")
        self.main()

    def main(self):
        while self.running:
            if not os.path.exists(CONFIG_PATH):
                self.logger.error(
                    f"Config file not found at {CONFIG_PATH}. "
                    "Copy config.example.json to config.json and fill in your router details."
                )
            else:
                try:
                    # Reloaded every cycle so router list changes don't require a service restart.
                    config = load_config(CONFIG_PATH)
                    run_backups(config, self.logger)
                except Exception as e:
                    self.logger.error(f"Backup run failed: {e}")

            # Wake up early if the service is asked to stop, otherwise wait a full day.
            rc = win32event.WaitForSingleObject(self.hWaitStop, RUN_INTERVAL_SECONDS * 1000)
            if rc == win32event.WAIT_OBJECT_0:
                break


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(MikroTikBackupService)
