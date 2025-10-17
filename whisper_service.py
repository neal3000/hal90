"""
Whisper Speech-to-Text Service
Uses faster-whisper for efficient transcription
Ported from old/maxheadbox/backend/whisper_service.py
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

class WhisperService:
    """Speech-to-text service using faster-whisper"""

    def __init__(self, model_name: str = "tiny.en", device: str = "cpu", compute_type: str = "int8"):
        """Initialize Whisper service

        Args:
            model_name: Whisper model to use (tiny.en, base.en, small.en, etc.)
            device: Device to run on (cpu, cuda)
            compute_type: Compute type (int8, float16, float32)
        """
        logger.info(f"Initializing WhisperService with model: {model_name}")
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.model = None

        # Load model
        self._load_model()

        logger.info(f"WhisperService initialized (device: {device}, compute_type: {compute_type})")

    def _load_model(self):
        """Load Whisper model"""
        logger.info(f"Loading Whisper model: {self.model_name}")

        try:
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type
            )
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}", exc_info=True)
            raise

    async def transcribe(self, audio_file_path: str, language: str = "en") -> Optional[str]:
        """Transcribe audio file to text

        Args:
            audio_file_path: Path to audio file
            language: Language code (default: en)

        Returns:
            Transcribed text, or None on error
        """
        logger.info(f"Transcribing audio file: {audio_file_path}")

        if not Path(audio_file_path).exists():
            logger.error(f"Audio file not found: {audio_file_path}")
            return None

        try:
            # Run transcription in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._transcribe_sync,
                audio_file_path,
                language
            )

            logger.info(f"Transcription complete: '{result}'")
            return result

        except Exception as e:
            logger.error(f"Error during transcription: {e}", exc_info=True)
            return None

    def _transcribe_sync(self, audio_file_path: str, language: str) -> str:
        """Synchronous transcription method

        Args:
            audio_file_path: Path to audio file
            language: Language code

        Returns:
            Transcribed text
        """
        logger.debug(f"Starting synchronous transcription of {audio_file_path}")

        # Transcribe with word-level timestamps
        segments, info = self.model.transcribe(
            audio_file_path,
            language=language,
            beam_size=5,
            word_timestamps=True
        )

        logger.info(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")

        # Aggregate all segments into single text
        full_text = ""
        segment_count = 0

        for segment in segments:
            segment_count += 1
            logger.debug(f"Segment {segment_count}: [{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")
            full_text += segment.text + " "

        full_text = full_text.strip()
        logger.info(f"Transcribed {segment_count} segment(s), total length: {len(full_text)} chars")

        return full_text

    async def transcribe_with_timestamps(self, audio_file_path: str, language: str = "en") -> Optional[Dict[str, Any]]:
        """Transcribe audio file with detailed word-level timestamps

        Args:
            audio_file_path: Path to audio file
            language: Language code (default: en)

        Returns:
            Dictionary with segments and words, or None on error
        """
        logger.info(f"Transcribing with timestamps: {audio_file_path}")

        if not Path(audio_file_path).exists():
            logger.error(f"Audio file not found: {audio_file_path}")
            return None

        try:
            # Run transcription in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._transcribe_with_timestamps_sync,
                audio_file_path,
                language
            )

            logger.info(f"Transcription with timestamps complete: {len(result.get('segments', []))} segments")
            return result

        except Exception as e:
            logger.error(f"Error during transcription with timestamps: {e}", exc_info=True)
            return None

    def _transcribe_with_timestamps_sync(self, audio_file_path: str, language: str) -> Dict[str, Any]:
        """Synchronous transcription with timestamps

        Args:
            audio_file_path: Path to audio file
            language: Language code

        Returns:
            Dictionary with full transcription data
        """
        logger.debug(f"Starting detailed transcription of {audio_file_path}")

        # Transcribe with word-level timestamps
        segments, info = self.model.transcribe(
            audio_file_path,
            language=language,
            beam_size=5,
            word_timestamps=True
        )

        logger.info(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")

        # Build result structure
        result = {
            "text": "",
            "language": info.language,
            "language_probability": info.language_probability,
            "segments": []
        }

        full_text = ""

        for segment in segments:
            segment_data = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "words": []
            }

            # Extract word-level timestamps
            if hasattr(segment, 'words') and segment.words:
                for word in segment.words:
                    word_data = {
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "probability": word.probability
                    }
                    segment_data["words"].append(word_data)
                    logger.debug(f"Word: {word.word} [{word.start:.2f}s - {word.end:.2f}s]")

            result["segments"].append(segment_data)
            full_text += segment.text + " "

        result["text"] = full_text.strip()
        logger.info(f"Detailed transcription complete: {len(result['segments'])} segments")

        return result

    def get_model_info(self) -> Dict[str, str]:
        """Get information about loaded model

        Returns:
            Dictionary with model information
        """
        info = {
            "model_name": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "loaded": self.model is not None
        }
        logger.debug(f"Model info: {info}")
        return info
