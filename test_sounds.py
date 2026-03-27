"""
Script rápido para probar que los sonidos se cargan y reproducen
"""

import os
import pygame
import time

NOTES_FOLDER = "PianoSongs/notes"

# Inicializar mixer
print("[*] Inicializando pygame.mixer...")
pygame.mixer.init()
print("[✓] pygame.mixer inicializado")

# Cargar algunos sonidos
print(f"\n[*] Buscando sonidos en: {NOTES_FOLDER}")
sounds = {}
count = 0

for filename in os.listdir(NOTES_FOLDER):
    if filename.endswith('.wav'):
        filepath = os.path.join(NOTES_FOLDER, filename)
        try:
            sound = pygame.mixer.Sound(filepath)
            sounds[filename] = sound
            count += 1
            
            # Mostrar solo los primeros 5
            if count <= 5:
                print(f"  ✓ {filename:15} cargado ({sound.get_length():.2f}s)")
        except Exception as e:
            print(f"  ✗ {filename} - {e}")

print(f"\n[✓] Total cargados: {count} sonidos")

# Probar reproducción
if sounds:
    print(f"\n[*] Probando reproducción...")
    test_files = list(sounds.keys())[:3]
    
    for filename in test_files:
        print(f"\n  Reproduciendo: {filename}...")
        sound = sounds[filename]
        sound.play()
        
        # Esperar a que termine
        duration = sound.get_length()
        time.sleep(duration + 0.1)
        
        print(f"  ✓ {filename} completado")

print("\n[✓] Test completado")
