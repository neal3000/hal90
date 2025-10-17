#!/bin/bash
# Fix USB Microphone for Wake Word Detection

echo "=========================================="
echo "USB Microphone Fix for Wake Word Detection"
echo "=========================================="
echo

# Disable Auto Gain Control (can cause issues)
echo "Disabling Auto Gain Control..."
amixer -c 2 set 'Auto Gain Control' off 2>/dev/null && echo "✓ Auto Gain Control disabled" || echo "✗ Could not disable Auto Gain Control"

# Set microphone to maximum
echo "Setting microphone volume to maximum..."
amixer -c 2 set Mic 16 unmute 2>/dev/null && echo "✓ Mic volume set to 16 (100%)" || echo "✗ Could not set Mic volume"

echo
echo "Current settings:"
amixer -c 2 | grep -A 5 "Simple mixer control 'Mic'"
echo

# Test recording
echo "=========================================="
echo "Testing microphone..."
echo "=========================================="
echo "Recording 3 seconds (speak loudly)..."
echo

arecord -D hw:2,0 -d 3 -f S16_LE -r 48000 -c 1 /tmp/mic_test.wav 2>&1

echo
echo "Analyzing volume..."
python3 << 'EOF'
import wave
import numpy as np

try:
    with wave.open('/tmp/mic_test.wav', 'rb') as wf:
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16)

        rms = np.sqrt(np.mean(audio ** 2))
        peak = np.max(np.abs(audio))

        print(f"RMS level: {rms:.0f}")
        print(f"Peak level: {peak:.0f}")
        print()

        if rms < 500:
            print("❌ VOLUME TOO LOW!")
            print("Solutions:")
            print("  1. Speak MUCH louder and closer to mic")
            print("  2. Check if mic has physical volume knob - turn it up")
            print("  3. Try different USB port")
            print("  4. Check mic is not muted physically")
        elif rms > 15000:
            print("⚠ VOLUME TOO HIGH - may distort")
        else:
            print("✅ VOLUME GOOD!")

except Exception as e:
    print(f"Could not analyze: {e}")
EOF

echo
echo "Playing back recording..."
aplay /tmp/mic_test.wav 2>/dev/null
echo

echo "=========================================="
echo "If you heard yourself clearly, mic is working!"
echo "If not, check:"
echo "  1. USB connection"
echo "  2. Physical mic switch/mute button"
echo "  3. Speak louder"
echo "=========================================="
