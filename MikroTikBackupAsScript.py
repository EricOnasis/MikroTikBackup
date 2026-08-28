"""Standalone script: back up every router listed in config.json, once."""
import logging
import os
import sys

from mikrotik_backup_lib import load_config, run_backups

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    logger = logging.getLogger("MikroTikBackup")

    if not os.path.exists(CONFIG_PATH):
        logger.error(
            f"Config file not found at {CONFIG_PATH}. "
            "Copy config.example.json to config.json and fill in your router details."
        )
        sys.exit(1)

    config = load_config(CONFIG_PATH)
    run_backups(config, logger)


if __name__ == "__main__":
    main()
