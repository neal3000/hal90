# Microphone Volume & Buffer Fix

## Problems Fixed

1. **Input Overflow** - Buffer too small for high sample rates
2. **Low Volume** - USB microphone volume too quiet

## Solution 1: Fix Buffer Overflow

The wake word detector now automatically calculates the correct buffer size based on your sample rate.

**What was changed:**
- `wake_word_detector.py` now uses dynamic blocksize: `sample_rate * 0.5` (0.5 seconds of audio)
- For 44100Hz: blocksize = 22050
- For 48000Hz: blocksize = 24000

This prevents "input overflow" warnings.

## Solution 2: Boost Microphone Volume

### Quick Fix (Run this script)

```bash
cd /home/hal/hal/voice-kiosk
./fix_microphone_volume.sh
```

This will:
- Find your USB audio card
- Set capture volume to 100%
- Unmute microphone
- Show before/after settings

### Manual Fix (Using alsamixer)

```bash
# Open alsamixer for your USB card
alsamixer -c 2  # Replace 2 with your card number

# Use arrow keys to navigate:
# - Right/Left: Select control
# - Up/Down: Adjust volume
# - M: Toggle mute

# Controls to adjust:
# - Mic: Set to 100
# - Capture: Set to 100
# - Press SPACE to enable capture (red = enabled)

# Press ESC to exit
```

### Verify Volume

```bash
# Record 5 seconds and play back
arecord -D hw:2,0 -d 5 -f S16_LE -r 48000 test.wav && aplay test.wav

# If you can hear yourself clearly, volume is good!
```

## Solution 3: Update Sample Rate in .env

Your USB device doesn't support 16000Hz. Update your configuration:

```bash
# Edit .env file
nano /home/hal/hal/voice-kiosk/.env
```

Change this line:
```
AUDIO_SAMPLE_RATE=16000
```

To one of these (test script will tell you which one works):
```
AUDIO_SAMPLE_RATE=44100  # Most common for USB devices
# OR
AUDIO_SAMPLE_RATE=48000  # Some USB devices prefer this
```

## Solution 4: Persist Volume Settings

ALSA volume settings reset on reboot. To make them permanent:

### Option A: Save to ALSA config
```bash
# After setting volume with alsamixer or the script:
sudo alsactl store
```

### Option B: Create systemd service

Create `/etc/systemd/system/set-usb-mic-volume.service`:
```ini
[Unit]
Description=Set USB Microphone Volume
After=sound.target

[Service]
Type=oneshot
ExecStart=/home/hal/hal/voice-kiosk/fix_microphone_volume.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Enable it:
```bash
sudo systemctl enable set-usb-mic-volume.service
sudo systemctl start set-usb-mic-volume.service
```

### Option C: Add to crontab
```bash
crontab -e
```

Add this line:
```
@reboot sleep 10 && /home/hal/hal/voice-kiosk/fix_microphone_volume.sh
```

## Test After Fixes

Run the test suite again:
```bash
python test_wake_and_record.py
```

You should see:
- ✅ No "input overflow" warnings
- ✅ Good volume levels (RMS > 1000)
- ✅ Wake word detection working

## Troubleshooting

### Still getting "input overflow"
- The blocksize fix should resolve this
- If it persists, your system CPU might be overloaded
- Try: `sudo systemctl stop unattended-upgrades` (temporary)

### Volume still too low
1. Check physical microphone gain (some USB mics have a switch/knob)
2. Speak closer to microphone
3. Try different USB port (USB 3.0 ports sometimes work better)
4. Check system mixer: `pavucontrol` (if using PulseAudio)

### Wake word still not detecting
1. Verify microphone is working: `arecord -d 3 test.wav && aplay test.wav`
2. Check volume with test: RMS should be > 1000
3. Try different wake words: "max", "computer", "alexa", "jarvis"
4. Speak clearly and slightly louder than normal
5. Reduce background noise

### Different sample rate needed
Some devices are picky. Try these in order:
1. 48000 (most common)
2. 44100 (CD quality)
3. 16000 (if device supports it)
4. Check device specs: `arecord -L` or `pactl list sources`

## Summary Checklist

- [ ] Run `./fix_microphone_volume.sh`
- [ ] Update `AUDIO_SAMPLE_RATE` in `.env` (use value from test)
- [ ] Save ALSA settings: `sudo alsactl store`
- [ ] Test: `python test_wake_and_record.py`
- [ ] Verify no overflow warnings
- [ ] Verify wake word detects

Once all green, the main application should work!
