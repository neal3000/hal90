#!/usr/bin/env python3
"""
Test Wake Word Detection and Audio Recording
Tests the complete pipeline: Wake Word -> Recording -> Transcription
"""
import asyncio
import logging
import sys
import sounddevice as sd
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Import our modules
from config import get_config
from wake_word_detector import WakeWordDetector
from audio_recorder import AudioRecorder
from whisper_service import WhisperService

# ANSI color codes for better visibility
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_color(message, color=Colors.OKGREEN):
    """Print colored message"""
    print(f"{color}{message}{Colors.ENDC}")

def print_header(message):
    """Print header"""
    print()
    print("=" * 80)
    print_color(message, Colors.HEADER + Colors.BOLD)
    print("=" * 80)
    print()

def find_usb_audio_device():
    """Find USB PnP Sound Device and detect supported sample rate"""
    print_header("FINDING USB AUDIO DEVICE")

    devices = sd.query_devices()
    logger.info(f"Found {len(devices)} audio devices")

    print("\nAvailable audio devices:")
    for idx, device in enumerate(devices):
        is_input = device['max_input_channels'] > 0
        is_output = device['max_output_channels'] > 0

        device_type = []
        if is_input:
            device_type.append("INPUT")
        if is_output:
            device_type.append("OUTPUT")

        marker = ""
        if "USB" in device['name'] and is_input:
            marker = " ← USB INPUT DEVICE"
            print_color(f"  [{idx}] {device['name']} ({', '.join(device_type)}){marker}", Colors.OKGREEN)
        else:
            print(f"  [{idx}] {device['name']} ({', '.join(device_type)}){marker}")

    # Find USB device
    usb_device_index = None
    usb_device = None
    for idx, device in enumerate(devices):
        if "USB" in device['name'] and device['max_input_channels'] > 0:
            usb_device_index = idx
            usb_device = device
            print_color(f"\n✓ Found USB audio device at index {idx}: {device['name']}", Colors.OKGREEN)
            break

    if usb_device_index is None:
        print_color("✗ No USB audio device found!", Colors.FAIL)
        print("\nPlease check:")
        print("  1. USB microphone is plugged in")
        print("  2. Device is recognized by the system (try: arecord -l)")
        sys.exit(1)

    # Detect supported sample rate
    print("\nDetecting supported sample rate...")
    supported_rate = None
    test_rates = [16000, 44100, 48000, 22050, 8000]

    for rate in test_rates:
        try:
            # Try to query if this rate is supported
            sd.check_input_settings(device=usb_device_index, channels=1, samplerate=rate)
            supported_rate = rate
            print_color(f"  ✓ {rate}Hz - SUPPORTED", Colors.OKGREEN)
            if supported_rate is None:
                supported_rate = rate
            break
        except Exception as e:
            print(f"  ✗ {rate}Hz - Not supported")

    if supported_rate is None:
        # Fallback to device's default sample rate
        supported_rate = int(usb_device['default_samplerate'])
        print_color(f"  Using device default: {supported_rate}Hz", Colors.WARNING)

    print()
    print_color(f"Selected sample rate: {supported_rate}Hz", Colors.OKGREEN + Colors.BOLD)

    return usb_device_index, usb_device['name'], supported_rate

def test_microphone(device_index, samplerate):
    """Test microphone input"""
    print_header("TESTING MICROPHONE")

    print(f"Recording 3 seconds from device {device_index} at {samplerate}Hz...")
    print_color("Speak into your microphone now!", Colors.OKCYAN)

    try:
        # Record 3 seconds
        duration = 3

        recording = sd.rec(
            int(duration * samplerate),
            samplerate=samplerate,
            channels=1,
            dtype='int16',
            device=device_index
        )
        sd.wait()

        # Calculate volume
        import numpy as np
        rms = np.sqrt(np.mean(recording ** 2))

        print(f"\nRecording complete!")
        print(f"  Samples: {len(recording)}")
        print(f"  RMS (volume): {rms:.0f}")

        if rms < 100:
            print_color("  ⚠ Warning: Very low volume detected. Check microphone.", Colors.WARNING)
        elif rms > 10000:
            print_color("  ⚠ Warning: Very high volume detected. Might be clipping.", Colors.WARNING)
        else:
            print_color("  ✓ Volume looks good!", Colors.OKGREEN)

        return True

    except Exception as e:
        print_color(f"✗ Microphone test failed: {e}", Colors.FAIL)
        logger.error(f"Microphone test error: {e}", exc_info=True)
        return False

async def test_wake_word_detection(device_index, samplerate):
    """Test wake word detection"""
    print_header("TESTING WAKE WORD DETECTION")

    # Load config
    config = get_config()

    # Check if Vosk model exists
    model_path = Path(config.WAKE_WORD_MODEL_PATH)
    if not model_path.exists():
        print_color(f"✗ Vosk model not found at: {model_path}", Colors.FAIL)
        print("\nTo download the model:")
        print("  mkdir -p models")
        print("  cd models")
        print("  wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
        print("  unzip vosk-model-small-en-us-0.15.zip")
        return False

    print_color(f"✓ Vosk model found: {model_path}", Colors.OKGREEN)

    try:
        # Initialize wake word detector
        print(f"\nInitializing wake word detector...")
        print(f"  Wake word: '{config.WAKE_WORD}'")
        print(f"  Sample rate: {samplerate}Hz")

        detector = WakeWordDetector(
            model_path=str(model_path),
            wake_word=config.WAKE_WORD,
            sample_rate=samplerate
        )

        print_color("✓ Wake word detector initialized", Colors.OKGREEN)

        # Test detection
        print(f"\nListening for wake word '{config.WAKE_WORD}'...")
        print_color(f"Say '{config.WAKE_WORD}' into your microphone!", Colors.OKCYAN + Colors.BOLD)
        print("(Will timeout after 30 seconds)")

        detected = asyncio.Event()
        detection_count = [0]

        async def on_wake_word():
            detection_count[0] += 1
            print()
            print_color("!" * 80, Colors.OKGREEN + Colors.BOLD)
            print_color(f"  WAKE WORD DETECTED! (#{detection_count[0]})", Colors.OKGREEN + Colors.BOLD)
            print_color("!" * 80, Colors.OKGREEN + Colors.BOLD)
            print()

            if detection_count[0] >= 2:
                print_color("✓ Multiple detections successful! Stopping test.", Colors.OKGREEN)
                detected.set()

        # Start listening
        listen_task = asyncio.create_task(detector.listen(on_wake_word))

        # Wait for detection or timeout
        try:
            await asyncio.wait_for(detected.wait(), timeout=30)
            print_color("\n✓ Wake word detection test PASSED!", Colors.OKGREEN + Colors.BOLD)
            result = True
        except asyncio.TimeoutError:
            print_color("\n✗ Wake word detection test TIMEOUT", Colors.WARNING)
            print(f"Did not detect wake word '{config.WAKE_WORD}' in 30 seconds")
            print("\nTroubleshooting:")
            print("  1. Speak clearly and loudly")
            print("  2. Say the exact word:", config.WAKE_WORD)
            print("  3. Check microphone is working (see test above)")
            print("  4. Try a different wake word in .env")
            result = False

        # Stop detector
        await detector.stop()
        listen_task.cancel()
        try:
            await listen_task
        except asyncio.CancelledError:
            pass

        return result

    except Exception as e:
        print_color(f"✗ Wake word detection test failed: {e}", Colors.FAIL)
        logger.error(f"Wake word test error: {e}", exc_info=True)
        return False

async def test_audio_recording(samplerate):
    """Test audio recording with silence detection"""
    print_header("TESTING AUDIO RECORDING")

    config = get_config()

    try:
        # Initialize recorder
        print("Initializing audio recorder...")
        print(f"  Sample rate: {samplerate}Hz")
        print(f"  Silence threshold: {config.RECORDING_SILENCE_THRESHOLD}")
        print(f"  Silence duration: {config.RECORDING_SILENCE_DURATION}s")
        print(f"  Max duration: {config.RECORDING_MAX_DURATION}s")

        recorder = AudioRecorder(
            sample_rate=samplerate,
            channels=config.AUDIO_CHANNELS,
            chunk_size=config.AUDIO_CHUNK_SIZE,
            silence_threshold=config.RECORDING_SILENCE_THRESHOLD,
            silence_duration=config.RECORDING_SILENCE_DURATION,
            max_duration=config.RECORDING_MAX_DURATION,
            recordings_dir=config.RECORDINGS_DIR
        )

        print_color("✓ Audio recorder initialized", Colors.OKGREEN)

        # Record
        print(f"\nStarting recording...")
        print_color("Speak something, then be quiet for 1.5 seconds...", Colors.OKCYAN + Colors.BOLD)

        audio_file = await recorder.record()

        if audio_file:
            print()
            print_color(f"✓ Recording saved: {audio_file}", Colors.OKGREEN)

            # Get recording info
            info = recorder.get_last_recording_info()
            print(f"  Duration: {info['duration_seconds']:.2f}s")
            print(f"  Chunks: {info['chunks']}")
            print(f"  Samples: {info['total_samples']}")

            return audio_file
        else:
            print_color("✗ Recording failed - no file returned", Colors.FAIL)
            return None

    except Exception as e:
        print_color(f"✗ Audio recording test failed: {e}", Colors.FAIL)
        logger.error(f"Recording test error: {e}", exc_info=True)
        return None

async def test_transcription(audio_file):
    """Test Whisper transcription"""
    print_header("TESTING TRANSCRIPTION")

    if not audio_file:
        print_color("✗ No audio file to transcribe", Colors.FAIL)
        return False

    config = get_config()

    try:
        # Initialize Whisper
        print("Initializing Whisper service...")
        print(f"  Model: {config.WHISPER_MODEL}")
        print(f"  Device: {config.WHISPER_DEVICE}")
        print(f"  Compute type: {config.WHISPER_COMPUTE_TYPE}")

        whisper = WhisperService(
            model_name=config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE
        )

        print_color("✓ Whisper service initialized", Colors.OKGREEN)

        # Transcribe
        print(f"\nTranscribing {audio_file}...")
        print("(This may take a few seconds...)")

        text = await whisper.transcribe(str(audio_file))

        if text:
            print()
            print_color("✓ Transcription successful!", Colors.OKGREEN + Colors.BOLD)
            print()
            print("  Transcribed text:")
            print_color(f"  \"{text}\"", Colors.OKCYAN + Colors.BOLD)
            print()
            return True
        else:
            print_color("✗ Transcription failed - no text returned", Colors.FAIL)
            return False

    except Exception as e:
        print_color(f"✗ Transcription test failed: {e}", Colors.FAIL)
        logger.error(f"Transcription test error: {e}", exc_info=True)
        return False

async def test_complete_pipeline(device_index, samplerate):
    """Test complete wake word -> record -> transcribe pipeline"""
    print_header("TESTING COMPLETE PIPELINE")

    config = get_config()
    model_path = Path(config.WAKE_WORD_MODEL_PATH)

    if not model_path.exists():
        print_color("✗ Cannot test pipeline: Vosk model not found", Colors.FAIL)
        return False

    try:
        # Initialize all components
        print("Initializing components...")

        detector = WakeWordDetector(
            model_path=str(model_path),
            wake_word=config.WAKE_WORD,
            sample_rate=samplerate
        )

        recorder = AudioRecorder(
            sample_rate=samplerate,
            channels=config.AUDIO_CHANNELS,
            chunk_size=config.AUDIO_CHUNK_SIZE,
            silence_threshold=config.RECORDING_SILENCE_THRESHOLD,
            silence_duration=config.RECORDING_SILENCE_DURATION,
            max_duration=config.RECORDING_MAX_DURATION,
            recordings_dir=config.RECORDINGS_DIR
        )

        whisper = WhisperService(
            model_name=config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE
        )

        print_color("✓ All components initialized", Colors.OKGREEN)

        # Pipeline test
        print(f"\n{'=' * 80}")
        print_color("PIPELINE TEST - Say wake word, then speak a sentence", Colors.HEADER + Colors.BOLD)
        print(f"{'=' * 80}\n")

        print(f"Step 1: Say '{config.WAKE_WORD}'")
        print("(Listening for 30 seconds...)")

        detected = asyncio.Event()
        audio_file = None

        async def on_wake_word():
            print()
            print_color("!" * 80, Colors.OKGREEN + Colors.BOLD)
            print_color("  WAKE WORD DETECTED!", Colors.OKGREEN + Colors.BOLD)
            print_color("!" * 80, Colors.OKGREEN + Colors.BOLD)
            print()

            # Stop listening
            await detector.stop()

            # Start recording
            print("Step 2: Speak now (will stop on silence)...")
            print_color("Say something, then be quiet...", Colors.OKCYAN + Colors.BOLD)

            nonlocal audio_file
            audio_file = await recorder.record()

            if audio_file:
                print()
                print_color(f"✓ Recorded: {audio_file}", Colors.OKGREEN)

                # Transcribe
                print("\nStep 3: Transcribing...")
                text = await whisper.transcribe(str(audio_file))

                if text:
                    print()
                    print_color("=" * 80, Colors.OKGREEN + Colors.BOLD)
                    print_color("  PIPELINE TEST SUCCESSFUL!", Colors.OKGREEN + Colors.BOLD)
                    print_color("=" * 80, Colors.OKGREEN + Colors.BOLD)
                    print()
                    print("  You said:")
                    print_color(f"  \"{text}\"", Colors.OKCYAN + Colors.BOLD)
                    print()
                else:
                    print_color("✗ Transcription failed", Colors.FAIL)
            else:
                print_color("✗ Recording failed", Colors.FAIL)

            detected.set()

        # Start listening
        listen_task = asyncio.create_task(detector.listen(on_wake_word))

        try:
            await asyncio.wait_for(detected.wait(), timeout=30)
            result = True
        except asyncio.TimeoutError:
            print_color("\n✗ Pipeline test TIMEOUT - wake word not detected", Colors.WARNING)
            result = False

        # Cleanup
        await detector.stop()
        listen_task.cancel()
        try:
            await listen_task
        except asyncio.CancelledError:
            pass

        return result

    except Exception as e:
        print_color(f"✗ Pipeline test failed: {e}", Colors.FAIL)
        logger.error(f"Pipeline test error: {e}", exc_info=True)
        return False

async def main():
    """Main test function"""
    print()
    print_color("=" * 80, Colors.HEADER + Colors.BOLD)
    print_color("  WAKE WORD & RECORDING TEST SUITE", Colors.HEADER + Colors.BOLD)
    print_color("=" * 80, Colors.HEADER + Colors.BOLD)
    print()

    # Find USB device and detect sample rate
    device_index, device_name, samplerate = find_usb_audio_device()

    # Set default input device for sounddevice
    sd.default.device = device_index
    print(f"\nSet default input device to: {device_index}")
    print_color(f"Using sample rate: {samplerate}Hz", Colors.OKGREEN)

    # Update config with detected sample rate
    config = get_config()
    if samplerate != config.AUDIO_SAMPLE_RATE:
        print()
        print_color(f"⚠ Note: Your .env uses {config.AUDIO_SAMPLE_RATE}Hz but device supports {samplerate}Hz", Colors.WARNING)
        print(f"  Update your .env file: AUDIO_SAMPLE_RATE={samplerate}")
        print()

    # Test 1: Microphone
    input("\nPress Enter to test microphone...")
    if not test_microphone(device_index, samplerate):
        print_color("\n✗ Microphone test failed. Cannot continue.", Colors.FAIL)
        return

    # Test 2: Wake word detection
    input("\nPress Enter to test wake word detection...")
    wake_result = await test_wake_word_detection(device_index, samplerate)

    # Test 3: Audio recording
    input("\nPress Enter to test audio recording...")
    audio_file = await test_audio_recording(samplerate)

    # Test 4: Transcription (if we have audio file)
    if audio_file:
        input("\nPress Enter to test transcription...")
        await test_transcription(audio_file)

    # Test 5: Complete pipeline
    if wake_result:
        input("\nPress Enter to test COMPLETE PIPELINE (wake -> record -> transcribe)...")
        await test_complete_pipeline(device_index, samplerate)

    print()
    print_header("TEST SUITE COMPLETE")

    # Show final recommendation
    if samplerate != 16000:
        print()
        print_color("RECOMMENDATION:", Colors.WARNING + Colors.BOLD)
        print(f"Your USB device works best at {samplerate}Hz.")
        print(f"Update your voice-kiosk/.env file:")
        print_color(f"  AUDIO_SAMPLE_RATE={samplerate}", Colors.OKCYAN + Colors.BOLD)
        print()
    print()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print_color("\nTest interrupted by user", Colors.WARNING)
    except Exception as e:
        print()
        print_color(f"\nTest suite error: {e}", Colors.FAIL)
        logger.error("Test suite error", exc_info=True)
