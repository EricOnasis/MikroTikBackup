"""Shared logic for backing up MikroTik routers over SSH/SFTP.

Used by both MikroTikBackupAsScript.py (manual run) and
MikroTikBackupAsService.py (Windows service).
"""
import json
import os
import re
import socket
import time

import paramiko

DEFAULT_CONNECTION_TIMEOUT = 10
DEFAULT_CONNECT_RETRIES = 3
DEFAULT_RETRY_DELAY = 5
DEFAULT_BACKUP_READY_TIMEOUT = 60
DEFAULT_RETENTION_DAYS = 0  # 0 = keep forever

IDENTITY_RE = re.compile(r"name:\s*(\S+)")


def load_config(config_path: str) -> dict:
    """Load router list and settings from a JSON config file."""
    with open(config_path, "r") as f:
        config = json.load(f)

    if not config.get("routers"):
        raise ValueError(f"No routers defined in {config_path}")

    settings = config.setdefault("settings", {})
    settings.setdefault("connection_timeout", DEFAULT_CONNECTION_TIMEOUT)
    settings.setdefault("connect_retries", DEFAULT_CONNECT_RETRIES)
    settings.setdefault("retry_delay", DEFAULT_RETRY_DELAY)
    settings.setdefault("backup_ready_timeout", DEFAULT_BACKUP_READY_TIMEOUT)
    settings.setdefault("retention_days", DEFAULT_RETENTION_DAYS)
    settings.setdefault("backup_password", None)

    return config


def connect_to_router(host: str, port: int, username: str, password: str,
                       logger, timeout: int = DEFAULT_CONNECTION_TIMEOUT,
                       retries: int = DEFAULT_CONNECT_RETRIES,
                       retry_delay: int = DEFAULT_RETRY_DELAY):
    """Create and return an SSH client connected to the router, retrying on failure."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Connecting to {host} (attempt {attempt}/{retries})...")
            client.connect(host, port=port, username=username, password=password,
                            timeout=timeout)
            return client
        except (paramiko.ssh_exception.SSHException, socket.timeout,
                socket.error, ConnectionError) as e:
            last_error = e
            logger.warning(f"Connection attempt {attempt} to {host} failed: {e}")
            if attempt < retries:
                time.sleep(retry_delay)

    logger.error(f"Giving up connecting to {host} after {retries} attempts: {last_error}")
    return None


def get_router_identity(client: paramiko.SSHClient, fallback: str) -> str:
    """Fetch the router's configured identity name, falling back to the host on failure."""
    try:
        stdin, stdout, stderr = client.exec_command("/system identity print")
        output = stdout.read().decode(errors="replace")
        match = IDENTITY_RE.search(output)
        if match:
            return match.group(1)
    except Exception:
        pass
    return fallback


def create_backup(client: paramiko.SSHClient, backup_name: str, logger,
                   password: str = None) -> None:
    """Trigger a backup save on the router."""
    logger.info(f"Creating backup: {backup_name}...")
    command = f"/system backup save name={backup_name}"
    if password:
        command += f" password={password}"
    stdin, stdout, stderr = client.exec_command(command)
    stdout.channel.recv_exit_status()
    logger.info(f"Configuration backup saved as {backup_name}.")


def wait_for_backup(client: paramiko.SSHClient, remote_path: str, logger,
                     timeout: int = DEFAULT_BACKUP_READY_TIMEOUT,
                     poll_interval: int = 2) -> bool:
    """Poll via SFTP until the backup file exists on the router, instead of a blind sleep."""
    deadline = time.time() + timeout
    with client.open_sftp() as sftp:
        while time.time() < deadline:
            try:
                sftp.stat(remote_path)
                return True
            except FileNotFoundError:
                time.sleep(poll_interval)
    logger.error(f"Timed out after {timeout}s waiting for {remote_path} to appear.")
    return False


def transfer_backup(client: paramiko.SSHClient, backup_name: str, local_path: str,
                     logger, ready_timeout: int = DEFAULT_BACKUP_READY_TIMEOUT) -> bool:
    """Download the backup from the router via SFTP, once it's confirmed ready."""
    remote_path = f"/{backup_name}"
    local_file_path = os.path.join(local_path, backup_name)

    if not wait_for_backup(client, remote_path, logger, timeout=ready_timeout):
        return False

    try:
        logger.info(f"Downloading backup: {backup_name} to {local_file_path}...")
        with client.open_sftp() as sftp:
            sftp.get(remote_path, local_file_path)
        logger.info(f"{backup_name} transferred successfully to {local_file_path}")
        return True
    except FileNotFoundError:
        logger.error(f"Error: Remote file {remote_path} not found.")
    except Exception as e:
        logger.error(f"Error during file transfer: {e}")
    return False


def delete_backup(client: paramiko.SSHClient, backup_name: str, logger) -> None:
    """Delete the backup file from the router."""
    logger.info(f"Deleting {backup_name} from the router...")
    stdin, stdout, stderr = client.exec_command(f"/file remove {backup_name}")
    stdout.channel.recv_exit_status()
    logger.info(f"{backup_name} deleted from the router.")


def cleanup_old_backups(local_path: str, retention_days: int, logger) -> None:
    """Delete local backup files older than retention_days. No-op if retention_days <= 0."""
    if retention_days <= 0 or not os.path.isdir(local_path):
        return

    cutoff = time.time() - (retention_days * 86400)
    for filename in os.listdir(local_path):
        if not filename.endswith(".backup"):
            continue
        file_path = os.path.join(local_path, filename)
        try:
            if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff:
                os.remove(file_path)
                logger.info(f"Removed old local backup: {file_path}")
        except OSError as e:
            logger.warning(f"Could not remove old backup {file_path}: {e}")


def backup_router(router: dict, settings: dict, logger) -> bool:
    """Run the full backup flow for a single router. Returns True on success."""
    host = router["host"]
    port = router.get("port", 22)
    username = router["username"]
    password = router["password"]

    client = None
    try:
        client = connect_to_router(
            host, port, username, password, logger,
            timeout=settings["connection_timeout"],
            retries=settings["connect_retries"],
            retry_delay=settings["retry_delay"],
        )
        if client is None:
            return False

        router_identity = get_router_identity(client, fallback=router.get("name", host))
        backup_name = f"{router_identity}_{time.strftime('%d-%m-%Y')}.backup"

        create_backup(client, backup_name, logger, password=settings.get("backup_password"))

        if transfer_backup(client, backup_name, settings["local_backup_path"], logger,
                            ready_timeout=settings["backup_ready_timeout"]):
            delete_backup(client, backup_name, logger)
            return True
        return False

    except Exception as e:
        logger.error(f"Error during operation for {host}: {e}")
        return False

    finally:
        if client:
            client.close()
            logger.info(f"SSH client closed for {host}.")


def run_backups(config: dict, logger) -> tuple:
    """Back up every router in config. Returns (success_count, fail_count)."""
    settings = config["settings"]
    os.makedirs(settings["local_backup_path"], exist_ok=True)

    success = 0
    fails = 0
    for router in config["routers"]:
        if backup_router(router, settings, logger):
            success += 1
        else:
            fails += 1

    cleanup_old_backups(settings["local_backup_path"], settings["retention_days"], logger)

    logger.info(f"{success} routers were successfully backed up.")
    logger.info(f"{fails} routers failed to be backed up.")
    return success, fails
