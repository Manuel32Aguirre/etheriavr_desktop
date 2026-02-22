import mido
import socket
import time
import os
from dotenv import load_dotenv

load_dotenv()

class MidiManager:
    def __init__(self, quest_ip, port=None):
        self.quest_ip = quest_ip
        self.port = port or int(os.getenv("UDP_PORT"))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.packet_count = 0 
        self.start_time = time.perf_counter() 

    def start_listening(self):
        inputs = mido.get_input_names()
        if not inputs:
            print("[!] ERROR: No se encontró ningún dispositivo MIDI. ¡Conecta el teclado, Víctor!")
            return

        device_name = inputs[0]
        print(f"[*] Dispositivo MIDI vinculado: {device_name}")
        print(f"[*] Destino UDP: {self.quest_ip}:{self.port}")
        print("-" * 60)

        try:
            with mido.open_input(device_name) as port:
                print(f"{time.strftime('%H:%M:%S')} INFO - EtheriaVR está listo!")
                
                for msg in port:
                    self.packet_count += 1
                    # Tiempo transcurrido desde que arrancó el script (en segundos con decimales)
                    t_rel = time.perf_counter() - self.start_time 

                    # --- Lógica de Notas (Tu estructura + Tiempo Relativo) ---
                    if msg.type in ['note_on', 'note_off']:
                        # Protocolo: note|tipo|nota|vel|id|timestamp_relativo
                        payload = f"note|{msg.type}|{msg.note}|{msg.velocity}|{self.packet_count}|{t_rel:.4f}"
                        self.sock.sendto(payload.encode('utf-8'), (self.quest_ip, self.port))
                        
                        # Tus logs originales que tanto te sirven
                        status = "KEY_DOWN" if msg.type == 'note_on' else "KEY_UP"
                        print(f"{time.strftime('%H:%M:%S')} DEBUG - {status} -> Nota: {msg.note} | ID: {self.packet_count}")

                    # --- Lógica del Pedal (Sustain CC 64) ---
                    # --- Lógica del Pedal con Inversión de Polaridad ---
                    elif msg.type == 'control_change' and msg.control == 64:
                        # Invertimos el valor: 127 - valor_recibido
                        # Si recibes 0 (pisado en tu caso), mandamos 127 (ON)
                        val_invertido = 127 - msg.value 
                        
                        payload = f"cc|64|{val_invertido}|0|{self.packet_count}|{t_rel:.4f}"
                        self.sock.sendto(payload.encode('utf-8'), (self.quest_ip, self.port))
                        
                        status = "ON" if val_invertido >= 64 else "OFF"
                        print(f"{time.strftime('%H:%M:%S')} DEBUG - PEDAL -> {status} (Invertido)")

        except KeyboardInterrupt:
            print(f"\n[!] Deteniendo flujo MIDI...")
        finally:
            self.sock.close()