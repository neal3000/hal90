"""
Wake Word Detector with Software Amplification
For PCM2902 and other low-gain USB audio devices
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Callable, Optional
import queue
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer

logger = logging.getLogger(__name__)

class WakeWordDetectorAmplified:
    """Detects wake word with software amplification for low-gain devices"""

    def __init__(self, model_path: str, wake_word: str, sample_rate: int = 48000,
                 amplification: float = 300.0):
        """Initialize wake word detector

        Args:
            model_path: Path to Vosk model directory
            wake_word: Wake word to detect (e.g., "max")
            sample_rate: Audio sample rate in Hz
            amplification: Amplification factor (default 50x for PCM2902)
        """
        logger.info(f"Initializing WakeWordDetectorAmplified with model: {model_path}")
        logger.info(f"Amplification factor: {amplification}x")
        self.model_path = model_path
        self.wake_word = wake_word.lower()
        self.sample_rate = sample_rate
        self.amplification = amplification
        self.is_listening = False
        self.audio_queue = queue.Queue(maxsize=20)  # Larger queue to handle bursts
        self.stream = None
        self.model = None
        self.recognizer = None

        # Load Vosk model
        self._load_model()

        logger.info(f"WakeWordDetectorAmplified initialized for word: '{self.wake_word}'")

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
            self.recognizer.SetWords(True)
            logger.info("Vosk model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Vosk model: {e}", exc_info=True)
            raise

    def _amplify_audio(self, audio_data: np.ndarray) -> bytes:
        """Amplify audio data with clipping protection

        Args:
            audio_data: Input audio as int16 numpy array

        Returns:
            Amplified audio as bytes
        """
        # Convert to float for processing
        audio_float = audio_data.astype(np.float32)

        # Amplify
        amplified = audio_float * self.amplification

        # Hard clip to prevent overflow
        amplified_int16 = np.clip(amplified, -32768, 32767).astype(np.int16)

        return amplified_int16.tobytes()

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream with amplification

        Args:
            indata: Audio data
            frames: Number of frames
            time_info: Time information
            status: Status flags
        """
        # Don't log every overflow, just drop frames silently
        if status and 'overflow' in str(status).lower():
            return  # Skip this frame

        try:
            # Convert to numpy array
            audio_np = np.frombuffer(indata, dtype=np.int16)

            # Amplify
            amplified_bytes = self._amplify_audio(audio_np)

            # Put in queue (non-blocking)
            try:
                self.audio_queue.put_nowait(amplified_bytes)
            except queue.Full:
                # Queue full - remove oldest item and add new one
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.put_nowait(amplified_bytes)
                except:
                    pass

        except Exception as e:
            logger.error(f"Error in audio callback: {e}")

    async def listen(self, callback: Callable):
        """Start listening for wake word

        Args:
            callback: Async function to call when wake word detected
        """
        logger.info("Starting amplified wake word detection...")
        self.is_listening = True

        try:
            # Calculate appropriate blocksize (0.2 seconds for faster processing)
            blocksize = int(self.sample_rate * 0.2)

            # Open audio stream
            logger.info(f"Opening audio stream (rate: {self.sample_rate}Hz, blocksize: {blocksize})")
            logger.info(f"Software amplification: {self.amplification}x")

            self.stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=blocksize,
                dtype='int16',
                channels=1,
                device=2,  # Force USB device (hw:2,0)
                callback=self._audio_callback,
                latency='high'
            )

            with self.stream:
                logger.info("Wake word detector listening with amplification...")

                while self.is_listening:
                    try:
                        # Get amplified audio data from queue (non-blocking check)
                        try:
                            data = self.audio_queue.get_nowait()
                        except queue.Empty:
                            await asyncio.sleep(0.01)
                            continue

                        # Process audio with Vosk
                        if self.recognizer.AcceptWaveform(data):
                            result = json.loads(self.recognizer.Result())
                            text = result.get('text', '').lower()

                            if text:
                                logger.info(f"Recognized: '{text}'")

                            # Check for wake word
                            if self.wake_word in text:
                                logger.info(f"Wake word '{self.wake_word}' detected!")

                                # Call callback
                                if asyncio.iscoroutinefunction(callback):
                                    await callback()
                                else:
                                    callback()

                                # Continue listening
                                logger.debug("Continuing to listen for wake word...")

                        else:
                            # Partial result
                            partial = json.loads(self.recognizer.PartialResult())
                            partial_text = partial.get('partial', '').lower()

                            if partial_text:
                                logger.debug(f"Partial: '{partial_text}'")

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
        await asyncio.sleep(0.2)
        logger.info("Wake word detector stopped")

    def is_running(self) -> bool:
        """Check if detector is currently listening"""
        return self.is_listening
