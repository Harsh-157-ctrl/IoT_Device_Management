# Secure IoT Hub & Web Controller

This project is a real-time, bi-directional IoT device management system. It features a secure TCP server utilizing SSL/TLS encryption for communication with remote hardware clients, coupled with a Flask-based web dashboard for centralized monitoring and command execution.

## 🚀 Key Features

* **Secure Socket Communication:** All TCP traffic between the controller and edge devices is encrypted using self-signed SSL/TLS certificates.
* **Bi-Directional Messaging:** Devices send continuous heartbeat/status updates, while the server pushes mechanical execution commands asynchronously.
* **Latency Tracking:** The server calculates the exact round-trip execution latency by tracking command dispatch times against client acknowledgment (`ACK`) receipts.
* **Threaded Client Architecture:** Clients utilize Python `threading` and locks (`threading.Lock`) to handle mechanical execution delays (e.g., 10-second simulations) without blocking the socket listener.
* **RESTful Web Dashboard:** A Flask frontend provides a real-time, auto-polling UI to monitor device health and dispatch commands to individual devices or broadcast to all.

## 📂 Project Structure

```text
.
├── web_controller1.py    # Main Flask Web Server & Background Secure TCP Server
├── client_new.py         # Simulated IoT Edge Device Client
├── make_certs.py         # Script to generate RSA Keys and X.509 Certificates
├── cert.pem              # Public Certificate (Generated)
├── key.pem               # Private RSA Key (Generated)
├── requirements.txt      # Python dependencies
└── templates/
    └── index.html        # Frontend UI for the Flask Dashboard