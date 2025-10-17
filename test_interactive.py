#!/usr/bin/env python3
"""
Interactive Test Suite for Voice Kiosk
Tests microphone, wake word detection, and speech-to-text with user interaction
"""
import asyncio
import sys
import time
import logging
from pathlib import Path
import numpy as np
import sounddevice as sd
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Import our modules
from config import get_config
from whisper_service import WhisperService
from wake_word_detector_improved import WakeWordDetectorImproved
from audio_recorder import AudioRecorder

class InteractiveTests:
    """Interactive test suite for voice kiosk hardware"""

    def __init__(self):
        self.config = get_config()
        self.test_results = {}

    def print_header(self, title):
        """Print a formatted test header"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)

    def print_result(self, test_name, passed, message=""):
        """Print test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results[test_name] = passed
        print(f"\n{status}: {test_name}")
        if message:
            print(f"  {message}")

    def get_user_confirmation(self, prompt):
        """Get yes/no confirmation from user"""
        while True:
            response = input(f"{prompt} (y/n): ").lower().strip()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print("Please answer 'y' or 'n'")

    # ========================================================================
    # Test 1: Audio Device Detection
    # ========================================================================
    def test_audio_device_detection(self):
        """Test 1: Detect and list available audio devices"""
        self.print_header("Test 1: Audio Device Detection")

        try:
            devices = sd.query_devices()
            input_devices = []

            print("\nAvailable audio devices:")
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_devices.append(i)
                    marker = " ← CONFIGURED" if i == self.config.AUDIO_INPUT_DEVICE else ""
                    print(f"  [{i}] {device['name']}")
                    print(f"      Input channels: {device['max_input_channels']}")
                    print(f"      Sample rate: {device['default_samplerate']}Hz{marker}")

            if not input_devices:
                self.print_result("Audio Device Detection", False,
                                "No input devices found!")
                return False

            configured_device = self.config.AUDIO_INPUT_DEVICE
            if configured_device not in input_devices:
                self.print_result("Audio Device Detection", False,
                                f"Configured device {configured_device} not found!")
                return False

            self.print_result("Audio Device Detection", True,
                            f"Found {len(input_devices)} input device(s), configured device is available")
            return True

        except Exception as e:
            self.print_result("Audio Device Detection", False, str(e))
            return False

    # ========================================================================
    # Test 2: Microphone Gain Calibration
    # ========================================================================
    def test_microphone_gain(self):
        """Test 2: Microphone gain calibration - measure RMS levels"""
        self.print_header("Test 2: Microphone Gain Calibration")

        print("\nThis test will measure your microphone input levels.")
        print(f"Target RMS level: 2000-30000 (configured threshold: {self.config.RECORDING_SILENCE_THRESHOLD})")
        print(f"Current amplification: {self.config.AUDIO_AMPLIFICATION}x")
        print("\nWhen prompted, speak normally for 5 seconds.")

        input("\nPress Enter to start recording...")

        try:
            duration = 5
            sample_rate = self.config.AUDIO_SAMPLE_RATE
            device = self.config.AUDIO_INPUT_DEVICE

            print(f"\n🎤 Recording for {duration} seconds - SPEAK NOW!")

            # Record audio
            recording = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                device=device,
                dtype='int16'
            )
            sd.wait()

            print("✓ Recording complete. Analyzing...")

            # Calculate RMS levels
            audio_data = recording.flatten()

            # Apply amplification like wake word detector does
            amplified = audio_data.astype(np.float32) * self.config.AUDIO_AMPLIFICATION
            amplified = np.clip(amplified, -32768, 32767).astype(np.int16)

            # Calculate statistics
            raw_rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            amplified_rms = np.sqrt(np.mean(amplified.astype(np.float32) ** 2))
            raw_max = np.max(np.abs(audio_data))
            amplified_max = np.max(np.abs(amplified))

            print("\n📊 Audio Level Analysis:")
            print(f"  Raw audio RMS:        {raw_rms:.1f}")
            print(f"  Raw audio peak:       {raw_max}")
            print(f"  Amplified RMS:        {amplified_rms:.1f}")
            print(f"  Amplified peak:       {amplified_max}")
            print(f"  Amplification factor: {self.config.AUDIO_AMPLIFICATION}x")
            print(f"  Silence threshold:    {self.config.RECORDING_SILENCE_THRESHOLD}")

            # Determine if levels are good
            threshold = self.config.RECORDING_SILENCE_THRESHOLD
            target_min = threshold
            target_max = 30000

            if amplified_rms < threshold / 2:
                status = "❌ TOO LOW - Increase amplification"
                passed = False
            elif amplified_rms < threshold:
                status = "⚠️  LOW - May have issues detecting speech"
                passed = False
            elif amplified_rms > target_max:
                status = "⚠️  TOO HIGH - May clip, decrease amplification"
                passed = True  # Still functional
            elif amplified_rms > target_max / 2:
                status = "⚠️  HIGH - Consider decreasing amplification"
                passed = True
            else:
                status = "✅ GOOD - Levels are optimal"
                passed = True

            print(f"\n  Status: {status}")

            if not passed or amplified_rms < threshold:
                print("\n💡 Recommendation:")
                if amplified_rms < threshold / 2:
                    new_amp = (threshold * 1.5 / raw_rms) if raw_rms > 0 else self.config.AUDIO_AMPLIFICATION * 2
                    print(f"  Try setting AUDIO_AMPLIFICATION={new_amp:.1f} in .env file")
                elif amplified_rms > target_max:
                    new_amp = (target_max * 0.8 / raw_rms) if raw_rms > 0 else self.config.AUDIO_AMPLIFICATION * 0.5
                    print(f"  Try setting AUDIO_AMPLIFICATION={new_amp:.1f} in .env file")

            self.print_result("Microphone Gain Calibration", passed,
                            f"Amplified RMS: {amplified_rms:.1f}")
            return passed

        except Exception as e:
            self.print_result("Microphone Gain Calibration", False, str(e))
            return False

    # ========================================================================
    # Test 3: Wake Word Detection
    # ========================================================================
    async def test_wake_word_detection(self):
        """Test 3: Wake word detection - test if detector recognizes wake word"""
        self.print_header("Test 3: Wake Word Detection")

        print(f"\nWake word: '{self.config.WAKE_WORD}'")
        print(f"Similarity threshold: {self.config.WAKE_WORD_SIMILARITY}")
        print(f"Amplification: {self.config.AUDIO_AMPLIFICATION}x")

        print(f"\nYou will have 15 seconds to say the wake word '{self.config.WAKE_WORD}'")
        print("The test will detect if it's recognized.")

        input("\nPress Enter to start wake word detection...")

        try:
            # Initialize wake word detector
            detector = WakeWordDetectorImproved(
                model_path=self.config.WAKE_WORD_MODEL_PATH,
                wake_word=self.config.WAKE_WORD,
                sample_rate=self.config.AUDIO_SAMPLE_RATE,
                amplification=self.config.AUDIO_AMPLIFICATION,
                similarity_threshold=self.config.WAKE_WORD_SIMILARITY,
                audio_device=self.config.AUDIO_INPUT_DEVICE
            )

            detected = False
            detection_text = ""

            async def on_wake_word():
                nonlocal detected, detection_text
                detected = True
                detection_text = "Wake word detected!"

            print(f"\n🎤 Listening for '{self.config.WAKE_WORD}'... (15 seconds)")
            print(f"   Say: '{self.config.WAKE_WORD}'\n")

            # Start listening
            listen_task = asyncio.create_task(detector.listen(on_wake_word))

            # Wait for detection or timeout
            try:
                await asyncio.wait_for(asyncio.sleep(15), timeout=15)
            except asyncio.TimeoutError:
                pass

            # Stop detector
            await detector.stop()
            await asyncio.sleep(0.5)

            try:
                listen_task.cancel()
                await listen_task
            except asyncio.CancelledError:
                pass

            if detected:
                self.print_result("Wake Word Detection", True,
                                f"Successfully detected '{self.config.WAKE_WORD}'")
            else:
                print("\n⏱️  Time's up!")
                user_said_it = self.get_user_confirmation(
                    f"Did you say '{self.config.WAKE_WORD}' clearly?"
                )

                if user_said_it:
                    self.print_result("Wake Word Detection", False,
                                    "Wake word not detected - check gain levels or similarity threshold")
                    print("\n💡 Try:")
                    print("  1. Reduce WAKE_WORD_SIMILARITY (currently {:.1f}) to 0.5 or 0.4".format(
                        self.config.WAKE_WORD_SIMILARITY))
                    print("  2. Check microphone gain from Test 2")
                else:
                    self.print_result("Wake Word Detection", None,
                                    "Test inconclusive - user didn't speak")

            return detected

        except Exception as e:
            self.print_result("Wake Word Detection", False, str(e))
            return False

    # ========================================================================
    # Test 4: Audio Recording
    # ========================================================================
    async def test_audio_recording(self):
        """Test 4: Audio recording with silence detection"""
        self.print_header("Test 4: Audio Recording with Silence Detection")

        print("\nThis test records audio until you stop speaking (silence detection).")
        print(f"Silence threshold: {self.config.RECORDING_SILENCE_THRESHOLD} RMS")
        print(f"Silence duration: {self.config.RECORDING_SILENCE_DURATION}s")
        print(f"Max recording: {self.config.RECORDING_MAX_DURATION}s")

        print("\nWhen prompted, speak a sentence and then remain silent.")

        input("\nPress Enter to start recording...")

        try:
            # Initialize audio recorder
            recorder = AudioRecorder(
                sample_rate=self.config.AUDIO_SAMPLE_RATE,
                channels=self.config.AUDIO_CHANNELS,
                chunk_size=self.config.AUDIO_CHUNK_SIZE,
                silence_threshold=self.config.RECORDING_SILENCE_THRESHOLD,
                silence_duration=self.config.RECORDING_SILENCE_DURATION,
                max_duration=self.config.RECORDING_MAX_DURATION,
                audio_device=self.config.AUDIO_INPUT_DEVICE,
                amplification=self.config.AUDIO_AMPLIFICATION,
                recordings_dir=self.config.RECORDINGS_DIR
            )

            print("\n🎤 Recording - SPEAK NOW!")
            print("   (Recording will stop when you're silent)\n")

            start_time = time.time()
            audio_file = await recorder.record()
            duration = time.time() - start_time

            if audio_file and audio_file.exists():
                file_size = audio_file.stat().st_size
                print(f"\n✓ Recording saved: {audio_file}")
                print(f"  Duration: {duration:.1f}s")
                print(f"  File size: {file_size:,} bytes")

                # Check if reasonable
                if duration < 0.5:
                    self.print_result("Audio Recording", False,
                                    "Recording too short - check microphone levels")
                    return False
                elif duration >= self.config.RECORDING_MAX_DURATION - 0.5:
                    print("  ⚠️  Warning: Hit maximum duration (may have been cut off)")

                did_speak = self.get_user_confirmation("Did you speak a full sentence?")

                if did_speak:
                    self.print_result("Audio Recording", True,
                                    f"Recorded {duration:.1f}s successfully")
                    return True
                else:
                    self.print_result("Audio Recording", None,
                                    "Test inconclusive - user didn't speak")
                    return False
            else:
                self.print_result("Audio Recording", False, "No audio file created")
                return False

        except Exception as e:
            self.print_result("Audio Recording", False, str(e))
            return False

    # ========================================================================
    # Test 5: Speech-to-Text
    # ========================================================================
    async def test_speech_to_text(self):
        """Test 5: Speech-to-text transcription"""
        self.print_header("Test 5: Speech-to-Text Transcription")

        print("\nThis test will record your speech and transcribe it.")
        print(f"Whisper model: {self.config.WHISPER_MODEL}")

        test_phrase = "The quick brown fox jumps over the lazy dog"
        print(f"\nPlease say this phrase clearly:")
        print(f"  '{test_phrase}'")

        input("\nPress Enter when ready to record...")

        try:
            # Initialize recorder
            recorder = AudioRecorder(
                sample_rate=self.config.AUDIO_SAMPLE_RATE,
                channels=self.config.AUDIO_CHANNELS,
                chunk_size=self.config.AUDIO_CHUNK_SIZE,
                silence_threshold=self.config.RECORDING_SILENCE_THRESHOLD,
                silence_duration=self.config.RECORDING_SILENCE_DURATION,
                max_duration=self.config.RECORDING_MAX_DURATION,
                audio_device=self.config.AUDIO_INPUT_DEVICE,
                amplification=self.config.AUDIO_AMPLIFICATION,
                recordings_dir=self.config.RECORDINGS_DIR
            )

            print("\n🎤 Recording - SPEAK NOW!")
            audio_file = await recorder.record()

            if not audio_file or not audio_file.exists():
                self.print_result("Speech-to-Text", False, "Recording failed")
                return False

            print("✓ Recording complete")
            print("\n⏳ Transcribing... (this may take a few seconds)")

            # Initialize Whisper
            whisper = WhisperService(
                model_name=self.config.WHISPER_MODEL,
                device=self.config.WHISPER_DEVICE,
                compute_type=self.config.WHISPER_COMPUTE_TYPE
            )

            # Transcribe
            transcription = await whisper.transcribe(str(audio_file))

            print(f"\n📝 Transcription:")
            print(f"  '{transcription}'")

            if transcription:
                print(f"\n  Expected: '{test_phrase}'")

                # Calculate rough accuracy
                transcription_lower = transcription.lower().strip()
                phrase_lower = test_phrase.lower()

                # Check if most words match
                trans_words = set(transcription_lower.split())
                phrase_words = set(phrase_lower.split())

                if trans_words & phrase_words:
                    matches = len(trans_words & phrase_words)
                    total = len(phrase_words)
                    accuracy = (matches / total) * 100

                    print(f"  Match: {matches}/{total} words ({accuracy:.0f}%)")

                was_accurate = self.get_user_confirmation(
                    "Was the transcription accurate?"
                )

                self.print_result("Speech-to-Text", was_accurate,
                                f"Transcribed: '{transcription}'")
                return was_accurate
            else:
                self.print_result("Speech-to-Text", False,
                                "No transcription produced")
                return False

        except Exception as e:
            self.print_result("Speech-to-Text", False, str(e))
            return False

    # ========================================================================
    # Test 6: End-to-End Voice Pipeline
    # ========================================================================
    async def test_voice_pipeline(self):
        """Test 6: Complete voice pipeline (wake word → record → transcribe)"""
        self.print_header("Test 6: End-to-End Voice Pipeline")

        print("\nThis test simulates the complete voice interaction:")
        print(f"  1. Say wake word: '{self.config.WAKE_WORD}'")
        print(f"  2. System records your command")
        print(f"  3. System transcribes what you said")

        print(f"\nYou will have 20 seconds total.")

        input("\nPress Enter to start the pipeline test...")

        try:
            # Initialize components
            detector = WakeWordDetectorImproved(
                model_path=self.config.WAKE_WORD_MODEL_PATH,
                wake_word=self.config.WAKE_WORD,
                sample_rate=self.config.AUDIO_SAMPLE_RATE,
                amplification=self.config.AUDIO_AMPLIFICATION,
                similarity_threshold=self.config.WAKE_WORD_SIMILARITY,
                audio_device=self.config.AUDIO_INPUT_DEVICE
            )

            recorder = AudioRecorder(
                sample_rate=self.config.AUDIO_SAMPLE_RATE,
                channels=self.config.AUDIO_CHANNELS,
                chunk_size=self.config.AUDIO_CHUNK_SIZE,
                silence_threshold=self.config.RECORDING_SILENCE_THRESHOLD,
                silence_duration=self.config.RECORDING_SILENCE_DURATION,
                max_duration=self.config.RECORDING_MAX_DURATION,
                audio_device=self.config.AUDIO_INPUT_DEVICE,
                amplification=self.config.AUDIO_AMPLIFICATION,
                recordings_dir=self.config.RECORDINGS_DIR
            )

            whisper = WhisperService(
                model_name=self.config.WHISPER_MODEL,
                device=self.config.WHISPER_DEVICE,
                compute_type=self.config.WHISPER_COMPUTE_TYPE
            )

            wake_detected = False
            audio_file = None
            transcription = None

            async def on_wake_word():
                nonlocal wake_detected
                wake_detected = True

            # Step 1: Wait for wake word
            print(f"\n🎤 Step 1: Listening for wake word '{self.config.WAKE_WORD}'...")

            listen_task = asyncio.create_task(detector.listen(on_wake_word))

            # Wait up to 10 seconds for wake word
            for i in range(10):
                if wake_detected:
                    break
                await asyncio.sleep(1)

            await detector.stop()

            try:
                listen_task.cancel()
                await listen_task
            except asyncio.CancelledError:
                pass

            if not wake_detected:
                self.print_result("End-to-End Pipeline", False,
                                "Wake word not detected")
                return False

            print("   ✓ Wake word detected!")

            # Brief delay to allow wake word to finish being spoken
            await asyncio.sleep(0.3)

            # Step 2: Record command
            print("\n🎤 Step 2: Recording your command...")
            print("   (Say something, then pause)")

            audio_file = await recorder.record()

            if not audio_file or not audio_file.exists():
                self.print_result("End-to-End Pipeline", False,
                                "Recording failed")
                return False

            print("   ✓ Recording complete")

            # Step 3: Transcribe
            print("\n⏳ Step 3: Transcribing...")

            transcription = await whisper.transcribe(str(audio_file))

            if transcription:
                print(f"   ✓ Transcription: '{transcription}'")

                worked = self.get_user_confirmation(
                    "Did the complete pipeline work correctly?"
                )

                self.print_result("End-to-End Pipeline", worked,
                                "All steps completed")
                return worked
            else:
                self.print_result("End-to-End Pipeline", False,
                                "Transcription failed")
                return False

        except Exception as e:
            self.print_result("End-to-End Pipeline", False, str(e))
            return False

    # ========================================================================
    # Main Test Runner
    # ========================================================================
    async def run_all_tests(self):
        """Run all interactive tests"""
        print("\n" + "=" * 70)
        print("  VOICE KIOSK - INTERACTIVE TEST SUITE")
        print("=" * 70)
        print("\nThese tests will verify your hardware setup:")
        print("  • Audio device detection")
        print("  • Microphone gain calibration")
        print("  • Wake word detection")
        print("  • Audio recording")
        print("  • Speech-to-text")
        print("  • End-to-end pipeline")
        print("\nMake sure you're in a quiet environment with your microphone ready.")

        input("\nPress Enter to begin tests...")

        # Run tests in order
        results = []

        # Test 1: Device detection (no user input needed)
        results.append(self.test_audio_device_detection())

        # Test 2: Microphone gain calibration
        results.append(self.test_microphone_gain())

        # Test 3: Wake word detection
        results.append(await self.test_wake_word_detection())

        # Test 4: Audio recording
        results.append(await self.test_audio_recording())

        # Test 5: Speech-to-text
        results.append(await self.test_speech_to_text())

        # Test 6: End-to-end pipeline
        run_pipeline = self.get_user_confirmation(
            "\nRun complete pipeline test?"
        )
        if run_pipeline:
            results.append(await self.test_voice_pipeline())

        # Print summary
        self.print_header("TEST SUMMARY")

        passed = sum(1 for r in results if r is True)
        failed = sum(1 for r in results if r is False)
        skipped = sum(1 for r in results if r is None)
        total = len(results)

        print(f"\nResults:")
        print(f"  ✅ Passed:  {passed}/{total}")
        print(f"  ❌ Failed:  {failed}/{total}")
        if skipped > 0:
            print(f"  ⏭️  Skipped: {skipped}/{total}")

        print("\nDetailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result is True else ("❌ FAIL" if result is False else "⏭️  SKIP")
            print(f"  {status}  {test_name}")

        if failed == 0 and passed > 0:
            print("\n🎉 All tests passed! Your hardware is configured correctly.")
        elif failed > 0:
            print("\n⚠️  Some tests failed. Check the recommendations above.")

        print("\n" + "=" * 70)


def main():
    """Main entry point"""
    tests = InteractiveTests()

    try:
        asyncio.run(tests.run_all_tests())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
