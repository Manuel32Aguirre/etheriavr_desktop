import pretty_midi
import json

midi_file = "tools/take_on_me_vocal.mid"

pm = pretty_midi.PrettyMIDI(midi_file)

instrument = pm.instruments[0]

notes_by_time = {}

for note in instrument.notes:

    if (note.end - note.start) < 0.15:
        continue

    key = round(note.start, 2)

    if key not in notes_by_time:
        notes_by_time[key] = note
    else:
        if note.pitch > notes_by_time[key].pitch:
            notes_by_time[key] = note

notes = []

for note in notes_by_time.values():

    note_name = pretty_midi.note_number_to_name(note.pitch)

    notes.append({
        "note": note_name,
        "midi": int(note.pitch),
        "start": float(note.start),
        "duration": float(note.end - note.start)
    })

song = {
    "songName": "Take On Me",
    "notes": notes
}

with open("song_take_on_me.json", "w") as f:
    json.dump(song, f, indent=4)

print("JSON generado")