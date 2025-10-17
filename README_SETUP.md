# Voice Kiosk Setup Guide

## Quick Start

This guide will help you set up the migrated Voice Kiosk application on your Raspberry Pi 5.

## Prerequisites

- Raspberry Pi 5 with Raspberry Pi OS
- Python 3.9 or higher
- Microphone and speakers connected
- Ollama installed and running

## Installation Steps

### 1. Install System Dependencies

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install audio dependencies
sudo apt-get install -y portaudio19-dev python3-pyaudio
sudo apt-get install -y libasound2-dev

# Install Python development headers
sudo apt-get install -y python3-dev python3-pip

# Install Chromium for Eel (if not already installed)
sudo apt-get install -y chromium-browser
```

### 2. Install Python Dependencies

```bash
cd /home/hal/hal/voice-kiosk

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Download Vosk Wake Word Model

```bash
# Create models directory
mkdir -p models
cd models

# Download Vosk model (small English model, ~40MB)
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
rm vosk-model-small-en-us-0.15.zip

cd ..
```

### 4. Configure Application

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
nano .env
```

Key settings to configure:
- `OLLAMA_URL`: Your Ollama server URL (default: http://localhost:11434)
- `OLLAMA_AGENT_MODEL`: Model for tool calling (default: qwen2.5:3b)
- `OLLAMA_CONVERSATION_MODEL`: Model for responses (default: gemma2:2b)
- `WAKE_WORD`: Your wake word (default: "max")
- `WAKE_WORD_MODEL_PATH`: Path to Vosk model (default: ./models/vosk-model-small-en-us-0.15)

### 5. Install Ollama Models

```bash
# Pull the agent model
ollama pull qwen2.5:3b

# Pull the conversation model
ollama pull gemma2:2b

# Verify models are installed
ollama list
```

### 6. Test Audio Setup

```bash
# Test microphone
python test_audio.py

# This will list available audio devices
# Note the device index for your microphone
```

If you need to specify a specific audio device, you may need to adjust the audio recording code.

### 7. Run the Application

```bash
# Make sure you're in the voice-kiosk directory
cd /home/hal/hal/voice-kiosk

# Activate virtual environment (if using)
source venv/bin/activate

# Run with new integrated main
python main_new.py
```

The application will:
1. Initialize all subsystems (this may take 10-30 seconds)
2. Open a Chromium window in kiosk mode
3. Display the voice assistant UI
4. Start listening for the wake word

## Usage

### Basic Interaction Flow

1. **Boot**: Click the screen to initiate the system
2. **Idle**: Say the wake word (default: "max") to activate
3. **Recording**: Speak your request (automatically stops on silence)
4. **Processing**: Transcription and AI processing
5. **Speaking**: AI responds with text and speech
6. **Back to Idle**: Ready for next interaction

### Manual Activation

You can also click the screen when in IDLE mode to start recording without saying the wake word.

### Stop Speaking

Click during the SPEAKING state to interrupt the response.

## Troubleshooting

### Audio Issues

**Problem**: No audio input detected
```bash
# Check audio devices
arecord -l

# Test recording
arecord -d 5 test.wav
aplay test.wav
```

**Problem**: "No default input device" error
```bash
# Set default audio device in ~/.asoundrc
pcm.!default {
    type hw
    card 1
}

ctl.!default {
    type hw
    card 1
}
```

### Wake Word Not Detecting

**Problem**: Wake word not recognized
- Check microphone is working
- Verify WAKE_WORD in .env matches what you're saying
- Try increasing microphone sensitivity
- Check logs for Vosk model loading errors

### Ollama Connection Issues

**Problem**: Cannot connect to Ollama
```bash
# Check Ollama is running
systemctl status ollama

# Or if running manually
ollama serve

# Test Ollama
curl http://localhost:11434/api/tags
```

### Whisper Model Download Issues

**Problem**: faster-whisper model not downloading
- The model downloads automatically on first use
- Check internet connection
- Check disk space (~300MB needed for tiny.en model)
- Models are cached in `~/.cache/huggingface/`

### Memory Issues on Pi 5

**Problem**: Out of memory errors
- Use smaller models (tiny.en for Whisper, smaller Ollama models)
- Close other applications
- Consider using int8 quantization (already default)
- Increase swap space if needed

### Log Files

Check logs for detailed error information:
```bash
# View log file
tail -f voice_kiosk.log

# Or watch console output
python main_new.py
```

## Configuration Options

### Audio Configuration

```bash
# In .env file:
AUDIO_SAMPLE_RATE=16000          # Sample rate in Hz
AUDIO_CHANNELS=1                  # Mono audio
RECORDING_SILENCE_THRESHOLD=2000  # RMS threshold for silence
RECORDING_SILENCE_DURATION=1.5    # Seconds of silence to stop
RECORDING_MAX_DURATION=30         # Maximum recording length
```

### Model Configuration

```bash
# In .env file:
WHISPER_MODEL=tiny.en            # Options: tiny.en, base.en, small.en
WHISPER_DEVICE=cpu               # Options: cpu, cuda
WHISPER_COMPUTE_TYPE=int8        # Options: int8, float16, float32

OLLAMA_AGENT_MODEL=qwen2.5:3b    # Tool calling model
OLLAMA_CONVERSATION_MODEL=gemma2:2b  # Response generation model
```

### UI Configuration

```bash
# In .env file:
UI_WIDTH=1024                    # Window width
UI_HEIGHT=768                    # Window height
UI_KIOSK_MODE=true              # Fullscreen kiosk mode
EEL_PORT=8080                   # Web server port
```

## Performance Tuning

### For Raspberry Pi 5

1. **Use smaller models**:
   - Whisper: `tiny.en` (fastest, ~300MB RAM)
   - Agent: `qwen2.5:1.7b` (smaller alternative)
   - Conversation: `gemma:2b` (good balance)

2. **Optimize Whisper**:
   - Use `int8` compute type (default)
   - Consider `tiny.en` or `base.en` models

3. **Reduce logging in production**:
   ```bash
   LOG_LEVEL=WARNING  # Less verbose
   ```

4. **Disable debug features**:
   ```bash
   DEBUG_MODE=false
   ```

## Advanced Configuration

### Adding Custom Tools

Create a new tool in `tools/`:

```python
# tools/my_tool.py
import logging

logger = logging.getLogger(__name__)

TOOL_NAME = "my_tool"
TOOL_PARAMS = "param"
TOOL_DESCRIPTION = "what my tool does"

async def execute(parameter=None):
    logger.info(f"Executing my_tool with: {parameter}")
    # Your tool logic here
    return f"Result: {parameter}"

tool_def = {
    "name": TOOL_NAME,
    "params": TOOL_PARAMS,
    "description": TOOL_DESCRIPTION,
    "execution": execute
}
```

Tools are automatically loaded on startup.

### Running as System Service

Create `/etc/systemd/system/voice-kiosk.service`:

```ini
[Unit]
Description=Voice Kiosk AI Assistant
After=network.target ollama.service

[Service]
Type=simple
User=hal
WorkingDirectory=/home/hal/hal/voice-kiosk
ExecStart=/home/hal/hal/voice-kiosk/venv/bin/python main_new.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable voice-kiosk
sudo systemctl start voice-kiosk
sudo systemctl status voice-kiosk
```

## Next Steps

1. Test all functionality thoroughly
2. Adjust wake word sensitivity as needed
3. Customize system prompts in `system_prompt.py`
4. Add more tools as needed
5. Tune LLM parameters for your use case

## Getting Help

Check the logs first:
```bash
tail -f voice_kiosk.log
```

For extensive debugging:
```bash
LOG_LEVEL=DEBUG python main_new.py
```

## Migration Notes

The old `main.py` has been backed up to `main.py.backup`. The new integrated version is in `main_new.py`.

Once tested and working, you can:
```bash
mv main.py main_old.py
mv main_new.py main.py
```
