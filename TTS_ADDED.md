# Text-to-Speech (TTS) Added

## What Was Added

Restored TTS functionality from the old `hal_main.py` so HAL now speaks responses out loud.

## Changes Made

### 1. Imported pyttsx3
**File**: `hal_voice_assistant.py:13`
```python
import pyttsx3
```

### 2. Added TTS Engine Global
**File**: `hal_voice_assistant.py:67`
```python
tts_engine = None  # TTS engine
```

### 3. Added TTS Initialization Function
**File**: `hal_voice_assistant.py:109-134`

Initializes pyttsx3 engine with configuration from config file:
- Sets speech rate from `config.TTS_RATE`
- Sets volume from `config.TTS_VOLUME`
- Optionally sets voice from `config.TTS_VOICE`

### 4. Added Speak Function
**File**: `hal_voice_assistant.py:137-150`

Simple function to speak text:
```python
def speak(text):
    """Speak text using TTS (non-blocking)"""
    tts_engine.say(text)
    tts_engine.runAndWait()
```

### 5. Initialize TTS on Startup
**File**: `hal_voice_assistant.py:171-176`

Added to `initialize_system()`:
```python
# Initialize TTS
eel_log("🔊 Initializing text-to-speech...")
if initialize_tts():
    eel_log("✅ TTS ready")
else:
    eel_log("⚠️  TTS initialization failed (will continue without speech)")
```

### 6. Speak Responses in Voice Loop
**File**: `hal_voice_assistant.py:251-253`

After processing command and getting response:
```python
# Speak response using TTS
loop = asyncio.get_event_loop()
await loop.run_in_executor(None, speak, response)
```

Uses `run_in_executor` to run the blocking TTS call without blocking the async event loop.

## Configuration

TTS settings are in `.env` or `config.py`:

```bash
TTS_ENGINE=pyttsx3
TTS_RATE=150          # Words per minute
TTS_VOLUME=0.9        # 0.0 to 1.0
TTS_VOICE=            # Leave empty for default voice
```

## Testing

To test TTS separately:
```bash
python test_tts.py
```

This runs comprehensive TTS tests to verify audio output.

## How It Works

1. User says wake word + command
2. System transcribes speech to text
3. Command is processed (MCP tool or LLM)
4. Response text is displayed in GUI
5. **Response is spoken using TTS** ✨
6. System returns to listening

## Notes

- TTS runs in thread executor to avoid blocking async event loop
- If TTS fails to initialize, system continues without speech (graceful degradation)
- Uses espeak backend on Linux (pyttsx3 default)
- Speech rate and volume are configurable
