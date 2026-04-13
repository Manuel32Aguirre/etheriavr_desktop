from flask import Flask, request, jsonify
from tessitura_model import predict

import socket
import threading
import time

app = Flask(__name__)

# ================== IA ==================
@app.route("/predict", methods=["POST"])
def predict_voice():
    data = request.json

    features = [
        data["min"],
        data["max"],
        data["avg"],
        data["range"],
        data["stability"]
    ]

    result = predict(features)

    return jsonify({"voice": result})

# ================== DISCOVERY ==================
def broadcast_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    message = b"AI_SERVER:5000"

    while True:
        try:
            s.sendto(message, ('255.255.255.255', 5051))
            time.sleep(1)
        except Exception as e:
            print("Broadcast error:", e)

# ================== MAIN ==================
if __name__ == "__main__":
    # iniciar broadcast en segundo plano
    threading.Thread(target=broadcast_server, daemon=True).start()

    # iniciar servidor Flask
    app.run(host="0.0.0.0", port=5000)