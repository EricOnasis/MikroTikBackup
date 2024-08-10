import paramiko
import time
import os
import socket

# Global timeout settings (in seconds)
CONNECTION_TIMEOUT = 10


def create_backup(client: paramiko.SSHClient, backup_name: str) -> None:
    """Create backup"""
    print(f"Creating backup: {backup_name}...")
    stdin, stdout, stderr = client.exec_command(f"/system backup save name={backup_name}")
    
    # Wait for exit status
    stdout.channel.recv_exit_status()
    print(f"Configuration backup saved as {backup_name}.")

def transfer_backup(client: paramiko.SSHClient, backup_name: str, local_path: str) -> bool:
    """Download the backup local using SFTP."""
    print(f"Downloading backup: {backup_name} to {local_path}...")
    
    # File path on MikroTik
    remote_path = f"/{backup_name}"
    local_file_path = os.path.join(local_path, backup_name)
    
    try:
        # Wait 10 seconds for backup to be available
        time.sleep(10)

        # Debug output
        print(f"Attempting to transfer{backup_name} from {remote_path} to {local_file_path}")
        with client.open_sftp() as sftp:
            sftp.get(remote_path, local_file_path)
        print(f"{backup_name} transferred successfully to {local_file_path}")
        return True
    except FileNotFoundError:
        print(f"Error: Remote file {remote_path} not found.")
    except Exception as e:
        print(f"Error during file transfer: {e}")
    return False

def delete_backup(client: paramiko.SSHClient, backup_name: str) -> None:
    """Delete backup from MikroTik"""
    print(f"Deleting {backup_name} from the router...")
    stdin, stdout, stderr = client.exec_command(f"/file remove {backup_name}")
    stdout.channel.recv_exit_status()  # Wait for command to finish
    print(f"{backup_name} deleted from the router.")
    

def connect_to_router(host: str, port: int, username: str, password: str) -> paramiko.SSHClient:
    """Create and return SSH client connected to the router."""
    print(f"Connecting to {host}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Set the global socket timeout
        socket.setdefaulttimeout(CONNECTION_TIMEOUT)
        
        # Connect to the router
        client.connect(host, port=port, username=username, password=password)
        return client
    except (paramiko.ssh_exception.SSHException, socket.timeout, ConnectionError) as e:
        print(f"Connection error for {host}: {e}")
        return None

def main():
    # Router connection details
    routers = [
        {'host': '1.1.1.1', 'port': 22, 'username': 'admin', 'password': 'admin'}, # Name
        
        # Add routers here
    ]
    
    # Modify path accordingly
    local_backup_path = r"C:\MikroTikBackups"
    
    success = 0
    fails = 0
    
    for router in routers:
        host = router['host']
        port = router['port']
        username = router['username']
        password = router['password']
        
        client = None
        try:
            # Connect to the router
            client = connect_to_router(host, port, username, password)
            if client is None:
                fails += 1
                continue  # Skip to next router if connection failed
            
            print(f"SSH client created for {host}.")
            
            # Fetch router identity
            stdin, stdout, stderr = client.exec_command('/system identity print')
            router_identity = stdout.read().decode().strip().split('\n')[0].split(':')[1].strip()
            print(f"Router identity: {router_identity}")
            
            # Define backup name and paths
            backup_name = f"{router_identity}_{time.strftime('%d-%m-%Y')}.backup"
            
            # Create backup
            create_backup(client, backup_name)
            
            # Transfer backup
            if transfer_backup(client, backup_name, local_backup_path):
                # Delete backup if transfer was successful
                delete_backup(client, backup_name)
                success += 1
            
        
        except Exception as e:
            print(f"Error during operation for {host}: {e}")
        
        finally:
            if client:
                client.close()
                print(f"SSH client closed for {host}.")
    print(f"{success} routers were successfully backed up.")
    print(f"{fails} routers failed to be backed up.")

if __name__ == "__main__":
    main()
