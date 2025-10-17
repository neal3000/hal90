#!/usr/bin/env python3
"""
Audio Diagnostic Tool
Helps identify the correct audio settings for your microphone
"""
import sounddevice as sd
import numpy as np
import time

print("=" * 70)
print("  AUDIO DIAGNOSTIC TOOL")
print("=" * 70)

# List devices
print("\nAvailable audio input devices:")
devices = sd.query_devices()
input_devices = []
for i, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        input_devices.append(i)
        print(f"  [{i}] {device['name']}")
        print(f"      Channels: {device['max_input_channels']}")
        print(f"      Default sample rate: {device['default_samplerate']}Hz")

if not input_devices:
    print("\n❌ No input devices found!")
    exit(1)

# Select device
print(f"\nCurrent device in .env: 2")
device_id = int(input("Enter device number to test (or press Enter for 2): ").strip() or "2")

if device_id not in input_devices:
    print(f"❌ Device {device_id} is not an input device!")
    exit(1)

print(f"\n✓ Testing device {device_id}: {devices[device_id]['name']}")

# Test settings
sample_rate = 48000
duration = 5

print("\n" + "=" * 70)
print("  RAW MICROPHONE TEST (No Amplification)")
print("=" * 70)
print(f"\nSpeak normally for {duration} seconds when recording starts...")
input("Press Enter to start recording...")

print(f"\n🎤 Recording for {duration} seconds - SPEAK NOW!")

try:
    # Record raw audio
    recording = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        device=device_id,
        dtype='int16'
    )
    sd.wait()

    print("✓ Recording complete")

    # Analyze raw audio
    audio = recording.flatten()

    # Calculate statistics
    rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
    peak = np.max(np.abs(audio))
    mean_abs = np.mean(np.abs(audio))

    # Calculate percentage of samples above silence threshold
    threshold = 2000
    above_threshold = np.sum(np.abs(audio) > threshold)
    total_samples = len(audio)
    percent_above = (above_threshold / total_samples) * 100

    print("\n📊 RAW AUDIO ANALYSIS:")
    print(f"  RMS Level:          {rms:.1f}")
    print(f"  Peak Level:         {peak}")
    print(f"  Mean Absolute:      {mean_abs:.1f}")
    print(f"  Samples > {threshold}:     {above_threshold} ({percent_above:.1f}%)")

    # Determine microphone type
    print("\n🔍 MICROPHONE TYPE ANALYSIS:")

    if rms < 50:
        mic_type = "VERY LOW GAIN (like PCM2902)"
        recommended_amp = 300.0
        print(f"  Type: {mic_type}")
        print(f"  Your mic has extremely low output")
        print(f"  ✅ Recommended: AUDIO_AMPLIFICATION={recommended_amp}")

    elif rms < 500:
        mic_type = "LOW GAIN"
        recommended_amp = max(10.0, (threshold * 1.5) / rms)
        print(f"  Type: {mic_type}")
        print(f"  Your mic has low output")
        print(f"  ✅ Recommended: AUDIO_AMPLIFICATION={recommended_amp:.1f}")

    elif rms < 2000:
        mic_type = "NORMAL GAIN"
        recommended_amp = max(1.0, (threshold * 1.2) / rms)
        print(f"  Type: {mic_type}")
        print(f"  Your mic has moderate output")
        print(f"  ✅ Recommended: AUDIO_AMPLIFICATION={recommended_amp:.1f}")

    elif rms < 5000:
        mic_type = "HIGH GAIN"
        recommended_amp = max(1.0, (threshold * 0.8) / rms)
        print(f"  Type: {mic_type}")
        print(f"  Your mic has strong output")
        if recommended_amp < 1.0:
            print(f"  ✅ Recommended: AUDIO_AMPLIFICATION=1.0 (no amplification needed)")
        else:
            print(f"  ✅ Recommended: AUDIO_AMPLIFICATION={recommended_amp:.1f}")

    else:
        mic_type = "VERY HIGH GAIN"
        print(f"  Type: {mic_type}")
        print(f"  Your mic has very strong output")
        print(f"  ✅ Recommended: AUDIO_AMPLIFICATION=1.0 (no amplification)")
        print(f"  ⚠️  Consider: RECORDING_SILENCE_THRESHOLD={int(rms * 0.4)}")
        recommended_amp = 1.0

    # Test with recommended amplification
    print("\n" + "=" * 70)
    print(f"  TESTING WITH AMPLIFICATION = {recommended_amp:.1f}")
    print("=" * 70)

    amplified = audio.astype(np.float32) * recommended_amp
    amplified = np.clip(amplified, -32768, 32767).astype(np.int16)

    amp_rms = np.sqrt(np.mean(amplified.astype(np.float32) ** 2))
    amp_peak = np.max(np.abs(amplified))

    # Check if clipping
    clipping = np.sum(np.abs(amplified) >= 32767)
    clip_percent = (clipping / total_samples) * 100

    print(f"\nWith {recommended_amp:.1f}x amplification:")
    print(f"  RMS Level:          {amp_rms:.1f}")
    print(f"  Peak Level:         {amp_peak}")
    print(f"  Clipping samples:   {clipping} ({clip_percent:.2f}%)")

    if clip_percent > 1.0:
        print(f"  ⚠️  WARNING: Too much clipping!")
        print(f"  Reduce amplification to {recommended_amp * 0.7:.1f}")
        recommended_amp = recommended_amp * 0.7

    # Final recommendations
    print("\n" + "=" * 70)
    print("  FINAL RECOMMENDATIONS")
    print("=" * 70)

    print(f"\nEdit your .env file with these values:")
    print(f"\n  AUDIO_INPUT_DEVICE={device_id}")
    print(f"  AUDIO_AMPLIFICATION={recommended_amp:.1f}")

    if rms > 5000:
        new_threshold = int(rms * 0.4)
        print(f"  RECORDING_SILENCE_THRESHOLD={new_threshold}")
        print(f"\n  Note: Your mic is loud, so silence threshold increased")
    else:
        print(f"  RECORDING_SILENCE_THRESHOLD=2000")

    print(f"\n  AUDIO_SAMPLE_RATE={sample_rate}")
    print(f"  WAKE_WORD_SIMILARITY=0.6")

    # Status check
    print("\n📋 STATUS CHECK:")

    if amp_rms < 1500:
        print("  ❌ Still too quiet - increase amplification more")
    elif amp_rms < 2000:
        print("  ⚠️  Borderline - may have issues detecting silence")
    elif amp_rms < 10000:
        print("  ✅ Good level for speech detection")
    elif amp_rms < 25000:
        print("  ✅ Excellent level")
    elif amp_rms < 32000:
        print("  ⚠️  High but acceptable")
    else:
        print("  ❌ Too loud - will clip!")

    if clip_percent > 5.0:
        print("  ❌ Excessive clipping detected")
    elif clip_percent > 1.0:
        print("  ⚠️  Some clipping (reduce amplification)")
    else:
        print("  ✅ No significant clipping")

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"\n  Microphone Type: {mic_type}")
    print(f"  Raw RMS: {rms:.1f}")
    print(f"  Amplified RMS: {amp_rms:.1f}")
    print(f"  Recommended Amplification: {recommended_amp:.1f}x")

    if 2000 <= amp_rms <= 25000 and clip_percent < 1.0:
        print("\n  ✅ Configuration should work well!")
    else:
        print("\n  ⚠️  May need adjustment - use recommended values above")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
