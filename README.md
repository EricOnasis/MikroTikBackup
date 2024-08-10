### MikroTikBackup

This repository contains two Python scripts for automating the backup process of MikroTik routers:

    MikroTikBackupAsService: A Windows service that automates daily backups.
    MikroTikBackupAsScript: A standalone script that can be executed manually to back up multiple MikroTik routers.

# Prerequisites

Before using these scripts, ensure the following software is installed on your system:

    Python 3.x: Download Python
    Paramiko: For SSH connections.
    PyWin32: Required for creating and managing the Windows service.

# Installing Python

    Download and install Python 3.x from the official Python website.
    Ensure that Python is added to your system's PATH during the installation process.

# Installing Required Python Packages

After installing Python, you need to install the required Python packages using pip:

    pip install paramiko pywin32

## MikroTikBackupAsService

# Overview

The MikroTikBackupAsService script is designed to run as a Windows service, performing daily backups of MikroTik routers and storing them locally.

# Installing the Service

Clone this repository to your local machine:


    git clone https://github.com/ericonasis/MikroTikBackup.git
    cd MikroTikBackup

Modify the MikroTikBackupAsService script to include your router details and desired local backup path.

Install the service by running the following command in the terminal:


    python MikroTikBackupAsService.py install

# Start the service:

    python MikroTikBackupAsService.py start

# Managing the Service

You can manually stop, start, or uninstall the service using these commands:

    Stop the service: python MikroTikBackupAsService.py stop
    Uninstall the service: python MikroTikBackupAsService.py remove

# Log Files

The service creates log files in a designated log directory (e.g., G:\Onasis\PythonAutomation\Logs). The logs provide detailed information about the backup process.


## MikroTikBackupAsScript

# Overview
The MikroTikBackupAsScript script is a standalone Python script that you can run manually to back up multiple MikroTik routers.
Running the Script

Modify the MikroTikBackupAsScript script to include your router details and desired local backup path.

Run the script using Python:

    python MikroTikBackupAsScript.py

The script will connect to each router, create a backup, transfer it to the local machine, and delete the backup from the router.

# Contributing

Contributions are welcome! Please fork this repository and submit a pull request with your changes.