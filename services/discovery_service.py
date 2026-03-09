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
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', self.port))  # ← Escuchar en TODAS las interfaces
            
            # Mostrar todas las IPs disponibles
            hostname = socket.gethostname()
            try:
                addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET)
                local_ips = [ip[4][0] for ip in addr_info if not ip[4][0].startswith('127.')]
                print(f"[*] Escuchando en todas las interfaces:")
                for ip in local_ips:
                    print(f"    - {ip}")
            except Exception as e:
                print(f"[!] No se pudieron listar las IPs: {e}")
            
            while True:
                data, addr = s.recvfrom(1024)
                message = data.decode('utf-8')
                if message == self.secret:
                    print(f"[OK] ¡Quest 3 detectado en la IP: {addr[0]}!")
                    return addr[0]