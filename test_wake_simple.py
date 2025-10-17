#!/usr/bin/env python3
"""
Simple Wake Word Test - Direct ALSA, No PipeWire
Tests wake word detection with optimized settings for USB devices
"""
import asyncio
import logging
import json
import queue
import os

# Disable PipeWire/PulseAudio - use ALSA directly
os.environ['SDL_AUDIODRIVER'] = 'alsa'

import sounddevice as sd
from vosk import Model, KaldiRecognizer
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Force ALSA backend
sd.default.hostapi = 0  # ALSA

# Configuration
SAMPLE_RATE = 48000  # Your USB device's native rate
WAKE_WORD = "max"
MODEL_PATH = "./models/vosk-model-small-en-us-0.15"
USB_DEVICE_INDEX = 2  # From arecord -l output

class SimpleWakeWordDetector:
    """Simplified wake word detector with better buffering"""

    def __init__(self):
        logger.info(f"Initializing detector: {SAMPLE_RATE}Hz, device index {USB_DEVICE_INDEX}")

        # Load Vosk model
        if not Path(MODEL_PATH).exists():
            raise FileNotFoundError(f"Vosk model not found at {MODEL_PATH}")

        logger.info(f"Loading Vosk model from {MODEL_PATH}...")
        self.model = Model(MODEL_PATH)
        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        self.recognizer.SetWords(True)
        logger.info("Vosk model loaded")

        self.audio_queue = queue.Queue(maxsize=10)  # Limit queue size
        self.is_running = False

    def audio_callback(self, indata, frames, time, status):
        """Audio input callback"""
        if status:
            # Only log overflow errors, not every status
            if 'overflow' in str(status).lower():
                logger.warning(f"Buffer overflow! Dropping {frames} frames")

        # Non-blocking put - drop frames if queue full
        try:
            self.audio_queue.put_nowait(bytes(indata))
        except queue.Full:
            logger.warning("Queue full, dropping audio frame")

    async def listen(self):
        """Listen for wake word"""
        logger.info("=" * 60)
        logger.info(f"Listening for wake word: '{WAKE_WORD}'")
        logger.info(f"Speak clearly into your USB microphone...")
        logger.info("=" * 60)

        self.is_running = True

        # Calculate buffer size: 1 second of audio
        blocksize = SAMPLE_RATE  # 1 second blocks

        logger.info(f"Opening audio stream:")
        logger.info(f"  Device: {USB_DEVICE_INDEX} (USB PnP Sound Device)")
        logger.info(f"  Sample rate: {SAMPLE_RATE}Hz")
        logger.info(f"  Block size: {blocksize} samples ({blocksize/SAMPLE_RATE}s)")
        logger.info(f"  Backend: ALSA (direct)")

        try:
            # Open stream with ALSA directly
            stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=blocksize,
                device=USB_DEVICE_INDEX,
                channels=1,
                dtype='int16',
                callback=self.audio_callback,
                latency='high'  # Request larger buffers
            )

            with stream:
                logger.info("✓ Stream opened successfully")
                logger.info("")
                logger.info("Waiting for wake word...")
                logger.info("")

                detection_count = 0
                frames_processed = 0

                while self.is_running and detection_count < 3:
                    try:
                        # Get audio data
                        data = self.audio_queue.get(timeout=0.1)
                        frames_processed += 1

                        # Process with Vosk
                        if self.recognizer.AcceptWaveform(data):
                            result = json.loads(self.recognizer.Result())
                            text = result.get('text', '').lower()

                            if text:
                                logger.info(f"Recognized: '{text}'")

                                # Check for wake word
                                if WAKE_WORD in text:
                                    detection_count += 1
                                    logger.info("")
                                    logger.info("!" * 60)
                                    logger.info(f"✓✓✓ WAKE WORD DETECTED! (#{detection_count}) ✓✓✓")
                                    logger.info("!" * 60)
                                    logger.info("")

                                    if detection_count < 3:
                                        logger.info(f"Say '{WAKE_WORD}' again to test multiple detections...")
                                        logger.info("")
                        else:
                            # Partial result
                            partial = json.loads(self.recognizer.PartialResult())
                            partial_text = partial.get('partial', '').lower()

                            if partial_text:
                                # Show partial results to help debugging
                                print(f"\r  Partial: {partial_text[:40]:<40}", end='', flush=True)

                        # Progress indicator
                        if frames_processed % 10 == 0:
                            logger.debug(f"Processed {frames_processed} audio blocks")

                    except queue.Empty:
                        await asyncio.sleep(0.01)
                        continue
                    except KeyboardInterrupt:
                        logger.info("\nInterrupted by user")
                        break

                logger.info("")
                logger.info("=" * 60)
                logger.info(f"Test complete! Detections: {detection_count}")
                logger.info("=" * 60)

                return detection_count > 0

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            return False
        finally:
            self.is_running = False

async def main():
    """Main test function"""
    print()
    print("=" * 60)
    print("  SIMPLE WAKE WORD TEST")
    print("  Direct ALSA Access (Bypass PipeWire)")
    print("=" * 60)
    print()

    # Show device info
    logger.info("USB Audio Device Info:")
    try:
        device_info = sd.query_devices(USB_DEVICE_INDEX)
        logger.info(f"  Name: {device_info['name']}")
        logger.info(f"  Sample rate: {int(device_info['default_samplerate'])}Hz")
        logger.info(f"  Input channels: {device_info['max_input_channels']}")
        logger.info(f"  Host API: {sd.query_hostapis(device_info['hostapi'])['name']}")
    except Exception as e:
        logger.error(f"Could not query device: {e}")

    print()

    # Test 1: Record and check volume
    logger.info("Step 1: Testing microphone volume...")
    logger.info("Speak loudly into your microphone for 2 seconds...")

    try:
        import numpy as np

        recording = sd.rec(
            int(2 * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='int16',
            device=USB_DEVICE_INDEX
        )
        sd.wait()

        rms = np.sqrt(np.mean(recording ** 2))
        peak = np.max(np.abs(recording))

        logger.info(f"  RMS level: {rms:.0f}")
        logger.info(f"  Peak level: {peak:.0f}")

        if rms < 500:
            logger.warning("⚠ Volume is LOW! Try:")
            logger.warning("  1. Speak louder and closer to mic")
            logger.warning("  2. Check USB connection")
            logger.warning("  3. Run: alsamixer -c 2 (adjust Mic volume)")
        elif rms > 15000:
            logger.warning("⚠ Volume is TOO HIGH! May clip. Reduce mic gain.")
        else:
            logger.info("✓ Volume looks good!")

        print()

    except Exception as e:
        logger.error(f"Volume test failed: {e}")
        print()

    # Test 2: Wake word detection
    input("Press Enter to start wake word test (will run for 30s or 3 detections)...")
    print()

    detector = SimpleWakeWordDetector()

    # Run with timeout
    try:
        success = await asyncio.wait_for(detector.listen(), timeout=30)

        if success:
            logger.info("✓✓✓ TEST PASSED! Wake word detection working!")
        else:
            logger.warning("✗ TEST TIMEOUT - No wake word detected in 30 seconds")
            logger.warning("")
            logger.warning("Troubleshooting:")
            logger.warning(f"  1. Say the exact word: '{WAKE_WORD}'")
            logger.warning("  2. Speak clearly and loudly")
            logger.warning("  3. Check microphone volume (see Step 1)")
            logger.warning("  4. Try different words: 'computer', 'alexa', 'jarvis'")

    except asyncio.TimeoutError:
        logger.warning("✗ TEST TIMEOUT - No wake word detected in 30 seconds")
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")

    print()
    logger.info("Test complete!")
    print()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest cancelled")
