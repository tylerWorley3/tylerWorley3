import paramiko
import sqlite3
import os



def ssh_command(ip, command):
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Connect to the server
    ssh.connect(ip, username='root', password='password')  

    # Execute the command
    stdin, stdout, stderr = ssh.exec_command(command)
    print(stdout.read().decode())  # Output the result of the command

    # Close the connection
    ssh.close()

def read_hp_settings(db_path):
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Read all data from the hp_setting table
    cursor.execute("SELECT * FROM hp_setting")
    settings_data = cursor.fetchall()
    
    # Store column names
    columns = [description[0] for description in cursor.description]
    
    # Close the connection
    cursor.close()
    conn.close()
    
    return settings_data, columns

def main():
    # IPs of the HMIs
    HMIs = ["192.168.1.201", "192.168.1.202"]

    # Commands to be executed
    stop_services = "systemctl stop vthp-backend crank-ui"
    remove_files = "rm /usr/local/bin/backend/*.db"
    restart_service = "systemctl restart vthp-backend"

    for HMI in HMIs:
        print(f"Stopping services on {HMI}")
        ssh_command(HMI, stop_services)
        
        print(f"Removing database files on {HMI}")
        ssh_command(HMI, remove_files)

        print(f"Restarting services on {HMI}")
        ssh_command(HMI, restart_service)

if __name__ == "__main__":
    main()
