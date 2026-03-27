import time
from services.discovery_service import DiscoveryService
from services.midi_service import MidiManager 
from services.vocal_service import VocalManager

BANNER = """
.-----------------------------------------------------------.
|  ETHERIAVR - SERVICE DISCOVERY ACTIVE                     |
|  Status: UP                   |
'-----------------------------------------------------------'
"""

def run():
    print(BANNER)
    
    mode=0; #0 para midi, 1 para canto    
    
    # 1. Fase de Descubrimiento (Escucha el "grito" del Quest)
    discovery = DiscoveryService()
    quest_ip = discovery.find_quest_ip()
    
    if quest_ip:
        print(f"[*] Estableciendo puente UDP con {quest_ip}...")
        if mode==0:
            midi_service = MidiManager(quest_ip)
            midi_service.start_listening()
        elif mode==1:
            vocal = VocalManager(quest_ip)
            vocal.start_processing()    
    else:
        print("[!] No se pudo obtener la IP del Quest. Abortando.")

if __name__ == "__main__":
    run()