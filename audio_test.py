import sounddevice as sd
import numpy as np

DEVICE_INDEX = 34
SAMPLE_RATE = 48000
FRAME_SIZE = 1024
THRESHOLD = 0.15
MIN_FREQ = 80
MAX_FREQ = 600
previous_pitch = -1
last_valid_pitch = -1
drop_frames = 0
MAX_DROPS = 3
stable_midi = -1
stable_time = 0
REQUIRED_STABLE_TIME = 0.15  # 150 ms

def yin_pitch(signal, sample_rate):
    signal = signal - np.mean(signal)

    tau_min = int(sample_rate / MAX_FREQ)
    tau_max = int(sample_rate / MIN_FREQ)

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

            # Interpolación parabólica
            if tau + 1 < tau_max and tau - 1 > 0:
                s0 = cmnd[tau - 1]
                s1 = cmnd[tau]
                s2 = cmnd[tau + 1]

                a = (s0 + s2 - 2 * s1) / 2
                b = (s2 - s0) / 2

                if a != 0:
                    tau = tau - b / (2 * a)

            return sample_rate / tau

    return -1

def smooth_pitch(current_pitch):
    global previous_pitch

    if current_pitch <= 0:
        return -1

    if previous_pitch > 0:
        # Diferencia en cents
        cents_diff = 1200 * np.log2(current_pitch / previous_pitch)

        # Si cambio grande → ataque rápido
        if abs(cents_diff) > 100:
            alpha = 0.6
        else:
            alpha = 0.25

        current_pitch = alpha * current_pitch + (1 - alpha) * previous_pitch

    previous_pitch = current_pitch
    return current_pitch

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F",
              "F#", "G", "G#", "A", "A#", "B"]

def hz_to_midi(frequency):
    if frequency <= 0:
        return -1
    return 69 + 12 * np.log2(frequency / 440.0)

def midi_to_hz(midi):
    return 440.0 * (2 ** ((midi - 69) / 12))

def pitch_to_note_data(frequency):
    midi_float = hz_to_midi(frequency)
    midi_int = int(round(midi_float))

    reference_freq = midi_to_hz(midi_int)
    cents = 1200 * np.log2(frequency / reference_freq)

    note_name = NOTE_NAMES[midi_int % 12]
    octave = (midi_int // 12) - 1
    note_label = f"{note_name}{octave}"

    return midi_int, note_label, cents

def detect_stability(current_midi, current_cents, delta_time):
    global stable_midi, stable_time

    if stable_midi == -1:
        stable_midi = current_midi
        stable_time = 0
        return False

    # Si es misma nota
    if current_midi == stable_midi:
        stable_time += delta_time

    # Si es nota vecina pero dentro de 40 cents → aún lo consideramos estable
    elif abs(current_cents) < 40:
        stable_time += delta_time

    else:
        stable_time = 0
        stable_midi = current_midi

    return stable_time >= REQUIRED_STABLE_TIME

def audio_callback(indata, frames, time_info, status):
    global last_valid_pitch, drop_frames

    audio = indata[:, 0]
    energy = np.mean(audio ** 2)

    if energy < 0.0005:
        drop_frames += 1
        if drop_frames < MAX_DROPS and last_valid_pitch > 0:
            midi, note, cents = pitch_to_note_data(last_valid_pitch)
            print(f"{note} | {last_valid_pitch:.2f} Hz | {cents:+.1f} cents")
        return

    pitch = yin_pitch(audio, SAMPLE_RATE)

    if pitch > 0:
        pitch = smooth_pitch(pitch)
        last_valid_pitch = pitch
        drop_frames = 0

        midi, note, cents = pitch_to_note_data(pitch)
        is_stable = detect_stability(midi, cents, FRAME_SIZE / SAMPLE_RATE)
        print(f"{note} | {pitch:.2f} Hz | {cents:+.1f} cents | Stable: {is_stable}")

    else:
        drop_frames += 1
        if drop_frames < MAX_DROPS and last_valid_pitch > 0:
            midi, note, cents = pitch_to_note_data(last_valid_pitch)
            print(f"{note} | {last_valid_pitch:.2f} Hz | {cents:+.1f} cents")

with sd.InputStream(
    device=DEVICE_INDEX,
    channels=1,
    samplerate=SAMPLE_RATE,
    blocksize=FRAME_SIZE,
    callback=audio_callback
):
    print("🎤 YIN vocal engine activo...")
    while True:
        pass