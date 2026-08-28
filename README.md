# MikroTikBackup

This repository contains two Python scripts for automating the backup process of MikroTik routers:

    MikroTikBackupAsService: A Windows service that automates daily backups.
    MikroTikBackupAsScript: A standalone script that can be executed manually to back up multiple MikroTik routers.

Both share the same backup logic in `mikrotik_backup_lib.py` and read router details/settings
from a `config.json` file (never committed — see Configuration below).

### Prerequisites

Before using these scripts, ensure the following software is installed on your system:

    Python 3.x: Download Python
    Paramiko: For SSH connections.
    PyWin32: Required for creating and managing the Windows service.

### Installing Python

    Download and install Python 3.x from the official Python website.
    Ensure that Python is added to your system's PATH during the installation process.

### Installing Required Python Packages

After installing Python, you need to install the required Python packages using pip:

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
        "backup_password": null
      }
    }

Settings:

    connect_retries / retry_delay: retry SSH connection this many times before giving up on a router.
    backup_ready_timeout: how long to poll the router for the backup file before failing the transfer
        (replaces a fixed blind wait).
    retention_days: local backups older than this are deleted automatically. Set to 0 to keep forever.
    backup_password: if set, backups are saved password-protected (`/system backup save password=...`).

# MikroTikBackupAsService

## Overview

The MikroTikBackupAsService script is designed to run as a Windows service, performing daily backups of MikroTik routers, deleting them from the router and storing them locally.

### Installing the Service

Clone this repository to your local machine:


    git clone https://github.com/ericonasis/MikroTikBackup.git
    cd MikroTikBackup

Set up `config.json` as described above (place it next to the scripts).

Install the service by running the following command in the terminal:


    python MikroTikBackupAsService.py install

### Start the service:

    python MikroTikBackupAsService.py start

### Managing the Service

You can manually stop, start, or uninstall the service using these commands:

    Stop the service: python MikroTikBackupAsService.py stop
    Uninstall the service: python MikroTikBackupAsService.py remove

### Log Files

The service creates daily log files in a `logs` directory next to the script. The logs provide detailed information about the backup process.


# MikroTikBackupAsScript

## Overview
The MikroTikBackupAsScript script is a standalone Python script that you can run manually to back up multiple MikroTik routers.

### Running the Script

Set up `config.json` as described above (place it next to the script).

Run the script using Python:

    python MikroTikBackupAsScript.py

The script will connect to each router, create a backup, transfer it to the local machine, and delete the backup from the router.

### Contributing

Contributions are welcome! Please fork this repository and submit a pull request with your changes.