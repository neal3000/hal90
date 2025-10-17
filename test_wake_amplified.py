#!/usr/bin/env python3
"""
Test Wake Word Detection with Software Amplification
For PCM2902 and other low-gain USB devices
"""
import asyncio
import logging
import sys
import numpy as np
import sounddevice as sd
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

from wake_word_detector_amplified import WakeWordDetectorAmplified

# Configuration
SAMPLE_RATE = 48000
WAKE_WORD = "max"
MODEL_PATH = "./models/vosk-model-small-en-us-0.15"
AMPLIFICATION = 300.0  # 300x amplification for PCM2902

print("=" * 70)
print("  AMPLIFIED WAKE WORD TEST")
print("  For PCM2902 and Low-Gain USB Devices")
print("=" * 70)
print()

async def test_with_amplification():
    """Test wake word detection with amplification"""

    # Check model
    if not Path(MODEL_PATH).exists():
        print(f"ERROR: Vosk model not found at {MODEL_PATH}")
        print("Download it first!")
        return False

    print("Step 1: Testing microphone with amplification")
    print("-" * 70)
    print(f"Recording 3 seconds at {SAMPLE_RATE}Hz...")
    print("Speak normally into your microphone...")
    print()

    # Record from USB device (device 2)
    print("Recording from device 2 (USB PnP Sound Device)...")
    recording = sd.rec(
        int(3 * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='int16',
        device=2  # Force USB device
    )
    sd.wait()

    # Analyze original
    rms_original = np.sqrt(np.mean(recording ** 2))
    print(f"Original RMS: {rms_original:.0f}")

    # Amplify
    recording_float = recording.astype(np.float32).flatten()
    amplified = recording_float * AMPLIFICATION
    amplified = np.tanh(amplified / 32767.0) * 32767.0
    amplified_int16 = np.clip(amplified, -32768, 32767).astype(np.int16)

    rms_amplified = np.sqrt(np.mean(amplified_int16 ** 2))
    print(f"Amplified RMS ({AMPLIFICATION}x): {rms_amplified:.0f}")
    print()

    if rms_amplified < 1000:
        print("⚠ Even with amplification, volume is low")
        print("Make sure to speak loudly and close to mic!")
    else:
        print(f"✓ Amplified volume looks good!")

    print()
    print("Step 2: Wake Word Detection Test")
    print("-" * 70)
    print(f"Listening for wake word: '{WAKE_WORD}'")
    print("Speak normally - amplification is active!")
    print("(Will detect up to 3 times or timeout in 30 seconds)")
    print()

    detection_count = [0]

    async def on_wake_word():
        detection_count[0] += 1
        print()
        print("!" * 70)
        print(f"  ✓✓✓ WAKE WORD DETECTED! (#{detection_count[0]}) ✓✓✓")
        print("!" * 70)
        print()

        if detection_count[0] < 3:
            print(f"Say '{WAKE_WORD}' again...")
            print()

    try:
        # Initialize detector with amplification
        detector = WakeWordDetectorAmplified(
            model_path=MODEL_PATH,
            wake_word=WAKE_WORD,
            sample_rate=SAMPLE_RATE,
            amplification=AMPLIFICATION
        )

        # Start listening
        listen_task = asyncio.create_task(detector.listen(on_wake_word))

        # Wait for 3 detections or 30 second timeout
        for i in range(300):  # 30 seconds
            if detection_count[0] >= 3:
                break
            await asyncio.sleep(0.1)

        # Stop
        await detector.stop()
        listen_task.cancel()
        try:
            await listen_task
        except asyncio.CancelledError:
            pass

        print()
        print("=" * 70)
        if detection_count[0] > 0:
            print(f"✓✓✓ TEST PASSED! Detected {detection_count[0]} time(s)")
            print("Amplification is working!")
        else:
            print("✗ TEST FAILED - No detections")
            print()
            print("Troubleshooting:")
            print(f"  1. Say the exact word: '{WAKE_WORD}'")
            print("  2. Speak clearly but normally (don't whisper)")
            print("  3. Check that mic is not muted/blocked")
            print("  4. Try increasing amplification in wake_word_detector_amplified.py")
            print(f"     (current: {AMPLIFICATION}x, try: 100.0)")
        print("=" * 70)
        print()

        return detection_count[0] > 0

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    try:
        success = asyncio.run(test_with_amplification())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest cancelled")
        sys.exit(1)
