"""
Wake Word Detector
Listens for wake word using Vosk speech recognition
Ported from old/maxheadbox/backend/awaker.py
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Callable, Optional
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer

logger = logging.getLogger(__name__)

class WakeWordDetector:
    """Detects wake word using Vosk model"""

    def __init__(self, model_path: str, wake_word: str, sample_rate: int = 16000):
        """Initialize wake word detector

        Args:
            model_path: Path to Vosk model directory
            wake_word: Wake word to detect (e.g., "max")
            sample_rate: Audio sample rate in Hz
        """
        logger.info(f"Initializing WakeWordDetector with model: {model_path}")
        self.model_path = model_path
        self.wake_word = wake_word.lower()
        self.sample_rate = sample_rate
        self.is_listening = False
        self.audio_queue = queue.Queue()
        self.stream = None
        self.model = None
        self.recognizer = None

        # Load Vosk model
        self._load_model()

        logger.info(f"WakeWordDetector initialized for word: '{self.wake_word}'")

    def _load_model(self):
        """Load Vosk model from disk"""
        logger.info(f"Loading Vosk model from {self.model_path}")

        if not Path(self.model_path).exists():
            error = f"Vosk model not found at {self.model_path}"
            logger.error(error)
            raise FileNotFoundError(error)

        try:
            self.model = Model(self.model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords(True)  # Enable word-level timestamps
            logger.info("Vosk model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Vosk model: {e}", exc_info=True)
            raise

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream

        Args:
            indata: Audio data
            frames: Number of frames
            time_info: Time information
            status: Status flags
        """
        if status:
            logger.warning(f"Audio callback status: {status}")

        # Put audio data in queue for processing
        self.audio_queue.put(bytes(indata))

    async def listen(self, callback: Callable):
        """Start listening for wake word

        Args:
            callback: Async function to call when wake word detected
        """
        logger.info("Starting wake word detection...")
        self.is_listening = True

        try:
            # Calculate appropriate blocksize based on sample rate
            # We want approximately 0.5 seconds of audio per block
            blocksize = int(self.sample_rate * 0.5)

            # Open audio stream
            logger.info(f"Opening audio stream (rate: {self.sample_rate}Hz, blocksize: {blocksize})")
            self.stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=blocksize,
                dtype='int16',
                channels=1,
                callback=self._audio_callback
            )

            with self.stream:
                logger.info("Wake word detector listening...")

                while self.is_listening:
                    try:
                        # Get audio data from queue
                        data = await asyncio.get_event_loop().run_in_executor(
                            None, self.audio_queue.get, True, 0.1
                        )

                        # Process audio with Vosk
                        if self.recognizer.AcceptWaveform(data):
                            result = json.loads(self.recognizer.Result())
                            text = result.get('text', '').lower()

                            logger.debug(f"Recognized: '{text}'")

                            # Check for wake word
                            if self.wake_word in text:
                                logger.info(f"Wake word '{self.wake_word}' detected!")

                                # Call callback
                                if asyncio.iscoroutinefunction(callback):
                                    await callback()
                                else:
                                    callback()

                                # Continue listening (don't stop)
                                logger.debug("Continuing to listen for wake word...")

                        else:
                            # Partial result
                            partial = json.loads(self.recognizer.PartialResult())
                            partial_text = partial.get('partial', '').lower()

                            if partial_text and self.wake_word in partial_text:
                                logger.debug(f"Partial match detected: '{partial_text}'")

                    except queue.Empty:
                        # No audio data available, continue
                        await asyncio.sleep(0.01)
                        continue
                    except asyncio.CancelledError:
                        logger.info("Wake word detection cancelled")
                        break
                    except Exception as e:
                        logger.error(f"Error processing audio: {e}", exc_info=True)
                        await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Error in wake word detection: {e}", exc_info=True)
        finally:
            self.is_listening = False
            if self.stream:
                try:
                    self.stream.close()
                    logger.info("Audio stream closed")
                except Exception as e:
                    logger.error(f"Error closing audio stream: {e}")

            logger.info("Wake word detection stopped")

    async def stop(self):
        """Stop listening for wake word"""
        logger.info("Stopping wake word detector...")
        self.is_listening = False

        # Give time for loop to exit
        await asyncio.sleep(0.2)

        logger.info("Wake word detector stopped")

    def is_running(self) -> bool:
        """Check if detector is currently listening"""
        return self.is_listening
