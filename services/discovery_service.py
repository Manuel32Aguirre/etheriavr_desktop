import socket
import os
from dotenv import load_dotenv

load_dotenv()

class DiscoveryService:
    def __init__(self, port=None, secret=None):
        self.port = port or int(os.getenv("DISCOVERY_PORT"))
        self.secret = secret or os.getenv("DISCOVERY_SECRET")
        
        if not self.secret:
            raise ValueError(
                "⚠️  DISCOVERY_SECRET no está configurado.\n"
                "   Copia .env.example a .env y configura tu secret personalizado."
            )

    def find_quest_ip(self):
        print(f"[*] Escuchando señales de EtheriaVR en el puerto {self.port}...")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(('', self.port))
            while True:
                data, addr = s.recvfrom(1024)
                message = data.decode('utf-8')
                if message == self.secret:
                    print(f"[OK] ¡Quest 3 detectado en la IP: {addr[0]}!")
                    return addr[0]