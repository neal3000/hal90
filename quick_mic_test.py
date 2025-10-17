#!/usr/bin/env python3
"""Quick microphone test - just shows you what your mic outputs"""
import sounddevice as sd
import numpy as np

print("Quick Microphone Level Test")
print("Speak for 3 seconds when recording starts...\n")
input("Press Enter to start: ")

print("🎤 Recording 3 seconds - SPEAK NOW!")

# Record with NO amplification
recording = sd.rec(
    int(3 * 48000),
    samplerate=48000,
    channels=1,
    device=2,  # Your USB device
    dtype='int16'
)
sd.wait()

print("✓ Done\n")

# Analyze
audio = recording.flatten()
rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
peak = np.max(np.abs(audio))

print(f"Raw RMS Level:  {rms:.1f}")
print(f"Raw Peak Level: {peak}\n")

# Determine what to do
if rms < 50:
    print("→ VERY QUIET mic: Use AUDIO_AMPLIFICATION=300.0")
elif rms < 500:
    amp = max(10, 3000 / rms)
    print(f"→ Quiet mic: Use AUDIO_AMPLIFICATION={amp:.1f}")
elif rms < 2000:
    amp = max(1, 2400 / rms)
    print(f"→ Normal mic: Use AUDIO_AMPLIFICATION={amp:.1f}")
else:
    print(f"→ LOUD mic: Use AUDIO_AMPLIFICATION=1.0")
    print(f"→ Also set: RECORDING_SILENCE_THRESHOLD={int(rms * 0.5)}")
