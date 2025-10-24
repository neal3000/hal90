"""
Configuration Management System
Loads environment variables and provides centralized config access
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Config:
    """Centralized configuration management"""

    def __init__(self):
        """Initialize configuration from environment variables"""
        # Load .env file if it exists
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            logger.info(f"Loading environment from {env_path}")
            load_dotenv(env_path)
        else:
            logger.warning(f"No .env file found at {env_path}, using defaults")

        # Ollama Configuration
        self.OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.OLLAMA_AGENT_MODEL = os.getenv('OLLAMA_AGENT_MODEL', 'qwen2.5:3b')
        self.OLLAMA_CONVERSATION_MODEL = os.getenv('OLLAMA_CONVERSATION_MODEL', 'gemma2:2b')
        self.OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', '120'))
        logger.info(f"Ollama URL: {self.OLLAMA_URL}")
        logger.info(f"Agent model: {self.OLLAMA_AGENT_MODEL}")
        logger.info(f"Conversation model: {self.OLLAMA_CONVERSATION_MODEL}")

        # Whisper Configuration
        self.WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'tiny.en')
        self.WHISPER_DEVICE = os.getenv('WHISPER_DEVICE', 'cpu')
        self.WHISPER_COMPUTE_TYPE = os.getenv('WHISPER_COMPUTE_TYPE', 'int8')
        logger.info(f"Whisper model: {self.WHISPER_MODEL} on {self.WHISPER_DEVICE} ({self.WHISPER_COMPUTE_TYPE})")

        # Wake Word Configuration
        self.WAKE_WORD = os.getenv('WAKE_WORD', 'max')
        self.WAKE_WORD_MODEL_PATH = os.getenv('WAKE_WORD_MODEL_PATH',
                                               str(Path(__file__).parent / 'models' / 'vosk-model-small-en-us-0.15'))
        self.WAKE_WORD_SIMILARITY = float(os.getenv('WAKE_WORD_SIMILARITY', '0.6'))
        self.WAKE_WORD_DEVICE_RELEASE_DELAY = float(os.getenv('WAKE_WORD_DEVICE_RELEASE_DELAY', '0.5'))
        logger.info(f"Wake word: '{self.WAKE_WORD}'")
        logger.info(f"Wake word similarity threshold: {self.WAKE_WORD_SIMILARITY}")
        logger.info(f"Wake word device release delay: {self.WAKE_WORD_DEVICE_RELEASE_DELAY}s")
        logger.info(f"Wake word model path: {self.WAKE_WORD_MODEL_PATH}")

        # Audio Configuration
        self.AUDIO_INPUT_DEVICE = int(os.getenv('AUDIO_INPUT_DEVICE', '2'))
        self.AUDIO_SAMPLE_RATE = int(os.getenv('AUDIO_SAMPLE_RATE', '48000'))
        self.AUDIO_CHANNELS = int(os.getenv('AUDIO_CHANNELS', '1'))
        self.AUDIO_CHUNK_SIZE = int(os.getenv('AUDIO_CHUNK_SIZE', '4096'))
        self.AUDIO_AMPLIFICATION = float(os.getenv('AUDIO_AMPLIFICATION', '300.0'))  # For low-gain USB devices
        self.RECORDING_SILENCE_THRESHOLD = int(os.getenv('RECORDING_SILENCE_THRESHOLD', '2000'))
        self.RECORDING_SILENCE_DURATION = float(os.getenv('RECORDING_SILENCE_DURATION', '1.5'))
        self.RECORDING_MAX_DURATION = int(os.getenv('RECORDING_MAX_DURATION', '30'))
        logger.info(f"Audio config: device {self.AUDIO_INPUT_DEVICE}, {self.AUDIO_SAMPLE_RATE}Hz, {self.AUDIO_CHANNELS} channel(s), {self.AUDIO_AMPLIFICATION}x amplification")
        logger.info(f"Recording: max {self.RECORDING_MAX_DURATION}s, silence threshold {self.RECORDING_SILENCE_THRESHOLD}")

        # Recording Storage
        self.RECORDINGS_DIR = Path(os.getenv('RECORDINGS_DIR', '/tmp/voice_kiosk_recordings'))
        self.RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Recordings directory: {self.RECORDINGS_DIR}")

        # TTS Configuration
        self.TTS_ENGINE = os.getenv('TTS_ENGINE', 'pyttsx3')  # or 'piper'
        self.TTS_RATE = int(os.getenv('TTS_RATE', '150'))
        self.TTS_VOLUME = float(os.getenv('TTS_VOLUME', '0.9'))
        self.TTS_VOICE = os.getenv('TTS_VOICE', '')  # Empty for default
        logger.info(f"TTS engine: {self.TTS_ENGINE}, rate: {self.TTS_RATE}, volume: {self.TTS_VOLUME}")

        # Application Configuration
        self.EEL_PORT = int(os.getenv('EEL_PORT', '8080'))
        self.DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', 'voice_kiosk.log')
        logger.info(f"App config: Port {self.EEL_PORT}, Debug: {self.DEBUG_MODE}, Log level: {self.LOG_LEVEL}")

        # Screensaver Configuration
        self.SCREENSAVER_TIMEOUT = int(os.getenv('SCREENSAVER_TIMEOUT', '15'))
        self.SCREENSAVER_ENGAGEMENT_INTERVAL = int(os.getenv('SCREENSAVER_ENGAGEMENT_INTERVAL', '180'))
        logger.info(f"Screensaver: {self.SCREENSAVER_TIMEOUT}s timeout, {self.SCREENSAVER_ENGAGEMENT_INTERVAL}s engagement")

        # Agent Configuration
        self.AGENT_MAX_ITERATIONS = int(os.getenv('AGENT_MAX_ITERATIONS', '5'))
        self.AGENT_TIMEOUT = int(os.getenv('AGENT_TIMEOUT', '60'))
        logger.info(f"Agent: max {self.AGENT_MAX_ITERATIONS} iterations, {self.AGENT_TIMEOUT}s timeout")

        # MCP Configuration
        self.MCP_SERVERS_CONFIG = os.getenv('MCP_SERVERS_CONFIG',
                                             str(Path(__file__).parent.parent / 'mcp-servers.json'))
        self.MCP_INTENT_MAPPING = os.getenv('MCP_INTENT_MAPPING',
                                             str(Path(__file__).parent.parent / 'intent-mapping.json'))
        logger.info(f"MCP servers config: {self.MCP_SERVERS_CONFIG}")
        logger.info(f"MCP intent mapping: {self.MCP_INTENT_MAPPING}")

        # UI Configuration
        self.UI_WIDTH = int(os.getenv('UI_WIDTH', '1024'))
        self.UI_HEIGHT = int(os.getenv('UI_HEIGHT', '768'))
        self.UI_KIOSK_MODE = os.getenv('UI_KIOSK_MODE', 'true').lower() == 'true'
        logger.info(f"UI: {self.UI_WIDTH}x{self.UI_HEIGHT}, Kiosk mode: {self.UI_KIOSK_MODE}")

        logger.info("Configuration loaded successfully")

    def validate(self):
        """Validate critical configuration parameters"""
        logger.info("Validating configuration...")
        issues = []

        # Check wake word model exists
        if not Path(self.WAKE_WORD_MODEL_PATH).exists():
            issues.append(f"Wake word model not found at {self.WAKE_WORD_MODEL_PATH}")
            logger.error(f"Wake word model missing: {self.WAKE_WORD_MODEL_PATH}")

        # Check recordings directory is writable
        try:
            test_file = self.RECORDINGS_DIR / '.test'
            test_file.touch()
            test_file.unlink()
            logger.info(f"Recordings directory {self.RECORDINGS_DIR} is writable")
        except Exception as e:
            issues.append(f"Recordings directory not writable: {e}")
            logger.error(f"Recordings directory not writable: {e}")

        # Validate numeric ranges
        if not (0 < self.TTS_VOLUME <= 1.0):
            issues.append(f"TTS_VOLUME must be between 0 and 1, got {self.TTS_VOLUME}")
            logger.error(f"Invalid TTS_VOLUME: {self.TTS_VOLUME}")

        if self.AGENT_MAX_ITERATIONS < 1:
            issues.append(f"AGENT_MAX_ITERATIONS must be >= 1, got {self.AGENT_MAX_ITERATIONS}")
            logger.error(f"Invalid AGENT_MAX_ITERATIONS: {self.AGENT_MAX_ITERATIONS}")

        if issues:
            logger.error(f"Configuration validation failed with {len(issues)} issue(s)")
            for issue in issues:
                logger.error(f"  - {issue}")
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(issues))

        logger.info("Configuration validation passed")
        return True

# Global config instance
config = Config()

def get_config():
    """Get the global configuration instance"""
    return config
