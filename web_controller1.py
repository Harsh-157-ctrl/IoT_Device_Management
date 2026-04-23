from flask import Flask, render_template, request, jsonify
import socket
import threading
import json
import time
import ssl
import os

app = Flask(__name__)

# --- TCP Server Configuration ---
TCP_HOST = '0.0.0.0'
TCP_PORT = 65432

devices = {}          # Holds the actual socket connections
device_statuses = {}  # Holds the latest status strings for the website to read
pending_commands = {} # ---> FIXED: Re-added to track Latency! <---
command_counter = 1

# --- Web Routes (HTTP) ---

@app.route('/')
def index():
    """Serves the main dashboard webpage."""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """The webpage will constantly ask this URL for the latest device statuses."""
    return jsonify(device_statuses)

@app.route('/api/command', methods=['POST'])
def send_command():
    """The webpage sends commands here, and we forward them to the TCP sockets."""
    global command_counter
    data = request.json
    target = data.get('target')
    action = data.get('action')

    if not action:
        return jsonify({"error": "No action provided"}), 400

    payload_str = json.dumps({"command_id": command_counter, "action": action})
    message = json.dumps({"type": "command", "payload": payload_str}) + "\n"

    try:
        if target == 'all':
            for d_id, conn in list(devices.items()):
                pending_commands[command_counter] = time.time() # Start Latency Timer
                conn.sendall(message.encode('utf-8'))
        elif target in devices:
            pending_commands[command_counter] = time.time() # Start Latency Timer
            devices[target].sendall(message.encode('utf-8'))
        else:
            return jsonify({"error": "Device not found"}), 404
        
        command_counter += 1
        return jsonify({"success": f"Command '{action}' sent to {target}."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- TCP Background Server ---

def handle_device(conn, addr):
    device_id = None
    try:
        while True:
            data = conn.recv(1024)
            if not data: break
            
            messages = data.decode('utf-8').strip().split('\n')
            for msg in messages:
                if not msg: continue
                
                try:
                    parsed = json.loads(msg)
                    
                    if parsed['type'] == 'status':
                        if device_id is None:
                            device_id = parsed['device_id']
                            devices[device_id] = conn
                            print(f"\n[+] Connected: {device_id} from {addr}")
                        
                        # Update the global dictionary so the website can see it
                        device_statuses[device_id] = {
                            "status": parsed['data'],
                            "last_seen": time.strftime('%H:%M:%S')
                        }
                    
                    # ---> FIXED: Latency calculation added back! <---
                    elif parsed['type'] == 'ack':
                        cmd_id = parsed['command_id']
                        if cmd_id in pending_commands:
                            latency = time.time() - pending_commands[cmd_id]
                            print(f"\n[Ack] Command {cmd_id} executed by {device_id}. Latency: {latency:.4f}s")
                            del pending_commands[cmd_id]
                    
                    # ---> FIXED: Catching commands sent FROM the client! <---
                    elif parsed['type'] == 'client_command':
                        action = parsed['action']
                        print(f"\n[!] ALERT: Remote device '{device_id}' sent a command to the server: '{action}'")

                except json.JSONDecodeError:
                    pass
    except Exception as e:
        pass
    finally:
        if device_id and device_id in devices:
            del devices[device_id]
            if device_id in device_statuses:
                del device_statuses[device_id]
            print(f"\n[-] {device_id} disconnected.")
        conn.close()

def start_tcp_server():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cert_path = os.path.join(current_dir, "cert.pem")
    key_path = os.path.join(current_dir, "key.pem")

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_path, keyfile=key_path)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Prevents "Port in use" errors
    server.bind((TCP_HOST, TCP_PORT))
    server.listen()
    secure_server = context.wrap_socket(server, server_side=True)
    
    print(f"[*] Secure TCP Server running on port {TCP_PORT}")

    while True:
        conn, addr = secure_server.accept()
        threading.Thread(target=handle_device, args=(conn, addr), daemon=True).start()

if __name__ == '__main__':
    # 1. Start the TCP server in the background
    threading.Thread(target=start_tcp_server, daemon=True).start()
    
    # 2. Start the Web server in the foreground (Port 5000)
    print("\n" + "="*50)
    print("🌐 WEB DASHBOARD IS LIVE!")
    print("👉 Open your browser and go to: http://127.0.0.1:5000")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=5000)