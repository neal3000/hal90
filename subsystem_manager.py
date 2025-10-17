"""
Subsystem Manager
Handles initialization, lifecycle, and coordination of all voice assistant subsystems
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class SubsystemManager:
    """Manages initialization and lifecycle of all subsystems"""

    def __init__(self, config, event_loop_coordinator):
        """Initialize subsystem manager

        Args:
            config: Configuration object
            event_loop_coordinator: Event loop coordinator instance
        """
        logger.info("Initializing SubsystemManager")
        self.config = config
        self.event_coordinator = event_loop_coordinator

        # Subsystem references (initialized in setup)
        self.wake_word_detector = None
        self.whisper_service = None
        self.audio_recorder = None
        self.tts_engine = None
        self.ollama_client = None
        self.tool_processor = None

        # Subsystem state
        self.subsystems_ready = False
        self.initialization_errors = []

        logger.info("SubsystemManager initialized")

    async def initialize_all(self):
        """Initialize all subsystems in proper order"""
        logger.info("=" * 60)
        logger.info("Starting subsystem initialization")
        logger.info("=" * 60)

        try:
            # 1. Initialize Ollama client (LLM)
            await self._initialize_ollama()

            # 2. Initialize Tool Processor
            await self._initialize_tool_processor()

            # 3. Initialize Whisper (STT)
            await self._initialize_whisper()

            # 4. Initialize TTS
            await self._initialize_tts()

            # 5. Initialize Audio Recorder
            await self._initialize_audio_recorder()

            # 6. Initialize Wake Word Detector (last, depends on audio)
            await self._initialize_wake_word()

            # Check if critical subsystems initialized
            # Critical: ollama, tool_processor, whisper, audio_recorder, wake_word
            # Non-critical: tts (can fail on systems without eSpeak)
            critical_subsystems = {
                'ollama': self.ollama_client,
                'tool_processor': self.tool_processor,
                'whisper': self.whisper_service,
                'audio_recorder': self.audio_recorder,
                'wake_word': self.wake_word_detector
            }

            missing_critical = [name for name, obj in critical_subsystems.items() if obj is None]

            if missing_critical:
                logger.error(f"Critical subsystem(s) failed to initialize: {', '.join(missing_critical)}")
                self.subsystems_ready = False
            else:
                logger.info("All critical subsystems initialized successfully")
                self.subsystems_ready = True

            if self.initialization_errors:
                logger.warning(f"Initialization completed with {len(self.initialization_errors)} non-critical error(s):")
                for error in self.initialization_errors:
                    logger.warning(f"  - {error}")

        except Exception as e:
            logger.error(f"Fatal error during subsystem initialization: {e}", exc_info=True)
            self.subsystems_ready = False
            raise

        logger.info("=" * 60)
        logger.info(f"Subsystem initialization complete. Ready: {self.subsystems_ready}")
        logger.info("=" * 60)

        return self.subsystems_ready

    async def _initialize_ollama(self):
        """Initialize Ollama LLM client"""
        logger.info("Initializing Ollama client...")
        try:
            from ollama_client import OllamaClient

            self.ollama_client = OllamaClient(
                base_url=self.config.OLLAMA_URL
            )

            # Test connection by listing models
            logger.info(f"Testing Ollama connection to {self.config.OLLAMA_URL}")
            # Note: We'll add a health check method to OllamaClient
            logger.info("Ollama client initialized successfully")

        except ImportError as e:
            error = f"Failed to import OllamaClient: {e}"
            logger.error(error)
            self.initialization_errors.append(error)
        except Exception as e:
            error = f"Failed to initialize Ollama client: {e}"
            logger.error(error, exc_info=True)
            self.initialization_errors.append(error)

    async def _initialize_tool_processor(self):
        """Initialize tool execution system"""
        logger.info("Initializing Tool Processor...")
        try:
            from tool_processor import ToolProcessor

            self.tool_processor = ToolProcessor()
            logger.info(f"Tool Processor initialized with {len(self.tool_processor.tools)} tools")

            # Log available tools
            for tool_name in self.tool_processor.tools.keys():
                logger.info(f"  - Tool registered: {tool_name}")

        except ImportError as e:
            error = f"Failed to import ToolProcessor: {e}"
            logger.error(error)
            self.initialization_errors.append(error)
        except Exception as e:
            error = f"Failed to initialize Tool Processor: {e}"
            logger.error(error, exc_info=True)
            self.initialization_errors.append(error)

    async def _initialize_whisper(self):
        """Initialize Whisper speech-to-text service"""
        logger.info("Initializing Whisper STT service...")
        try:
            from whisper_service import WhisperService

            self.whisper_service = WhisperService(
                model_name=self.config.WHISPER_MODEL,
                device=self.config.WHISPER_DEVICE,
                compute_type=self.config.WHISPER_COMPUTE_TYPE
            )

            logger.info(f"Whisper service initialized (model: {self.config.WHISPER_MODEL})")

        except ImportError as e:
            error = f"Failed to import WhisperService: {e}"
            logger.error(error)
            self.initialization_errors.append(error)
        except Exception as e:
            error = f"Failed to initialize Whisper service: {e}"
            logger.error(error, exc_info=True)
            self.initialization_errors.append(error)

    async def _initialize_tts(self):
        """Initialize text-to-speech engine"""
        logger.info("Initializing TTS engine...")
        try:
            if self.config.TTS_ENGINE == 'pyttsx3':
                import pyttsx3

                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', self.config.TTS_RATE)
                self.tts_engine.setProperty('volume', self.config.TTS_VOLUME)

                # Set voice if specified
                if self.config.TTS_VOICE:
                    voices = self.tts_engine.getProperty('voices')
                    for voice in voices:
                        if self.config.TTS_VOICE in voice.id:
                            self.tts_engine.setProperty('voice', voice.id)
                            logger.info(f"TTS voice set to: {voice.id}")
                            break

                logger.info(f"TTS engine initialized (pyttsx3, rate: {self.config.TTS_RATE})")
            else:
                error = f"Unsupported TTS engine: {self.config.TTS_ENGINE}"
                logger.error(error)
                self.initialization_errors.append(error)

        except ImportError as e:
            error = f"Failed to import pyttsx3: {e}"
            logger.error(error)
            self.initialization_errors.append(error)
        except Exception as e:
            error = f"Failed to initialize TTS engine: {e}"
            logger.error(error, exc_info=True)
            self.initialization_errors.append(error)

    async def _initialize_audio_recorder(self):
        """Initialize audio recording subsystem"""
        logger.info("Initializing Audio Recorder...")
        try:
            from audio_recorder import AudioRecorder

            self.audio_recorder = AudioRecorder(
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

            logger.info(f"Audio Recorder initialized ({self.config.AUDIO_SAMPLE_RATE}Hz, device: {self.config.AUDIO_INPUT_DEVICE}, amp: {self.config.AUDIO_AMPLIFICATION}x)")

        except ImportError as e:
            error = f"Failed to import AudioRecorder: {e}"
            logger.error(error)
            self.initialization_errors.append(error)
        except Exception as e:
            error = f"Failed to initialize Audio Recorder: {e}"
            logger.error(error, exc_info=True)
            self.initialization_errors.append(error)

    async def _initialize_wake_word(self):
        """Initialize wake word detection"""
        logger.info("Initializing Wake Word Detector...")
        try:
            # Use improved version with phonetic matching
            from wake_word_detector_improved import WakeWordDetectorImproved

            # Check if model exists
            model_path = Path(self.config.WAKE_WORD_MODEL_PATH)
            if not model_path.exists():
                error = f"Wake word model not found at {model_path}"
                logger.error(error)
                self.initialization_errors.append(error)
                return

            # Get amplification and similarity threshold from config
            amplification = float(getattr(self.config, 'AUDIO_AMPLIFICATION', 300.0))
            similarity_threshold = float(getattr(self.config, 'WAKE_WORD_SIMILARITY', 0.6))
            audio_device = int(getattr(self.config, 'AUDIO_INPUT_DEVICE', 2))

            self.wake_word_detector = WakeWordDetectorImproved(
                model_path=str(model_path),
                wake_word=self.config.WAKE_WORD,
                sample_rate=self.config.AUDIO_SAMPLE_RATE,
                amplification=amplification,
                similarity_threshold=similarity_threshold,
                audio_device=audio_device
            )

            logger.info(f"Wake Word Detector initialized (word: '{self.config.WAKE_WORD}', amp: {amplification}x, threshold: {similarity_threshold})")

        except ImportError as e:
            error = f"Failed to import WakeWordDetectorImproved: {e}"
            logger.error(error)
            self.initialization_errors.append(error)
        except Exception as e:
            error = f"Failed to initialize Wake Word Detector: {e}"
            logger.error(error, exc_info=True)
            self.initialization_errors.append(error)

    async def start_wake_word_listening(self, callback):
        """Start wake word detection with callback

        Args:
            callback: Async function to call when wake word detected
        """
        if not self.wake_word_detector:
            logger.error("Cannot start wake word listening: detector not initialized")
            return

        logger.info("Starting wake word listener...")
        try:
            task = self.event_coordinator.create_task(
                self.wake_word_detector.listen(callback),
                name="wake_word_listener"
            )
            logger.info("Wake word listener started")
            return task
        except Exception as e:
            logger.error(f"Failed to start wake word listener: {e}", exc_info=True)

    async def stop_wake_word_listening(self):
        """Stop wake word detection"""
        if not self.wake_word_detector:
            logger.warning("Cannot stop wake word listening: detector not initialized")
            return

        logger.info("Stopping wake word listener...")
        try:
            await self.wake_word_detector.stop()
            logger.info("Wake word listener stopped")
        except Exception as e:
            logger.error(f"Error stopping wake word listener: {e}", exc_info=True)

    async def record_audio(self) -> Optional[Path]:
        """Record audio until silence detected

        Returns:
            Path to recorded audio file, or None on error
        """
        if not self.audio_recorder:
            logger.error("Cannot record audio: recorder not initialized")
            return None

        logger.info("Starting audio recording...")
        try:
            audio_file = await self.audio_recorder.record()
            logger.info(f"Audio recording complete: {audio_file}")
            return audio_file
        except Exception as e:
            logger.error(f"Error during audio recording: {e}", exc_info=True)
            return None

    async def transcribe_audio(self, audio_file: Path) -> Optional[str]:
        """Transcribe audio file to text

        Args:
            audio_file: Path to audio file

        Returns:
            Transcribed text, or None on error
        """
        if not self.whisper_service:
            logger.error("Cannot transcribe: Whisper service not initialized")
            return None

        logger.info(f"Transcribing audio file: {audio_file}")
        try:
            text = await self.whisper_service.transcribe(str(audio_file))
            logger.info(f"Transcription complete: '{text}'")
            return text
        except Exception as e:
            logger.error(f"Error during transcription: {e}", exc_info=True)
            return None

    async def speak(self, text: str):
        """Speak text using TTS engine

        Args:
            text: Text to speak
        """
        if not self.tts_engine:
            logger.error("Cannot speak: TTS engine not initialized")
            return

        logger.info(f"Speaking text: '{text[:50]}...'")
        try:
            # Run TTS in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._speak_sync, text)
            logger.info("Speech complete")
        except Exception as e:
            logger.error(f"Error during speech: {e}", exc_info=True)

    def _speak_sync(self, text: str):
        """Synchronous TTS method"""
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    async def shutdown(self):
        """Shutdown all subsystems gracefully"""
        logger.info("Shutting down all subsystems...")

        # Stop wake word detector
        if self.wake_word_detector:
            try:
                await self.stop_wake_word_listening()
            except Exception as e:
                logger.error(f"Error stopping wake word detector: {e}")

        # Cleanup Whisper
        if self.whisper_service:
            try:
                logger.info("Cleaning up Whisper service")
                # Add cleanup if needed
            except Exception as e:
                logger.error(f"Error cleaning up Whisper: {e}")

        # Cleanup TTS
        if self.tts_engine:
            try:
                logger.info("Stopping TTS engine")
                self.tts_engine.stop()
            except Exception as e:
                logger.error(f"Error stopping TTS: {e}")

        logger.info("All subsystems shut down")

    def get_status(self) -> Dict[str, Any]:
        """Get status of all subsystems

        Returns:
            Dictionary with subsystem status
        """
        status = {
            'ready': self.subsystems_ready,
            'errors': self.initialization_errors,
            'subsystems': {
                'ollama': self.ollama_client is not None,
                'tool_processor': self.tool_processor is not None,
                'whisper': self.whisper_service is not None,
                'tts': self.tts_engine is not None,
                'audio_recorder': self.audio_recorder is not None,
                'wake_word': self.wake_word_detector is not None,
            }
        }

        logger.debug(f"Subsystem status: {status}")
        return status
