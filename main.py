import time
from services.discovery_service import DiscoveryService
from services.midi_service import MidiManager 

BANNER = """
.-----------------------------------------------------------.
|  ETHERIAVR - SERVICE DISCOVERY ACTIVE                     |
|  Status: UP                   |
'-----------------------------------------------------------'
"""

def run():
    print(BANNER)
    
    # 1. Fase de Descubrimiento (Escucha el "grito" del Quest)
    discovery = DiscoveryService()
    quest_ip = discovery.find_quest_ip()
    
    if quest_ip:
        # 2. Fase de MIDI (Inicia el envío de datos)
        print(f"[*] Estableciendo puente UDP con {quest_ip}...")
        
        midi_service = MidiManager(quest_ip)
        midi_service.start_listening()
    else:
        print("[!] No se pudo obtener la IP del Quest. Abortando.")

if __name__ == "__main__":
    run()