"""
Test para verificar que múltiples notas se reproducen sin interferencias
"""

import pygame
import os
import time
from threading import Thread

NOTES_FOLDER = "PianoSongs/notes"

def note_name_to_midi(note_name):
    """Convierte nombre de nota musical a número MIDI"""
    notes_map = {'c': 0, 'c#': 1, 'd': 2, 'd#': 3, 'e': 4, 'f': 5, 'f#': 6, 
                 'g': 7, 'g#': 8, 'a': 9, 'a#': 10, 'b': 11}
    
    note_name = note_name.lower().strip()
    
    try:
        octave = int(note_name[-1])
        note_str = note_name[:-1]
        
        if note_str not in notes_map:
            return None
        
        midi_num = (octave + 1) * 12 + notes_map[note_str]
        return midi_num
    except:
        return None

print("[*] Inicializando pygame.mixer...")
pygame.mixer.init()
pygame.mixer.set_num_channels(64)
print("[✓] pygame.mixer inicializado (64 canales)")

# Cargar sonidos
print(f"\n[*] Cargando sonidos desde: {NOTES_FOLDER}")
note_sounds = {}

for filename in os.listdir(NOTES_FOLDER):
    if filename.endswith('.wav'):
        note_name = filename.rsplit('.', 1)[0]
        midi_note = note_name_to_midi(note_name)
        
        if midi_note is not None:
            filepath = os.path.join(NOTES_FOLDER, filename)
            try:
                note_sounds[midi_note] = pygame.mixer.Sound(filepath)
            except:
                pass

print(f"[✓] {len(note_sounds)} sonidos cargados")

# Test 1: Nota simple
print("\n" + "="*60)
print("TEST 1: Una nota simple")
print("="*60)
print("Tocando: C4 (MIDI 60)")
note_sounds[60].play()
time.sleep(1.5)
print("✓ Completado\n")

# Test 2: Dos notas simultáneas
print("="*60)
print("TEST 2: Dos notas simultáneas")
print("="*60)
print("Tocando: C4 (60) + G4 (67)")
note_sounds[60].play()
time.sleep(0.05)
note_sounds[67].play()
time.sleep(1.5)
print("✓ Completado\n")

# Test 3: Acorde (3 notas simultáneas)
print("="*60)
print("TEST 3: Acorde (3 notas simultáneas)")
print("="*60)
print("Tocando: C4 (60) + E4 (64) + G4 (67)")
note_sounds[60].play()
note_sounds[64].play()
note_sounds[67].play()
time.sleep(1.5)
print("✓ Completado\n")

# Test 4: Secuencia rápida
print("="*60)
print("TEST 4: Secuencia rápida")
print("="*60)
print("Tocando: C4 -> D4 -> E4 -> F4 -> G4...")
notas = [60, 62, 64, 65, 67, 69, 71, 72]
for note in notas:
    if note in note_sounds:
        print(f"  Nota {note}")
        note_sounds[note].play()
        time.sleep(0.3)
print("✓ Completado\n")

# Test 5: Múltiples notas con threading (como el grabador)
print("="*60)
print("TEST 5: Múltiples notas con threading")
print("="*60)
print("Tocando: C4 + E4 + G4 (en threads separados)")

def play_note(midi_note):
    if midi_note in note_sounds:
        note_sounds[midi_note].play()

threads = []
for note in [60, 64, 67]:
    t = Thread(target=play_note, args=(note,), daemon=True)
    threads.append(t)
    t.start()

for t in threads:
    t.join()

time.sleep(1.5)
print("✓ Completado\n")

print("="*60)
print("[✓] Todos los tests completados")
print("="*60)
print("\n¿Escuchaste todas las notas claramente?")
print("  - Test 1: Una nota clara")
print("  - Test 2: Dos notas (sin cortes)")
print("  - Test 3: Acorde completo (3 notas)")
print("  - Test 4: Secuencia fluida")
print("  - Test 5: Acorde sin interferencias")
