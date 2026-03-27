"""
ETHERIAVR - Probador de Grabaciones MIDI
Reproductor de JSONs grabados para verificar tiempos y notas
"""

import json
import os
import time
from datetime import datetime
from threading import Thread, Event
import pygame
import mido
from pathlib import Path

# Configuración
SONGS_FOLDER = "songs"
BACKGROUND_AUDIO_BASE = "PianoSongs/background song"
NOTES_FOLDER = "PianoSongs/notes"

def note_name_to_midi(note_name):
    """Convierte nombre de nota musical a número MIDI
    Ej: 'c4' -> 60, 'd#4' -> 63, 'a3' -> 57
    """
    notes_map = {'c': 0, 'c#': 1, 'd': 2, 'd#': 3, 'e': 4, 'f': 5, 'f#': 6, 
                 'g': 7, 'g#': 8, 'a': 9, 'a#': 10, 'b': 11}
    
    note_name = note_name.lower().strip()
    
    try:
        # Extraer octava (último carácter)
        octave = int(note_name[-1])
        note_str = note_name[:-1]
        
        if note_str not in notes_map:
            return None
        
        # Fórmula MIDI: (octava + 1) * 12 + offset_nota
        midi_num = (octave + 1) * 12 + notes_map[note_str]
        return midi_num
    except:
        return None

class MIDIPlayback:
    def __init__(self, json_file):
        self.json_file = json_file
        self.json_data = None
        self.stop_event = Event()
        self.note_sounds = {}
        self.playback_start = 0
        self.midi_output = None
        
        # Inicializar pygame PRIMERO
        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(64)  # Permitir hasta 64 sonidos simultáneos
            print("[✓] pygame.mixer inicializado (64 canales)")
        except Exception as e:
            print(f"[!] Error inicializando mixer: {e}")
        
        # Cargar JSON
        self._load_json()
        
        # Cargar sonidos de notas (si existen) DESPUÉS de init
        self._load_note_sounds()
        
        # Detectar salida MIDI
        self._setup_midi_output()
    
    def _load_json(self):
        """Carga el JSON de la grabación"""
        if not os.path.exists(self.json_file):
            print(f"[!] Archivo no encontrado: {self.json_file}")
            return False
        
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.json_data = json.load(f)
            
            print(f"[✓] JSON cargado: {self.json_file}")
            print(f"    Canción: {self.json_data.get('song_name', 'N/A')}")
            print(f"    Duración: {self.json_data.get('duration', 0):.2f}s")
            print(f"    Total notas: {self.json_data.get('total_notes', 0)}")
            print(f"    Acordes: {self.json_data.get('total_chords', 0)}")
            return True
        
        except Exception as e:
            print(f"[!] Error cargando JSON: {e}")
            return False
    
    def _load_note_sounds(self):
        """Carga sonidos de notas para reproducción local (ej: c4.wav, d#4.wav)"""
        if not os.path.exists(NOTES_FOLDER):
            print(f"[*] Carpeta de sonidos no existe: {NOTES_FOLDER}")
            return
        
        try:
            for filename in os.listdir(NOTES_FOLDER):
                if filename.endswith(('.wav', '.mp3', '.ogg')):
                    try:
                        # Extraer nombre sin extensión (ej: "c4" de "c4.wav")
                        note_name = filename.rsplit('.', 1)[0]
                        midi_note = note_name_to_midi(note_name)
                        
                        if midi_note is not None:
                            filepath = os.path.join(NOTES_FOLDER, filename)
                            sound = pygame.mixer.Sound(filepath)
                            sound.set_volume(1.0)  # Volumen máximo (100%)
                            self.note_sounds[midi_note] = sound
                    except Exception as e:
                        pass
            
            if self.note_sounds:
                print(f"[✓] {len(self.note_sounds)} sonidos cargados (volumen: 100%)")
        
        except Exception as e:
            print(f"[*] Error cargando sonidos: {e}")
    
    def _setup_midi_output(self):
        """Configura salida MIDI opcional para sincronización con otros dispositivos"""
        try:
            outputs = mido.get_output_names()
            if outputs:
                # Usar primera salida disponible
                self.midi_output = mido.open_output(outputs[0])
                print(f"[*] Salida MIDI: {outputs[0]}")
            else:
                print(f"[*] No hay salida MIDI disponible")
        except Exception as e:
            print(f"[*] MIDI output deshabilitado: {e}")
    
    def _send_midi_note(self, note, velocity=100, duration=0.1):
        """Envía nota MIDI si hay output disponible"""
        if not self.midi_output:
            return
        
        try:
            # Nota activa
            msg_on = mido.Message('note_on', note=note, velocity=velocity)
            self.midi_output.send(msg_on)
            
            # Envío de timbre
            if note in self.note_sounds:
                try:
                    self.note_sounds[note].play()
                except:
                    pass
            
            # Esperar duración
            time.sleep(duration)
            
            # Nota inactiva
            msg_off = mido.Message('note_off', note=note)
            self.midi_output.send(msg_off)
        
        except Exception as e:
            pass
    
    def _playback_thread(self):
        """Thread que reproduce las notas en tiempo real"""
        if not self.json_data or 'all_notes' not in self.json_data:
            return
        
        notes = self.json_data['all_notes']
        self.playback_start = time.perf_counter()
        
        # Índice de nota actual
        note_index = 0
        
        while not self.stop_event.is_set():
            elapsed = time.perf_counter() - self.playback_start
            
            # Reproducir notas que llegaron
            while note_index < len(notes) and not self.stop_event.is_set():
                note_data = notes[note_index]
                note_time = note_data['time']
                
                # Aún no es tiempo de esta nota
                if elapsed < note_time:
                    break
                
                # Reproducir nota
                midi_notes = note_data['midi_notes']
                duration = note_data.get('duration', 0.1)
                clef = note_data.get('clef', 'treble')
                is_chord = note_data.get('is_chord', False)
                
                tipo = "🎼 ACORDE" if is_chord else "♪ NOTA"
                clef_name = "Sol" if clef == 'treble' else "Fa"
                notas_str = f"[{', '.join(map(str, midi_notes))}]"
                
                print(f"  {tipo} @ {note_time:.3f}s ({clef_name}) {notas_str} [dur: {duration:.3f}s]")
                
                # Reproducir sonidos
                for note in midi_notes:
                    if note in self.note_sounds:
                        try:
                            # Reproducir en thread separado para no bloquear
                            sound = self.note_sounds[note]
                            play_thread = Thread(
                                target=lambda s=sound: s.play(),
                                daemon=True
                            )
                            play_thread.start()
                        except Exception as e:
                            pass
                
                note_index += 1
            
            # Verificar si terminó la reproducción
            if note_index >= len(notes):
                break
            
            time.sleep(0.01)
    
    def play(self):
        """Reproduce la grabación completa"""
        if not self.json_data:
            print("[!] No hay datos para reproducir")
            return False
        
        # Cargar audio de fondo
        audio_file = self.json_data.get('audio_file', 'test_song.mp3')
        
        # Buscar el archivo de audio
        if not os.path.exists(audio_file):
            # Intentar en PianoSongs/background song/
            alt_path = os.path.join(BACKGROUND_AUDIO_BASE, os.path.basename(audio_file))
            if os.path.exists(alt_path):
                audio_file = alt_path
            else:
                print(f"[!] Archivo de audio no encontrado: {audio_file}")
                audio_file = None
        
        # Reproducir
        try:
            print("\n" + "="*60)
            print("▶️  REPRODUCIENDO...")
            print("="*60)
            
            # Cargar audio
            if audio_file and os.path.exists(audio_file):
                try:
                    sound = pygame.mixer.Sound(audio_file)
                    duration = sound.get_length()
                    print(f"[*] Audio: {audio_file} ({duration:.2f}s)")
                    sound.play()
                except Exception as e:
                    print(f"[!] Error cargando audio: {e}")
                    sound = None
                    duration = self.json_data.get('recorded_duration', 10)
            else:
                print("[*] Sin audio de fondo (solo notas)")
                sound = None
                duration = self.json_data.get('recorded_duration', 10)
            
            # Iniciar thread de reproducción
            play_thread = Thread(target=self._playback_thread, daemon=True)
            play_thread.start()
            
            print(f"\n📝 Notas a reproducir:")
            print("-"*60)
            
            # Esperar a que termine
            while not self.stop_event.is_set():
                if sound and not pygame.mixer.get_busy():
                    # Audio terminó
                    print("\n[*] Audio terminado")
                    break
                
                # Timeout por duración grabada
                elapsed = time.perf_counter() - self.playback_start
                if elapsed > duration + 1:
                    print(f"\n[*] Reproducción completada ({elapsed:.2f}s)")
                    break
                
                time.sleep(0.1)
            
            # Esperar a que terminen notas
            play_thread.join(timeout=2)
            
            print("\n" + "="*60)
            print("✅ Reproducción finalizada")
            print("="*60)
            
            return True
        
        except KeyboardInterrupt:
            print("\n[*] Reproducción cancelada (Ctrl+C)")
            self.stop_event.set()
            return False
        
        except Exception as e:
            print(f"[!] Error durante reproducción: {e}")
            return False


def main():
    print("\n" + "="*60)
    print("🎵 ETHERIAVR - PROBADOR DE GRABACIONES MIDI")
    print("="*60)
    
    # Listar JSONs disponibles
    if not os.path.exists(SONGS_FOLDER):
        print(f"\n[!] Carpeta no encontrada: {SONGS_FOLDER}")
        print("    Primero debes grabar una canción con record_song_helper.py")
        return
    
    json_files = [f for f in os.listdir(SONGS_FOLDER) if f.endswith('.json')]
    
    if not json_files:
        print(f"\n[!] No hay JSONs en la carpeta '{SONGS_FOLDER}'")
        print("    Primero debes grabar una canción con record_song_helper.py")
        return
    
    print(f"\n📁 Grabaciones disponibles en '{SONGS_FOLDER}':")
    for i, json_file in enumerate(json_files, 1):
        print(f"   {i}. {json_file}")
    
    # Pedir selección
    print()
    choice = input("📝 Nombre del JSON a probar (sin .json): ").strip()
    
    if not choice:
        print("[!] Operación cancelada")
        return
    
    # Agregar .json si no lo tiene
    if not choice.endswith('.json'):
        choice += '.json'
    
    json_path = os.path.join(SONGS_FOLDER, choice)
    
    if not os.path.exists(json_path):
        print(f"[!] Archivo no encontrado: {json_path}")
        return
    
    # Crear reproductor y jugar
    player = MIDIPlayback(json_path)
    player.play()


if __name__ == "__main__":
    main()
