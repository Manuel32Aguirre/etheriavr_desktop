import socket
import time
import numpy as np
import sounddevice as sd
import os
from dotenv import load_dotenv

load_dotenv()

DEVICE_INDEX = 0
SAMPLE_RATE = 48000
FRAME_SIZE = 1024
THRESHOLD = 0.15
MIN_FREQ = 80
MAX_FREQ = 1200

REQUIRED_STABLE_TIME = 0.15
MAX_DROPS = 3

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F",
              "F#", "G", "G#", "A", "A#", "B"]


class VocalManager:

    def __init__(self, quest_ip, port=None):
        self.quest_ip = quest_ip
        self.port = port or int(os.getenv("UDP_PORT"))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.packet_count = 0
        self.start_time = time.perf_counter()

        self.previous_pitch = -1
        self.last_valid_pitch = -1
        self.drop_frames = 0

        self.stable_midi = -1
        self.stable_time = 0

        # 🔥 Control de tasa de envío (30 Hz estable para VR)
        self.last_send_time = 0
        self.send_interval = 0.033

    # -------------------- YIN --------------------

    def yin_pitch(self, signal):
        signal = signal - np.mean(signal)

        tau_min = int(SAMPLE_RATE / MAX_FREQ)
        tau_max = int(SAMPLE_RATE / MIN_FREQ)

        diff = np.zeros(tau_max)

        for tau in range(tau_min, tau_max):
            diff[tau] = np.sum((signal[:-tau] - signal[tau:]) ** 2)

        cmnd = np.zeros(tau_max)
        cmnd[0] = 1
        running_sum = 0

        for tau in range(1, tau_max):
            running_sum += diff[tau]
            if running_sum == 0:
                cmnd[tau] = 1
            else:
                cmnd[tau] = diff[tau] * tau / running_sum

        for tau in range(tau_min, tau_max):
            if cmnd[tau] < THRESHOLD:

                if tau + 1 < tau_max and tau - 1 > 0:
                    s0 = cmnd[tau - 1]
                    s1 = cmnd[tau]
                    s2 = cmnd[tau + 1]

                    a = (s0 + s2 - 2 * s1) / 2
                    b = (s2 - s0) / 2

                    if a != 0:
                        tau = tau - b / (2 * a)

                return SAMPLE_RATE / tau

        return -1

    # -------------------- Pitch smoothing --------------------

    def smooth_pitch(self, current_pitch):

        if current_pitch <= 0:
            return -1

        if self.previous_pitch > 0:
            cents_diff = 1200 * np.log2(current_pitch / self.previous_pitch)

            if abs(cents_diff) > 100:
                alpha = 0.6
            else:
                alpha = 0.25

            current_pitch = alpha * current_pitch + (1 - alpha) * self.previous_pitch

        self.previous_pitch = current_pitch
        return current_pitch

    # -------------------- Musical conversion --------------------

    def hz_to_midi(self, frequency):
        return 69 + 12 * np.log2(frequency / 440.0)

    def midi_to_hz(self, midi):
        return 440.0 * (2 ** ((midi - 69) / 12))

    def pitch_to_note_data(self, frequency):

        midi_float = self.hz_to_midi(frequency)
        midi_int = int(round(midi_float))

        reference_freq = self.midi_to_hz(midi_int)
        cents = 1200 * np.log2(frequency / reference_freq)

        note_name = NOTE_NAMES[midi_int % 12]
        octave = (midi_int // 12) - 1
        note_label = f"{note_name}{octave}"

        return midi_int, note_label, cents

    # -------------------- Stability --------------------

    def detect_stability(self, current_midi, current_cents):

        delta_time = FRAME_SIZE / SAMPLE_RATE

        if self.stable_midi == -1:
            self.stable_midi = current_midi
            self.stable_time = 0
            return False

        if current_midi == self.stable_midi:
            self.stable_time += delta_time
        elif abs(current_cents) < 40:
            self.stable_time += delta_time
        else:
            self.stable_time = 0
            self.stable_midi = current_midi

        return self.stable_time >= REQUIRED_STABLE_TIME

    # -------------------- UDP Send --------------------

    def send_udp(self, pitch, midi, note, cents, stable):

        now = time.perf_counter()

        # Limitar frecuencia de envío
        if now - self.last_send_time < self.send_interval:
            return

        self.last_send_time = now

        self.packet_count += 1
        t_rel = now - self.start_time
        stable_flag = 1 if stable else 0

        payload = (
            f"voice|{pitch:.2f}|{midi}|{note}|"
            f"{cents:.1f}|{stable_flag}|"
            f"{self.packet_count}|{t_rel:.4f}"
        )
        print("IP DESTINO:", self.quest_ip, "PUERTO:", self.port)
        print("ENVIANDO UDP")
        self.sock.sendto(payload.encode('utf-8'), (self.quest_ip, self.port))

    # -------------------- Audio callback --------------------

    def audio_callback(self, indata, frames, time_info, status):
        audio = np.mean(indata, axis=1)
        energy = np.mean(audio ** 2)

        if energy < 0.0005:
            self.drop_frames += 1
            if self.drop_frames < MAX_DROPS and self.last_valid_pitch > 0:
                midi, note, cents = self.pitch_to_note_data(self.last_valid_pitch)
                stable = self.detect_stability(midi, cents)
                self.send_udp(self.last_valid_pitch, midi, note, cents, stable)
            return

        pitch = self.yin_pitch(audio)

        if pitch > 0:
            pitch = self.smooth_pitch(pitch)

            self.last_valid_pitch = pitch
            self.drop_frames = 0

            midi, note, cents = self.pitch_to_note_data(pitch)
            stable = self.detect_stability(midi, cents)

            self.send_udp(pitch, midi, note, cents, stable)

        else:
            self.drop_frames += 1
            if self.drop_frames < MAX_DROPS and self.last_valid_pitch > 0:
                midi, note, cents = self.pitch_to_note_data(self.last_valid_pitch)
                stable = self.detect_stability(midi, cents)
                self.send_udp(self.last_valid_pitch, midi, note, cents, stable)

    # -------------------- Start processing --------------------

    def start_processing(self):

        print(f"[*] Vocal Engine activo → Enviando a {self.quest_ip}:{self.port}")

        with sd.InputStream(
            device=DEVICE_INDEX,
            channels=1,
            samplerate=SAMPLE_RATE,
            blocksize=FRAME_SIZE,
            callback=self.audio_callback
        ):
            while True:
                time.sleep(1)