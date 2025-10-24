"""
Voice Activity Detection (VAD) based Audio Recorder
Uses Google's WebRTC VAD for reliable speech detection
"""
import asyncio
import logging
import wave
import time
from pathlib import Path
from typing import Optional
import numpy as np
import sounddevice as sd
import webrtcvad
from audio_agc import AutomaticGainControl

logger = logging.getLogger(__name__)


class VADRecorder:
    """
    Audio recorder with Voice Activity Detection
    Much more reliable than simple RMS-based silence detection
    """

    def __init__(
        self,
        sample_rate: int = 16000,  # WebRTC VAD requires 8k, 16k, 32k, or 48k
        channels: int = 1,
        vad_aggressiveness: int = 2,  # 0-3, higher = more aggressive filtering
        audio_device: Optional[int] = None,
        frame_duration_ms: int = 30,  # 10, 20, or 30ms frames for WebRTC VAD
        padding_duration_ms: int = 300,  # Add silence padding before/after speech
        min_speech_duration_ms: int = 500,  # Minimum speech length to keep
        max_duration_s: int = 30,
        recordings_dir: Path = Path("/tmp/voice_kiosk_recordings"),
        use_agc: bool = True
    ):
        """
        Initialize VAD-based recorder

        Args:
            sample_rate: Sample rate (must be 8000, 16000, 32000, or 48000)
            channels: Number of audio channels
            vad_aggressiveness: VAD aggressiveness (0=least, 3=most aggressive)
            audio_device: Audio input device index
            frame_duration_ms: Frame duration in ms (10, 20, or 30)
            padding_duration_ms: Silence padding around speech
            min_speech_duration_ms: Minimum speech duration to keep
            max_duration_s: Maximum recording duration
            recordings_dir: Directory to save recordings
            use_agc: Enable Automatic Gain Control
        """
        # Validate sample rate for WebRTC VAD
        if sample_rate not in [8000, 16000, 32000, 48000]:
            logger.warning(f"Sample rate {sample_rate} not directly supported by WebRTC VAD")
            logger.warning(f"Supported rates: 8000, 16000, 32000, 48000")
            logger.warning(f"Will use closest supported rate for VAD")
            # Find closest supported rate
            supported_rates = [8000, 16000, 32000, 48000]
            sample_rate = min(supported_rates, key=lambda x: abs(x - sample_rate))
            logger.info(f"Using VAD sample rate: {sample_rate}Hz")

        # Validate frame duration
        if frame_duration_ms not in [10, 20, 30]:
            raise ValueError(f"Frame duration must be 10, 20, or 30ms. Got {frame_duration_ms}")

        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_device = audio_device
        self.frame_duration_ms = frame_duration_ms
        self.max_duration_s = max_duration_s
        self.recordings_dir = Path(recordings_dir)
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        # Frame size in samples
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)

        # Padding frames (silence before/after speech)
        self.padding_frames = int(padding_duration_ms / frame_duration_ms)

        # Minimum speech frames
        self.min_speech_frames = int(min_speech_duration_ms / frame_duration_ms)

        # Initialize WebRTC VAD
        self.vad = webrtcvad.Vad(vad_aggressiveness)

        # Initialize AGC if enabled
        self.agc = None
        if use_agc:
            self.agc = AutomaticGainControl(
                target_rms=3000.0,
                min_gain=0.5,
                max_gain=50.0,
                sample_rate=sample_rate
            )

        logger.info(f"VAD Recorder initialized:")
        logger.info(f"  Sample rate: {sample_rate}Hz")
        logger.info(f"  VAD aggressiveness: {vad_aggressiveness}")
        logger.info(f"  Frame duration: {frame_duration_ms}ms")
        logger.info(f"  Padding: {padding_duration_ms}ms")
        logger.info(f"  Min speech: {min_speech_duration_ms}ms")
        logger.info(f"  AGC: {'enabled' if use_agc else 'disabled'}")

    async def record(self) -> Optional[Path]:
        """
        Record audio with VAD-based speech detection

        Returns:
            Path to saved audio file, or None if no speech detected
        """
        logger.info("Starting VAD recording...")

        frames = []
        speech_frames = []
        num_padding_frames = 0
        in_speech = False
        speech_detected = False

        # Start time
        start_time = time.time()

        def audio_callback(indata, frames_count, time_info, status):
            """Audio input callback"""
            if status:
                logger.warning(f"Audio callback status: {status}")

            # Copy audio data
            audio_frame = indata[:, 0].copy() if self.channels > 1 else indata.copy()

            # Convert to int16 for VAD
            audio_int16 = (audio_frame * 32767).astype(np.int16)

            # Apply AGC if enabled
            if self.agc:
                audio_int16 = self.agc.process(audio_int16)

            frames.append(audio_int16)

        # Open audio stream
        stream = sd.InputStream(
            device=self.audio_device,
            channels=self.channels,
            samplerate=self.sample_rate,
            blocksize=self.frame_size,
            dtype=np.float32,
            callback=audio_callback
        )

        with stream:
            logger.info("🎤 Listening... (speak now)")

            while True:
                # Check if we have enough frames to process
                if len(frames) == 0:
                    await asyncio.sleep(0.01)
                    continue

                # Get next frame
                frame = frames.pop(0)

                # Check for max duration
                if time.time() - start_time > self.max_duration_s:
                    logger.info(f"⏱️  Max duration ({self.max_duration_s}s) reached")
                    break

                # Detect speech in this frame
                frame_bytes = frame.tobytes()
                is_speech = self.vad.is_speech(frame_bytes, self.sample_rate)

                if is_speech:
                    if not in_speech:
                        logger.debug("🗣️  Speech started")
                        in_speech = True
                        speech_detected = True

                        # Add padding frames from before speech
                        for _ in range(self.padding_frames):
                            if speech_frames:
                                frames.insert(0, speech_frames.pop())

                    speech_frames.append(frame)
                    num_padding_frames = 0

                else:
                    if in_speech:
                        # Add padding after speech
                        speech_frames.append(frame)
                        num_padding_frames += 1

                        # Check if padding is complete
                        if num_padding_frames >= self.padding_frames:
                            logger.debug("🔇 Speech ended")

                            # Check if we have enough speech
                            if len(speech_frames) >= self.min_speech_frames:
                                logger.info(f"✅ Speech detected ({len(speech_frames)} frames)")
                                break
                            else:
                                logger.debug(f"⚠️  Speech too short ({len(speech_frames)} < {self.min_speech_frames} frames), continuing...")
                                speech_frames.clear()
                                in_speech = False
                                num_padding_frames = 0
                    else:
                        # Not in speech, keep limited buffer for padding
                        speech_frames.append(frame)
                        if len(speech_frames) > self.padding_frames:
                            speech_frames.pop(0)

                # Small sleep to prevent busy waiting
                await asyncio.sleep(0.001)

        # Check if we got any speech
        if not speech_detected or len(speech_frames) < self.min_speech_frames:
            logger.warning("⚠️  No speech detected")
            return None

        # Concatenate all frames
        audio_data = np.concatenate(speech_frames)

        # Save to file
        timestamp = int(time.time())
        filename = self.recordings_dir / f"recording_{timestamp}.wav"

        with wave.open(str(filename), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

        duration = len(audio_data) / self.sample_rate
        logger.info(f"✅ Recording saved: {filename} ({duration:.2f}s)")

        return filename
