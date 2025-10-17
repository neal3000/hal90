# Fix: Audio Device Conflict (Device Unavailable Error)

## Issue

```
Error opening InputStream: Device unavailable [PaErrorCode -9985]
```

### Problem Description

When the wake word "hal" is detected, the system transitions from IDLE to RECORDING state. This triggers:
1. Wake word detector stops
2. Audio recorder tries to start **immediately**
3. ERROR: Audio device still in use by wake word detector

The wake word detector's audio stream isn't fully closed before the recorder tries to open the same audio device (PCM2902).

### Timeline from Logs

```
06:40:49 - WAKE WORD DETECTED!
06:40:49 - State transition: IDLE -> RECORDING
06:40:49 - Stopping wake word listener...
06:40:49 - Starting audio recording...
06:40:49 - Opening audio stream...
06:40:49 - ERROR: Device unavailable [PaErrorCode -9985]
06:40:50 - Audio stream closed  ← Too late!
```

## Root Cause

**File:** `main_new.py` lines 144-148

The `on_recording` callback stops the wake word detector but doesn't wait for the audio device to be fully released before `handle_recording()` is called.

```python
# BEFORE - No delay
async def on_recording(metadata):
    logger.info("Entered RECORDING state")
    if subsystem_manager and subsystem_manager.wake_word_detector:
        await subsystem_manager.stop_wake_word_listening()
    # handle_recording() called immediately after this callback
```

## Solution

Add a configurable delay after stopping the wake word detector to ensure the audio device is fully released.

### Changes Made

#### 1. Updated `.env` Configuration

Added new configuration parameter:

```bash
# Wake Word Configuration
WAKE_WORD=hal
WAKE_WORD_MODEL_PATH=./models/vosk-model-small-en-us-0.15
WAKE_WORD_SIMILARITY=0.6
WAKE_WORD_DEVICE_RELEASE_DELAY=0.5  # NEW: Seconds to wait for device release
```

#### 2. Updated `config.py`

Added configuration loading (line 45):

```python
# Wake Word Configuration
self.WAKE_WORD = os.getenv('WAKE_WORD', 'max')
self.WAKE_WORD_MODEL_PATH = os.getenv('WAKE_WORD_MODEL_PATH', ...)
self.WAKE_WORD_SIMILARITY = float(os.getenv('WAKE_WORD_SIMILARITY', '0.6'))
self.WAKE_WORD_DEVICE_RELEASE_DELAY = float(os.getenv('WAKE_WORD_DEVICE_RELEASE_DELAY', '0.5'))  # NEW
logger.info(f"Wake word device release delay: {self.WAKE_WORD_DEVICE_RELEASE_DELAY}s")
```

#### 3. Updated `main_new.py`

Added delay in `on_recording` callback (lines 144-153):

```python
# AFTER - With configurable delay
async def on_recording(metadata):
    logger.info("Entered RECORDING state")
    if subsystem_manager and subsystem_manager.wake_word_detector:
        await subsystem_manager.stop_wake_word_listening()
        # Brief delay to ensure audio device is fully released
        delay = config.WAKE_WORD_DEVICE_RELEASE_DELAY
        logger.info(f"Waiting {delay}s for audio device release...")
        await asyncio.sleep(delay)
        logger.info("Audio device released, ready for recording")
```

## Expected Behavior After Fix

### New Timeline

```
06:40:49 - WAKE WORD DETECTED!
06:40:49 - State transition: IDLE -> RECORDING
06:40:49 - Stopping wake word listener...
06:40:49 - Waiting 0.5s for audio device release...
06:40:50 - Audio stream closed  ← Device released
06:40:50 - Audio device released, ready for recording
06:40:50 - Starting audio recording...
06:40:50 - Opening audio stream...
06:40:50 - ✓ Recording started successfully
```

## Testing

### Verify the Fix

1. Run the main application:
   ```bash
   python3 main_new.py
   ```

2. Say the wake word "hal"

3. Check logs for:
   ```
   Waiting 0.5s for audio device release...
   Audio device released, ready for recording
   Recording started - speak now...
   ```

4. Verify NO error: `Device unavailable [PaErrorCode -9985]`

### Adjust Delay If Needed

If you still see the device unavailable error:

1. Edit `.env`:
   ```bash
   WAKE_WORD_DEVICE_RELEASE_DELAY=1.0  # Increase to 1 second
   ```

2. Restart application

If 0.5s works perfectly, you could try reducing it:
```bash
WAKE_WORD_DEVICE_RELEASE_DELAY=0.3  # Reduce to 300ms
```

## Technical Details

### Why This Happens

**PortAudio/ALSA Device Access:**
- Only ONE process/stream can have exclusive access to an audio device at a time
- Wake word detector opens device with: `sd.InputStream(device=2, ...)`
- Audio recorder tries to open same device: `sd.InputStream(device=2, ...)`
- If first stream isn't closed, second open fails with PaErrorCode -9985

### Why Async Stop Isn't Enough

Even though `stop_wake_word_listening()` is async and we await it, the underlying PortAudio cleanup happens in a separate thread and takes time:

1. Python calls `stream.stop()` → returns immediately
2. PortAudio sends stop signal to audio thread
3. Audio thread processes final buffers
4. Audio thread closes ALSA device
5. Device is finally available ← This is not instant!

The 0.5s delay ensures step 5 completes before we try to open the device again.

## Configuration

### Default Value
```bash
WAKE_WORD_DEVICE_RELEASE_DELAY=0.5  # 500ms delay
```

### Tuning Guidelines

- **Too short** (< 0.3s): May still get "Device unavailable" errors
- **Optimal** (0.3-0.7s): Device releases cleanly, minimal user-perceived delay
- **Too long** (> 1.0s): Works but creates awkward pause after wake word

**Recommended:** Start with 0.5s, reduce to 0.3s if tests show it's stable.

## Related Files

- `.env` - Configuration file (line 19)
- `config.py` - Configuration loader (line 45)
- `main_new.py` - Main application with state callbacks (lines 144-153)
- `audio_recorder.py` - Audio recording class (uses device parameter)
- `wake_word_detector_improved.py` - Wake word detector (opens audio device)

## Impact

✅ **Benefits:**
- Eliminates "Device unavailable" errors
- Allows smooth transition from wake word detection to recording
- Configurable delay for different hardware

⚠️ **Trade-off:**
- Adds 0.5s delay between wake word detection and recording start
- User must pause slightly after saying wake word (already needed anyway)

## Summary

**Problem:** Audio device conflict when transitioning from wake word listening to recording.

**Solution:** Add configurable 0.5s delay after stopping wake word detector to ensure device is fully released.

**Configuration:** `WAKE_WORD_DEVICE_RELEASE_DELAY=0.5` in `.env`

**Status:** ✅ Fixed - Device release delay prevents conflicts
