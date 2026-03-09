import mido
import socket
import time
import os
import struct
import threading
from dotenv import load_dotenv

load_dotenv()

class MidiManager:
    def __init__(self, quest_ip, port=None, status_port=None):
        self.quest_ip = quest_ip
        self.port = port or int(os.getenv("UDP_PORT"))
        self.status_port = status_port or int(os.getenv("UDP_STATUS_PORT", "12346"))
        
        # Socket para notas MIDI (ya existente)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        
        # Socket para heartbeat de estado MIDI
        self.status_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        self.packet_count = 0 
        self.start_time = time.perf_counter()
        
        # Pre-calcular destinos
        self.dest = (self.quest_ip, self.port)
        self.status_dest = (self.quest_ip, self.status_port)
        
        # Formato binario: tipo(1B) + nota(1B) + vel(1B) + pad(1B) + id(4B) + time(4f) = 12 bytes
        self.struct_format = 'BBBBIf'
        
        # Control para el heartbeat
        self.heartbeat_counter = 0

    def send_status_heartbeat(self):
        """Envía el estado de conexión MIDI cada 2 segundos"""
        print(f"[*] Thread de heartbeat iniciado en puerto {self.status_port}")
        
        while True:
            try:
                # Detectar si hay dispositivo MIDI conectado
                inputs = mido.get_input_names()
                is_connected = len(inputs) > 0
                
                # tipo 3 = conectado, tipo 4 = desconectado
                msg_type = 3 if is_connected else 4
                t_rel = time.perf_counter() - self.start_time
                
                payload = struct.pack(self.struct_format, 
                                    msg_type,  # 3 o 4
                                    0, 0, 0,   # padding
                                    self.heartbeat_counter,
                                    t_rel)
                
                self.status_sock.sendto(payload, self.status_dest)
                self.heartbeat_counter += 1
                
                # Log cada 10 heartbeats (cada 20 segundos) para no saturar
                if self.heartbeat_counter % 10 == 0:
                    status_text = "✅ CONECTADO" if is_connected else "❌ DESCONECTADO"
                    print(f"[HEARTBEAT] MIDI: {status_text} | Enviado: {self.heartbeat_counter}")
                
            except Exception as e:
                print(f"[!] Error en heartbeat: {e}")
            
            time.sleep(2)  # Enviar cada 2 segundos

    def start_listening(self):
        # Iniciar thread de heartbeat en segundo plano
        heartbeat_thread = threading.Thread(target=self.send_status_heartbeat, daemon=True)
        heartbeat_thread.start()
        print(f"[*] Heartbeat iniciado -> {self.quest_ip}:{self.status_port}")
        
        # Código original de detección MIDI
        inputs = mido.get_input_names()
        if not inputs:
            print("[!] ERROR: No se encontró ningún dispositivo MIDI. ¡Conecta el teclado!")
            # Aunque no haya MIDI, el heartbeat sigue corriendo en segundo plano
            print("[*] El heartbeat seguirá enviando estado 'DESCONECTADO'...")
            # Mantener el programa vivo para que el heartbeat siga
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print(f"\n[!] Deteniendo servicio MIDI...")
            return

        device_name = inputs[0]
        print(f"[*] Dispositivo MIDI vinculado: {device_name}")
        print(f"[*] Destino UDP (notas): {self.quest_ip}:{self.port}")
        print("-" * 60)

        try:
            with mido.open_input(device_name) as port:
                print(f"{time.strftime('%H:%M:%S')} INFO - EtheriaVR está listo!")
                print(f"[*] Modo: Datos binarios optimizados (12 bytes/paquete)")
                
                for msg in port:
                    self.packet_count += 1
                    t_rel = time.perf_counter() - self.start_time 

                    # --- Lógica de Notas (Formato Binario Optimizado) ---
                    if msg.type in ['note_on', 'note_off']:
                        msg_type = 1 if msg.type == 'note_on' else 0
                        
                        payload = struct.pack(self.struct_format, 
                                            msg_type, 
                                            msg.note, 
                                            msg.velocity, 
                                            0,  # padding
                                            self.packet_count,
                                            t_rel)
                        self.sock.sendto(payload, self.dest)
                        
                        status = "KEY_DOWN" if msg_type == 1 else "KEY_UP"
                        print(f"{time.strftime('%H:%M:%S')} DEBUG - {status} -> Nota: {msg.note} | ID: {self.packet_count}")

                    # --- Lógica del Pedal con Inversión de Polaridad (Binario) ---
                    elif msg.type == 'control_change' and msg.control == 64:
                        val_invertido = 127 - msg.value 
                        
                        payload = struct.pack(self.struct_format,
                                            2,  # tipo CC
                                            64,  # control number
                                            val_invertido,
                                            0,  # padding
                                            self.packet_count,
                                            t_rel)
                        self.sock.sendto(payload, self.dest)
                        
                        status = "ON" if val_invertido >= 64 else "OFF"
                        print(f"{time.strftime('%H:%M:%S')} DEBUG - PEDAL -> {status} (Invertido)")

        except KeyboardInterrupt:
            print(f"\n[!] Deteniendo flujo MIDI...")
        finally:
            self.sock.close()
            self.status_sock.close()