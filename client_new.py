import socket
import threading
import json
import time
import ssl

HOST = '10.118.172.30'
PORT = 65432
DEVICE_ID = "Sensor_Remote_2" 

# Traffic cop to prevent socket corruption when multiple threads send data
send_lock = threading.Lock() 

def send_status_updates(conn):
    """Thread 1: Sends automatic status updates every 5 seconds."""
    while True:
        try:
            msg = json.dumps({
                "type": "status",
                "device_id": DEVICE_ID,
                "data": "Online. Temp: 22C, Motor: Active"
            }) + "\n"
            
            with send_lock: # Wait for green light to send
                conn.sendall(msg.encode('utf-8'))
            time.sleep(5)
        except Exception:
            break

def execute_and_ack(conn, cmd_data):
    """Simulates the physical execution of a command with a 10-second delay."""
    action = cmd_data['action']
    cmd_id = cmd_data['command_id']
    
    print(f"\n[+] SERVER COMMAND RECEIVED: '{action}'")
    print(f"    -> Simulating mechanical execution (Waiting 10 seconds)...")
    
    # --- THE 10 SECOND DELAY ---
    time.sleep(10) 
    
    ack = json.dumps({
        "type": "ack",
        "command_id": cmd_id,
        "device_id": DEVICE_ID
    }) + "\n"
    
    try:
        with send_lock: # Wait for green light to send ACK
            conn.sendall(ack.encode('utf-8'))
        print(f"[-] Execution Complete. Acknowledgment sent for command {cmd_id}")
    except Exception as e:
        print(f"Failed to send ack: {e}")

def listen_for_server_commands(secure_client):
    """Thread 2: Constantly listens for commands FROM the server."""
    while True:
        try:
            data = secure_client.recv(1024)
            if not data: break
            
            messages = data.decode('utf-8').strip().split('\n')
            for msg in messages:
                if not msg: continue
                parsed = json.loads(msg)
                
                if parsed.get('type') == 'command':
                    cmd_data = json.loads(parsed['payload'])
                    # Pass the command to a new thread so we don't freeze our listener!
                    threading.Thread(target=execute_and_ack, args=(secure_client, cmd_data), daemon=True).start()
                    
        except Exception as e:
            print(f"\n[!] Listening stopped: {e}")
            break

def main():
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    secure_client = context.wrap_socket(client, server_hostname=HOST)
    
    try:
        print(f"Attempting to connect to Controller at {HOST}:{PORT}...")
        secure_client.connect((HOST, PORT))
        print(f"{DEVICE_ID} Connected Securely to Controller!")
        
        # Start background tasks
        threading.Thread(target=send_status_updates, args=(secure_client,), daemon=True).start()
        threading.Thread(target=listen_for_server_commands, args=(secure_client,), daemon=True).start()

        # Thread 3 (Main): Wait for YOU to type a command to send to the server
        while True:
            time.sleep(0.5)
            client_cmd = input("\nEnter emergency command to send TO server (or 'exit'): ")
            if client_cmd.lower() == 'exit':
                break
            
            msg = json.dumps({
                "type": "client_command",
                "device_id": DEVICE_ID,
                "action": client_cmd
            }) + "\n"
            
            with send_lock: # Wait for green light to send
                secure_client.sendall(msg.encode('utf-8'))
            print(f"Sent command '{client_cmd}' to server.")

    except Exception as e:
        print(f"Connection failed: {e}")
    finally:
        secure_client.close()

if __name__ == "__main__":
    main()