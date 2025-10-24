# TTS (Text-to-Speech) Fix

## Problem

The application was in SPEAKING state and logs showed it was trying to speak, but **no audible output** was produced. Hardware audio was verified working (aplay, speaker-test all working fine with HDMI monitors).

## Root Cause

**The `subsystem_manager.speak()` method was never being called!**

The application flow was:
1. ✅ Generate LLM response
2. ✅ Stream response text to UI frontend
3. ✅ Update app state to SPEAKING
4. ❌ **MISSING: Actually speak the response using TTS**
5. ✅ Transition back to IDLE

## Solution

Added calls to `subsystem_manager.speak()` in two places:

### 1. Main Response Speaking (main_new.py:417-420)

**Location**: `generate_conversation_response()` function

**Added**:
```python
# Speak the response using TTS
logger.info("Speaking response via TTS...")
await subsystem_manager.speak(message)
logger.info("TTS complete")
```

**Position**: After streaming response to UI, before adding to conversation history

### 2. Boot Greeting Speaking (main_new.py:555-558)

**Location**: `complete_boot_sequence()` function

**Added**:
```python
# Speak the greeting
logger.info("Speaking boot greeting via TTS...")
await subsystem_manager.speak(greeting_text)
logger.info("Boot greeting TTS complete")
```

**Position**: After displaying greeting words to UI

## Flow Now

### Normal Conversation
1. User says wake word
2. System records audio
3. Whisper transcribes audio → text
4. Agent loop processes with tools
5. Conversation model generates response
6. Response streams to UI (visual)
7. **Response speaks via TTS (audio)** ← FIXED
8. Return to IDLE state

### Boot Sequence
1. Initialize application
2. Display "Initializing systems..."
3. Stream greeting to UI
4. **Speak greeting via TTS** ← FIXED
5. Transition to IDLE (ready for wake word)

## TTS Configuration

TTS is working correctly using:
- **Engine**: pyttsx3 (espeak backend on Linux)
- **Rate**: 150 words/minute (from config)
- **Volume**: 0.9 (from config)
- **Voice**: Default English voice
- **Output**: System default audio device (PulseAudio/PipeWire → HDMI)

## Testing

### Test TTS Directly
Run the comprehensive TTS test:
```bash
python3 test_tts.py
```

This tests:
- Audio device enumeration
- PulseAudio status
- espeak direct execution
- pyttsx3 initialization
- Synchronous and asynchronous speaking
- Multiple message sequences

### Test in Application
1. Start the application: `python3 main_new.py`
2. **Boot greeting**: You should hear "Hello! I'm your AI voice assistant..."
3. Say wake word "hal"
4. Say a command like "what time is it"
5. **Response**: You should hear the AI speak the time back to you

## Files Modified

1. **main_new.py** (2 locations)
   - Line 417-420: Added TTS call after generating conversation response
   - Line 555-558: Added TTS call during boot greeting

2. **test_tts.py** (new file)
   - Comprehensive TTS testing suite
   - Tests all TTS components and audio routing

## Audio Routing Notes

- System uses PipeWire (modern audio server on Pi 5)
- Default output: HDMI audio
- TTS output goes to system default sink
- If you need different output, configure PulseAudio default sink

## Performance Impact

TTS speaking adds:
- ~1-3 seconds depending on message length
- Runs in executor (non-blocking)
- Does not interfere with wake word detection
- Audio manager stays in IDLE mode during TTS (correct behavior)

## Related Issues Fixed

This fix also revealed that:
- TTS initialization was working correctly all along
- Hardware audio routing was correct
- The only issue was the missing function call

## Status

✅ **FIXED** - TTS now produces audible speech output
✅ Boot greeting speaks
✅ Conversation responses speak
✅ No conflicts with audio input (wake word detection)
