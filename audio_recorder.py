"""
Audio Recorder
Records audio from microphone with silence detection
"""
import asyncio
import logging
import wave
import time
from pathlib import Path
from typing import Optional
import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

class AudioRecorder:
    """Records audio with automatic silence detection"""

    def __init__(self, sample_rate: int = 16000, channels: int = 1, chunk_size: int = 4096,
                 silence_threshold: int = 2000, silence_duration: float = 1.5,
                 max_duration: int = 30, audio_device: Optional[int] = None,
                 amplification: float = 1.0,
                 recordings_dir: Path = Path("/tmp/voice_kiosk_recordings")):
        """Initialize audio recorder

        Args:
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            chunk_size: Chunk size for recording
            silence_threshold: RMS threshold below which is considered silence
            silence_duration: Duration of silence in seconds to stop recording
            max_duration: Maximum recording duration in seconds
            audio_device: Audio input device index (None for default)
            amplification: Audio amplification factor (1.0 = no amplification)
            recordings_dir: Directory to save recordings
        """
        logger.info("Initializing AudioRecorder")
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.max_duration = max_duration
        self.audio_device = audio_device
        self.amplification = amplification
        self.recordings_dir = Path(recordings_dir)

        # Create recordings directory
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        # Recording state
        self.is_recording = False
        self.audio_buffer = []

        logger.info(f"AudioRecorder initialized: {sample_rate}Hz, device: {audio_device}, amp: {amplification}x, silence threshold: {silence_threshold}")

    async def record(self) -> Optional[Path]:
        """Record audio until silence detected or max duration reached

        Returns:
            Path to saved audio file, or None on error
        """
        logger.info("Starting audio recording...")
        logger.info(f"Settings: sample_rate={self.sample_rate}, silence_threshold={self.silence_threshold}, "
                   f"silence_duration={self.silence_duration}s, max_duration={self.max_duration}s")

        self.is_recording = True
        self.audio_buffer = []

        # Generate filename with timestamp
        timestamp = int(time.time())
        output_file = self.recordings_dir / f"recording_{timestamp}.wav"
        logger.info(f"Output file: {output_file}")

        silence_start = None
        recording_start = time.time()
        chunk_count = 0
        total_chunks = 0

        try:
            # Open audio stream
            logger.info("Opening audio stream...")
            stream = sd.InputStream(
                device=self.audio_device,
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16'
            )

            with stream:
                logger.info("Recording started - speak now...")

                while self.is_recording:
                    # Read chunk
                    chunk, overflowed = stream.read(self.chunk_size)
                    if overflowed:
                        logger.warning("Audio buffer overflow detected")

                    chunk_count += 1
                    total_chunks += 1

                    # Apply amplification
                    if self.amplification != 1.0:
                        amplified_chunk = chunk.astype(np.float32) * self.amplification
                        amplified_chunk = np.clip(amplified_chunk, -32768, 32767).astype(np.int16)
                    else:
                        amplified_chunk = chunk

                    # Add amplified audio to buffer
                    self.audio_buffer.append(amplified_chunk.copy())

                    # Calculate RMS (volume level) from amplified audio
                    rms = np.sqrt(np.mean(amplified_chunk.astype(np.float32) ** 2))

                    # Log every 10 chunks
                    if chunk_count >= 10:
                        logger.debug(f"Recording... RMS: {rms:.0f}, chunks: {total_chunks}, "
                                   f"duration: {(time.time() - recording_start):.1f}s")
                        chunk_count = 0

                    # Check for silence
                    if rms < self.silence_threshold:
                        if silence_start is None:
                            silence_start = time.time()
                            logger.info(f"Silence detected (RMS: {rms:.0f} < {self.silence_threshold})")
                        else:
                            silence_elapsed = time.time() - silence_start
                            if silence_elapsed >= self.silence_duration:
                                logger.info(f"Silence duration threshold reached ({silence_elapsed:.2f}s), stopping recording")
                                break
                    else:
                        # Reset silence timer on speech
                        if silence_start is not None:
                            logger.debug(f"Speech resumed (RMS: {rms:.0f}), resetting silence timer")
                        silence_start = None

                    # Check max duration
                    elapsed = time.time() - recording_start
                    if elapsed >= self.max_duration:
                        logger.info(f"Maximum duration reached ({elapsed:.1f}s), stopping recording")
                        break

                    await asyncio.sleep(0.001)  # Small yield to allow other tasks

            logger.info("Recording stopped")

            # Save to file
            if self.audio_buffer:
                await self._save_audio(output_file)
                logger.info(f"Audio saved: {output_file} ({len(self.audio_buffer)} chunks)")
                return output_file
            else:
                logger.warning("No audio data recorded")
                return None

        except Exception as e:
            logger.error(f"Error during recording: {e}", exc_info=True)
            return None
        finally:
            self.is_recording = False
            logger.info("Recording cleanup complete")

    async def _save_audio(self, output_file: Path):
        """Save audio buffer to WAV file

        Args:
            output_file: Path to save file
        """
        logger.info(f"Saving audio to {output_file}")

        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._save_audio_sync, output_file)
            logger.info(f"Audio file saved successfully: {output_file}")
        except Exception as e:
            logger.error(f"Error saving audio file: {e}", exc_info=True)
            raise

    def _save_audio_sync(self, output_file: Path):
        """Synchronous audio save method

        Args:
            output_file: Path to save file
        """
        # Concatenate all chunks
        audio_data = np.concatenate(self.audio_buffer, axis=0)

        # Save as WAV
        with wave.open(str(output_file), 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

        logger.debug(f"WAV file written: {audio_data.shape[0]} frames")

    async def stop(self):
        """Stop current recording"""
        logger.info("Stopping audio recording...")
        self.is_recording = False

    def get_last_recording_info(self) -> dict:
        """Get information about the last recording

        Returns:
            Dictionary with recording info
        """
        if not self.audio_buffer:
            return {"status": "no recording"}

        total_samples = sum(len(chunk) for chunk in self.audio_buffer)
        duration = total_samples / self.sample_rate

        info = {
            "status": "available",
            "chunks": len(self.audio_buffer),
            "total_samples": total_samples,
            "duration_seconds": duration,
            "sample_rate": self.sample_rate,
            "channels": self.channels
        }

        logger.debug(f"Last recording info: {info}")
        return info
