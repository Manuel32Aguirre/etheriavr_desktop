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
        
        # Socket para notas MIDI
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        # Socket para heartbeat de estado MIDI
        self.status_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.status_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        
        self.packet_count = 0 
        self.start_time = time.perf_counter()
        
        # Pre-calcular destinos
        self.dest = (self.quest_ip, self.port)
        self.status_dest = (self.quest_ip, self.status_port)
        
        # Formato binario: tipo(1B) + nota(1B) + vel(1B) + pad(1B) + id(4B) + time(4f) = 12 bytes
        self.struct_format = 'BBBBIf'
        
        # Control para el heartbeat
        self.heartbeat_counter = 0
        
        self.running = False

    def midi_input_thread(self, device_name):
        """Thread que lee MIDI BLOQUEANTE y envía directamente (latencia mínima)"""
        try:
            with mido.open_input(device_name) as port:
                for msg in port:  # ← BLOQUEANTE: espera eventos sin overhead
                    if not self.running:
                        break
                    
                    # Enviar INMEDIATAMENTE sin pasar por queue
                    if msg.type in ['note_on', 'note_off']:
                        msg_type = 1 if msg.type == 'note_on' else 0
                        self.send_midi_event(msg_type, msg.note, msg.velocity, 0)
                    
                    elif msg.type == 'control_change' and msg.control == 64:
                        val_invertido = 127 - msg.value
                        self.send_midi_event(2, 64, val_invertido, 0)
        
        except Exception as e:
            print(f"[!] Error en thread MIDI: {e}")
    
    def send_status_heartbeat(self):
        """Envía el estado de conexión MIDI cada 2 segundos"""
        print(f"[*] Heartbeat MIDI iniciado -> {self.quest_ip}:{self.status_port}")
        
        while self.running:
            try:
                inputs = mido.get_input_names()
                is_connected = len(inputs) > 0
                
                msg_type = 3 if is_connected else 4
                t_rel = time.perf_counter() - self.start_time
                
                payload = struct.pack(self.struct_format, 
                                    msg_type,
                                    0, 0, 0,
                                    self.heartbeat_counter,
                                    t_rel)
                
                self.status_sock.sendto(payload, self.status_dest)
                self.heartbeat_counter += 1
                
                if self.heartbeat_counter % 10 == 0:
                    status_text = "✅ CONECTADO" if is_connected else "❌ DESCONECTADO"
                    print(f"[HEARTBEAT] MIDI {status_text} | Pkt: {self.heartbeat_counter}")
                
            except Exception as e:
                print(f"[!] Error heartbeat: {e}")
            
            time.sleep(2)
    
    def send_midi_event(self, msg_type, note=0, velocity=0, param=0):
        """Envía evento MIDI inmediatamente (cada nota hacia Unity)"""
        now = time.perf_counter()
        self.packet_count += 1
        t_rel = now - self.start_time
        
        payload = struct.pack(self.struct_format, 
                            msg_type, 
                            note, 
                            velocity, 
                            param,
                            self.packet_count,
                            t_rel)
        self.sock.sendto(payload, self.dest)

    def start_listening(self):
        """Inicia los threads para MIDI sin bloqueos"""
        self.running = True
        
        # Iniciar heartbeat
        heartbeat_thread = threading.Thread(target=self.send_status_heartbeat, daemon=True)
        heartbeat_thread.start()
        
        # Detectar dispositivo MIDI
        inputs = mido.get_input_names()
        if not inputs:
            print("[!] Sin dispositivo MIDI. Heartbeat seguirá activo...")
            device_name = None
        else:
            device_name = inputs[0]
            print(f"[*] MIDI detectado: {device_name} -> {self.quest_ip}:{self.port}")
        
        # Iniciar thread de lectura MIDI si hay dispositivo
        if device_name:
            midi_thread = threading.Thread(target=self.midi_input_thread, 
                                          args=(device_name,), 
                                          daemon=True)
            midi_thread.start()
        
        print(f"[*] EtheriaVR MIDI Listo (latencia mínima, lectura bloqueante)")
        print("-" * 60)
        
        # Con lectura bloqueante, el thread MIDI hace TODO
        # El main loop solo duerme
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print(f"\n[!] MIDI detenido")
        finally:
            self.running = False
            self.sock.close()
            self.status_sock.close()