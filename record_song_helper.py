"""
ETHERIAVR - Grabador de Canciones MIDI
Helper para generar JSONs de prueba con notas y tiempos
"""

import mido
import json
import os
import time
from datetime import datetime
from pathlib import Path
from threading import Thread, Event
import pygame
import sys
import numpy as np

# Configuración
BACKGROUND_AUDIO = "PianoSongs/background song/test_song.mp3"  # Música de fondo
NOTES_FOLDER = "PianoSongs/notes"  # Carpeta con sonidos de notas
ACCORDION_THRESHOLD = 0.02  # 20ms para detectar acordes (más sensible)
TREBLE_CLEF_THRESHOLD = 60  # C4 - notas >= 60 = clave de sol
BASS_CLEF_THRESHOLD = 59    # B3 - notas < 60 = clave de fa
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
class SongRecorder:
    def __init__(self, audio_path=BACKGROUND_AUDIO, output_name=None, bpm=120):
        self.audio_path = audio_path
        self.output_name = output_name or f"song_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.bpm = bpm  # Tempo en beats por minuto
        
        # Eventos
        self.recording = False
        self.stop_event = Event()
        
        # Datos grabados
        self.midi_events = []
        self.song_duration = 0
        self.start_time = 0
        
        # Estado
        self.current_notes = {}  # midi_note: {time, velocity}
        self.last_chord_check_time = 0
        
        # Inicializar pygame para audio PRIMERO
        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(64)  # Permitir hasta 64 sonidos simultáneos
            print("[✓] pygame.mixer inicializado (64 canales)")
        except Exception as e:
            print(f"[!] Error inicializando mixer: {e}")
        
        # Sonidos de notas cargados (después de init mixer)
        self.note_sounds = {}
        self._load_note_sounds()
        
        # Cargar audio de fondo
        try:
            self.sound = pygame.mixer.Sound(audio_path)
            self.song_duration = self.sound.get_length()
            print(f"[✓] Audio cargado: {audio_path} ({self.song_duration:.2f}s)")
        except Exception as e:
            print(f"[!] Error cargando audio: {e}")
            self.sound = None
    
    def _load_note_sounds(self):
        """Carga los sonidos de las notas disponibles (ej: c4.wav, d#4.wav)"""
        if not os.path.exists(NOTES_FOLDER):
            print(f"[*] Carpeta de notas no encontrada: {NOTES_FOLDER}")
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
    
    def countdown(self):
        """Cuenta regresiva 3, 2, 1, bip"""
        print("\n" + "="*60)
        print(f"PREPARÁNDOSE PARA GRABAR (BPM: {self.bpm})...")
        print("="*60)
        
        for i in range(3, 0, -1):
            print(f"\n⏱️  {i}...")
            time.sleep(1)
        
        print("\n🔔 ¡BIP! GRABACIÓN INICIADA")
        print("="*60)
    
    def metronome_thread(self):
        """Thread que toca el metrónomo sincronizado con el BPM"""
        beat_duration = 60.0 / self.bpm  # Duración de cada beat en segundos
        click_duration = 0.05  # 50ms de duración del click
        
        try:
            sample_rate = 22050
            frequency = 1000  # Hz (tono del metrónomo)
            samples = int(sample_rate * click_duration)
            
            # Crear onda sinusoidal para el click
            arr = np.sin((2.0 * np.pi * frequency / sample_rate) * np.arange(samples))
            arr = (arr * 32767).astype(np.int16)
            arr = np.repeat(arr.reshape(samples, 1), 2, axis=1)  # Estéreo
            
            metronome_sound = pygame.sndarray.make_sound(arr)
            metronome_sound.set_volume(0.3)  # Volumen moderado
            
            beat_count = 0
            while not self.stop_event.is_set():
                elapsed = time.perf_counter() - self.start_time
                expected_beat = elapsed / beat_duration
                
                if int(expected_beat) > beat_count:
                    beat_count = int(expected_beat)
                    metronome_sound.play()
                    print(f"  🎵 Beat {beat_count + 1}")
                
                time.sleep(0.01)
        
        except Exception as e:
            print(f"[*] Metrónomo deshabilitado: {e}")
            while not self.stop_event.is_set():
                time.sleep(0.1)
    
    def play_audio_thread(self):
        """Thread que reproduce el audio"""
        if self.sound:
            self.sound.play()
            # Esperar a que termine o se detonga
            while pygame.mixer.get_busy() and not self.stop_event.is_set():
                time.sleep(0.1)
        
        # Auto-detener cuando termina la canción
        if not self.stop_event.is_set():
            print("\n[*] Canción terminada. Finalizando grabación...")
        self.stop_event.set()
    
    def midi_input_thread(self, device_name):
        """Thread que graba eventos MIDI y reproduce sonidos de notas"""
        try:
            with mido.open_input(device_name) as port:
                while not self.stop_event.is_set():
                    msg = port.poll()
                    if msg:
                        # Tiempo relativo desde inicio
                        elapsed = time.perf_counter() - self.start_time
                        
                        # Registrar evento
                        if msg.type == 'note_on' and msg.velocity > 0:
                            self.current_notes[msg.note] = {
                                'time': elapsed,
                                'velocity': msg.velocity
                            }
                            
                            # Reproducir sonido de la nota si existe (en thread separado)
                            if msg.note in self.note_sounds:
                                try:
                                    # Reproducir en thread para no bloquear MIDI
                                    sound = self.note_sounds[msg.note]
                                    # Copiar el sonido para evitar conflictos de canales
                                    play_thread = Thread(
                                        target=lambda s=sound: s.play(),
                                        daemon=True
                                    )
                                    play_thread.start()
                                except Exception as e:
                                    pass
                            
                            print(f"  ▶️  NOTE ON  - Nota {msg.note} (vel: {msg.velocity}) @ {elapsed:.3f}s")
                        
                        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                            if msg.note in self.current_notes:
                                note_start = self.current_notes[msg.note]['time']
                                duration = elapsed - note_start
                                velocity = self.current_notes[msg.note]['velocity']
                                
                                self.midi_events.append({
                                    'midi_note': msg.note,
                                    'time': note_start,
                                    'duration': duration,
                                    'velocity': velocity
                                })
                                
                                del self.current_notes[msg.note]
                                print(f"  ⏹️  NOTE OFF - Nota {msg.note} (duración: {duration:.3f}s)")
                    
                    else:
                        time.sleep(0.001)
        
        except Exception as e:
            print(f"[!] Error en MIDI: {e}")
    
    def detect_chords(self):
        """
        Detecta acordes agrupando notas con timestamps similares
        Si varias notas se presionan dentro de ACCORDION_THRESHOLD, son un acorde
        """
        if not self.midi_events:
            return []
        
        # Ordenar por tiempo
        events = sorted(self.midi_events, key=lambda x: x['time'])
        
        chords = []
        current_group = [events[0]]
        
        for i in range(1, len(events)):
            event = events[i]
            first_event = current_group[0]
            
            # Si está dentro del threshold, agregar al grupo
            if abs(event['time'] - first_event['time']) <= ACCORDION_THRESHOLD:
                current_group.append(event)
            else:
                # Procesar grupo actual
                if current_group:
                    chords.append(self._group_to_chord(current_group))
                current_group = [event]
        
        # Último grupo
        if current_group:
            chords.append(self._group_to_chord(current_group))
        
        return chords
    
    def _group_to_chord(self, group):
        """Convierte un grupo de notas en un acorde o nota individual"""
        midi_notes = sorted([e['midi_note'] for e in group])
        time = group[0]['time']
        
        # Duración: la más larga del grupo
        duration = max([e['duration'] for e in group])
        
        # Determinar clave según rango
        min_note = min(midi_notes)
        max_note = max(midi_notes)
        
        if max_note >= TREBLE_CLEF_THRESHOLD:
            clef = "treble"  # Clave de Sol
        else:
            clef = "bass"    # Clave de Fa
        
        # Si la mayoría está en una clave, usar esa
        treble_count = sum(1 for n in midi_notes if n >= TREBLE_CLEF_THRESHOLD)
        bass_count = len(midi_notes) - treble_count
        
        if treble_count > bass_count:
            clef = "treble"
        elif bass_count > treble_count:
            clef = "bass"
        else:
            # Empate: usar la nota más baja
            clef = "bass" if min_note < TREBLE_CLEF_THRESHOLD else "treble"
        
        return {
            'time': round(time, 3),
            'duration': round(duration, 3),
            'midi_notes': midi_notes,
            'clef': clef,
            'is_chord': len(midi_notes) > 1
        }
    
    def generate_json(self):
        """Genera el JSON con todas las notas/acordes"""
        # Detectar acordes
        chords = self.detect_chords()
        
        # Separar por clave
        treble_notes = [c for c in chords if c['clef'] == 'treble']
        bass_notes = [c for c in chords if c['clef'] == 'bass']
        
        # Estrutura final
        song_data = {
            'song_name': self.output_name,
            'audio_file': self.audio_path,
            'duration': round(self.song_duration, 2),
            'recorded_duration': round(time.perf_counter() - self.start_time, 2),
            'all_notes': chords,
            'treble_clef': treble_notes,
            'bass_clef': bass_notes,
            'total_notes': len(chords),
            'total_chords': sum(1 for c in chords if c['is_chord']),
            'recorded_at': datetime.now().isoformat()
        }
        
        return song_data
    
    def save_json(self, data, output_dir="songs"):
        """Guarda el JSON a disco"""
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{output_dir}/{self.output_name}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ JSON guardado: {filename}")
        print(f"   Ruta absoluta: {os.path.abspath(filename)}")
        return filename
    
    def record(self):
        """Inicia la grabación completa"""
        # Detectar MIDI
        inputs = mido.get_input_names()
        if not inputs:
            print("[!] ERROR: No hay dispositivo MIDI conectado")
            return False
        
        device_name = inputs[0]
        print(f"[*] Dispositivo MIDI: {device_name}")
        
        if not self.sound:
            print("[!] ERROR: No se pudo cargar el audio")
            return False
        
        # Countdown
        self.countdown()
        
        # Iniciar threads
        self.start_time = time.perf_counter()
        
        audio_thread = Thread(target=self.play_audio_thread, daemon=True)
        midi_thread = Thread(target=self.midi_input_thread, args=(device_name,), daemon=True)
        metronome = Thread(target=self.metronome_thread, daemon=True)
        
        audio_thread.start()
        midi_thread.start()
        metronome.start()
        
        # Loop principal esperando input o fin
        print("\n📝 GRABANDO... (Presiona ESPACIO para detener)")
        print("="*60)
        
        try:
            # Esperar a que termine la grabación
            while not self.stop_event.is_set():
                try:
                    # Intentar detectar espacio en Windows
                    import msvcrt
                    if msvcrt.kbhit():
                        key = msvcrt.getch()
                        if key == b' ':  # Espacio
                            print("\n[*] ⏹️  Detenido por usuario (ESPACIO)")
                            self.stop_event.set()
                            break
                except:
                    # En Unix/Linux, solo esperar a que termina la canción
                    pass
                
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\n[*] Interrumpido por Ctrl+C")
            self.stop_event.set()
        
        # Esperar a que se detengan los threads
        print("[*] Esperando a que finalicen threads...")
        audio_thread.join(timeout=2)
        midi_thread.join(timeout=2)
        
        print("[✓] Threads finalizados")
        print("\n✏️  Procesando datos grabados...")
        return True


def main():
    print("\n" + "="*60)
    print("🎵 ETHERIAVR - GRABADOR DE CANCIONES MIDI")
    print("="*60)
    
    # Configuración
    audio_file = BACKGROUND_AUDIO
    song_name = input("\n📝 Nombre de la canción (ej: 'take_on_me'): ").strip()
    
    if not song_name:
        song_name = "test_song"
    
    # Preguntar por BPM
    bpm_input = input("\n⏱️  BPM (tempo, ej: 120) [default: 120]: ").strip()
    try:
        bpm = int(bpm_input) if bpm_input else 120
        if bpm < 40 or bpm > 240:
            print("[!] BPM debe estar entre 40 y 240, usando 120")
            bpm = 120
    except ValueError:
        print("[!] BPM inválido, usando 120")
        bpm = 120
    
    # Crear grabador
    recorder = SongRecorder(audio_path=audio_file, output_name=song_name, bpm=bpm)
    
    # Grabar
    if recorder.record():
        # Generar JSON
        song_data = recorder.generate_json()
        
        # Mostrar resumen
        print("\n" + "="*60)
        print("📊 RESUMEN DE GRABACIÓN")
        print("="*60)
        print(f"Canción: {song_data['song_name']}")
        print(f"Duración audio: {song_data['duration']:.2f}s")
        print(f"Duración grabada: {song_data['recorded_duration']:.2f}s")
        print(f"Total de notas/acordes: {song_data['total_notes']}")
        print(f"Acordes detectados: {song_data['total_chords']}")
        print(f"Notas clave de Sol: {len(song_data['treble_clef'])}")
        print(f"Notas clave de Fa: {len(song_data['bass_clef'])}")
        
        # Mostrar algunas notas
        if song_data['all_notes']:
            print(f"\nPrimeras 5 notas:")
            for note in song_data['all_notes'][:5]:
                tipo = "🎼 ACORDE" if note['is_chord'] else "♪ NOTA"
                clef = "Sol" if note['clef'] == 'treble' else "Fa"
                print(f"  {tipo} @ {note['time']:.3f}s | MIDI: {note['midi_notes']} | Clave: {clef}")
        
        # Guardar
        recorder.save_json(song_data)
        
        print("\n✅ ¡Grabación completada exitosamente!")
    
    else:
        print("\n[!] Grabación cancelada")


if __name__ == "__main__":
    main()
