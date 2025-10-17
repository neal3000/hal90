"""
Improved Wake Word Detector with Phonetic Matching
Better accuracy for short wake words like "hal"
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
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class WakeWordDetectorImproved:
    """Detects wake word with phonetic matching for better accuracy"""

    def __init__(self, model_path: str, wake_word: str, sample_rate: int = 48000,
                 amplification: float = 300.0, similarity_threshold: float = 0.6,
                 audio_device: int = 2):
        """Initialize improved wake word detector

        Args:
            model_path: Path to Vosk model directory
            wake_word: Wake word to detect (e.g., "hal")
            sample_rate: Audio sample rate in Hz
            amplification: Amplification factor for low-gain devices
            similarity_threshold: Minimum similarity ratio (0.0-1.0) for detection
            audio_device: Audio input device index (default: 2)
        """
        logger.info(f"Initializing Improved Wake Word Detector: '{wake_word}'")
        self.model_path = model_path
        self.wake_word = wake_word.lower()
        self.sample_rate = sample_rate
        self.amplification = amplification
        self.similarity_threshold = similarity_threshold
        self.audio_device = audio_device
        self.is_listening = False
        self.audio_queue = queue.Queue(maxsize=20)
        self.stream = None
        self.model = None
        self.recognizer = None

        # Common misrecognitions for phonetic matching
        self.wake_word_variants = self._generate_variants()
        logger.info(f"Wake word variants: {self.wake_word_variants}")

        # Load Vosk model
        self._load_model()

        logger.info(f"Improved detector initialized: amp={amplification}x, threshold={similarity_threshold}")

    def _generate_variants(self):
        """Generate common phonetic variants of the wake word"""
        word = self.wake_word
        variants = [word]

        # Common phonetic substitutions
        phonetic_map = {
            'hal': ['how', 'hall', 'hell', 'hail', 'haul', 'owl', 'al', 'pal', 'cal'],
            'max': ['mack', 'mac', 'macs', 'backs', 'wax', 'tax'],
            'hey': ['hay', 'high', 'hi', 'a'],
            'computer': ['computers', 'computed'],
            'alexa': ['alex', 'alexis'],
            'jarvis': ['service', 'services'],
        }

        # Add known variants
        if word in phonetic_map:
            variants.extend(phonetic_map[word])

        return variants

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
        """Amplify audio data"""
        audio_float = audio_data.astype(np.float32)
        amplified = audio_float * self.amplification
        amplified_int16 = np.clip(amplified, -32768, 32767).astype(np.int16)
        return amplified_int16.tobytes()

    def _calculate_similarity(self, word1: str, word2: str) -> float:
        """Calculate similarity ratio between two words"""
        return SequenceMatcher(None, word1.lower(), word2.lower()).ratio()

    def _check_wake_word(self, text: str) -> bool:
        """Check if text contains wake word or close variant

        Args:
            text: Recognized text to check

        Returns:
            True if wake word detected
        """
        text = text.lower().strip()
        words = text.split()

        # Direct match
        if self.wake_word in text:
            logger.info(f"✓ Direct match: '{text}' contains '{self.wake_word}'")
            return True

        # Check each word in recognized text
        for word in words:
            # Check exact variants
            if word in self.wake_word_variants:
                logger.info(f"✓ Variant match: '{word}' is variant of '{self.wake_word}'")
                return True

            # Check phonetic similarity
            similarity = self._calculate_similarity(word, self.wake_word)
            if similarity >= self.similarity_threshold:
                logger.info(f"✓ Similarity match: '{word}' ~= '{self.wake_word}' ({similarity:.2f})")
                return True
            else:
                logger.debug(f"  '{word}' similarity to '{self.wake_word}': {similarity:.2f} (need {self.similarity_threshold})")

        return False

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream with amplification"""
        if status and 'overflow' in str(status).lower():
            return

        try:
            audio_np = np.frombuffer(indata, dtype=np.int16)
            amplified_bytes = self._amplify_audio(audio_np)

            try:
                self.audio_queue.put_nowait(amplified_bytes)
            except queue.Full:
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.put_nowait(amplified_bytes)
                except:
                    pass

        except Exception as e:
            logger.error(f"Error in audio callback: {e}")

    async def listen(self, callback: Callable):
        """Start listening for wake word"""
        logger.info("Starting improved wake word detection...")
        self.is_listening = True

        try:
            blocksize = int(self.sample_rate * 0.2)

            logger.info(f"Opening audio stream (rate: {self.sample_rate}Hz, blocksize: {blocksize})")
            logger.info(f"Software amplification: {self.amplification}x")
            logger.info(f"Similarity threshold: {self.similarity_threshold}")
            logger.info(f"Listening for: '{self.wake_word}' and variants: {self.wake_word_variants[:3]}")

            self.stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=blocksize,
                dtype='int16',
                channels=1,
                device=self.audio_device,
                callback=self._audio_callback,
                latency='high'
            )

            with self.stream:
                logger.info("Wake word detector listening...")

                while self.is_listening:
                    try:
                        try:
                            data = self.audio_queue.get_nowait()
                        except queue.Empty:
                            await asyncio.sleep(0.01)
                            continue

                        # Process audio with Vosk
                        if self.recognizer.AcceptWaveform(data):
                            result = json.loads(self.recognizer.Result())
                            text = result.get('text', '').strip()

                            if text:
                                logger.info(f"Recognized: '{text}'")

                                # Check for wake word with variants
                                if self._check_wake_word(text):
                                    logger.info("!" * 70)
                                    logger.info(f"WAKE WORD DETECTED from: '{text}'")
                                    logger.info("!" * 70)

                                    # Call callback
                                    if asyncio.iscoroutinefunction(callback):
                                        await callback()
                                    else:
                                        callback()

                        else:
                            # Partial result
                            partial = json.loads(self.recognizer.PartialResult())
                            partial_text = partial.get('partial', '').strip()

                            if partial_text:
                                # Check partial results too
                                if self._check_wake_word(partial_text):
                                    logger.info("!" * 70)
                                    logger.info(f"WAKE WORD DETECTED (partial) from: '{partial_text}'")
                                    logger.info("!" * 70)

                                    if asyncio.iscoroutinefunction(callback):
                                        await callback()
                                    else:
                                        callback()

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

        # Explicitly close the stream if it's open
        if self.stream:
            try:
                logger.info("Closing audio stream...")
                self.stream.close()
                self.stream = None
                logger.info("Audio stream closed successfully")
            except Exception as e:
                logger.error(f"Error closing audio stream: {e}")

        # Give time for stream resources to be fully released
        await asyncio.sleep(0.3)
        logger.info("Wake word detector stopped")

    def is_running(self) -> bool:
        """Check if detector is currently listening"""
        return self.is_listening

    def set_similarity_threshold(self, threshold: float):
        """Adjust similarity threshold (0.0-1.0)

        Lower = more sensitive (more false positives)
        Higher = less sensitive (fewer false positives)
        """
        self.similarity_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"Similarity threshold set to {self.similarity_threshold}")
