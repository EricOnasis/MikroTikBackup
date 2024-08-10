import paramiko
import time
import os
import socket
import win32serviceutil
import win32service
import win32event
import servicemanager
import logging

# Setup logging
log_path = r"G:\Onasis\PythonAutomation\Logs"
if not os.path.exists(log_path):
    os.makedirs(log_path)
log_file = os.path.join(log_path, time.strftime("%d-%m-%Y") + ".log")
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Global timeout settings (in seconds)
CONNECTION_TIMEOUT = 10

class MikroTikBackupService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MikroTikBackupService"
    _svc_display_name_ = "MikroTik Backup Service"
    _svc_description_ = "Service to automate backups of MikroTik routers"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcStop(self):
        logging.info("Stopping service...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        logging.info("Service started.")
        self.main()

    def create_backup(self, client: paramiko.SSHClient, backup_name: str) -> None:
        logging.info(f"Creating backup: {backup_name}...")
        stdin, stdout, stderr = client.exec_command(f"/system backup save name={backup_name}")
        stdout.channel.recv_exit_status()
        logging.info(f"Configuration backup saved as {backup_name}.")

    def transfer_backup(self, client: paramiko.SSHClient, backup_name: str, local_path: str) -> bool:
        logging.info(f"Downloading backup: {backup_name} to {local_path}...")
        remote_path = f"/{backup_name}"
        local_file_path = os.path.join(local_path, backup_name)
        
        try:
            time.sleep(10)
            logging.info(f"Attempting to use SFTP to transfer file from {remote_path} to {local_file_path}")
            with client.open_sftp() as sftp:
                sftp.get(remote_path, local_file_path)
            logging.info(f"Backup {backup_name} transferred successfully to {local_file_path}")
            return True
        except FileNotFoundError:
            logging.error(f"Error: Remote file {remote_path} not found.")
        except Exception as e:
            logging.error(f"Error during file transfer: {e}")
        return False

    def delete_backup(self, client: paramiko.SSHClient, backup_name: str) -> None:
        logging.info(f"Deleting backup: {backup_name} from the router...")
        stdin, stdout, stderr = client.exec_command(f"/file remove {backup_name}")
        stdout.channel.recv_exit_status()
        logging.info(f"Backup {backup_name} deleted from the router.")

    def connect_to_router(self, host: str, port: int, username: str, password: str) -> paramiko.SSHClient:
        logging.info(f"Connecting to {host}...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            socket.setdefaulttimeout(CONNECTION_TIMEOUT)
            client.connect(host, port=port, username=username, password=password)
            return client
        except (paramiko.ssh_exception.SSHException, socket.timeout, ConnectionError) as e:
            logging.error(f"Connection error for {host}: {e}")
            return None

    def main(self):
        routers = [
            {'host': '1.1.1.1', 'port': 22, 'username': 'admin', 'password': 'admin'}, # Name
            # Add routers here
        ]

        # Modify path accordingly
        local_backup_path = r"C:\MikroTikBackups"

        while self.running:
            for router in routers:
                host = router['host']
                port = router['port']
                username = router['username']
                password = router['password']

                client = None
                try:
                    client = self.connect_to_router(host, port, username, password)
                    if client is None:
                        continue

                    stdin, stdout, stderr = client.exec_command('/system identity print')
                    router_identity = stdout.read().decode().strip().split('\n')[0].split(':')[1].strip()

                    backup_name = f"{router_identity}_{time.strftime('%d-%m-%Y')}.backup"

                    self.create_backup(client, backup_name)

                    if self.transfer_backup(client, backup_name, local_backup_path):
                        self.delete_backup(client, backup_name)

                except Exception as e:
                    logging.error(f"Error during operation for {host}: {e}")

                finally:
                    if client:
                        client.close()
                        logging.info(f"SSH client closed for {host}.")

            time.sleep(86400)  # Run once per day

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(MikroTikBackupService)
