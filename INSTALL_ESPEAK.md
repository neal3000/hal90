# Installing eSpeak for TTS

The voice kiosk uses pyttsx3 which requires eSpeak or eSpeak-NG on Linux.

## Installation

Run the following command to install eSpeak:

```bash
sudo apt-get update
sudo apt-get install -y espeak espeak-ng
```

## Note

TTS is marked as **non-critical** in the subsystem initialization. The application will still start without eSpeak installed, but text-to-speech functionality will not be available.

If you need TTS functionality, install eSpeak using the commands above and restart the application.

## Verification

To verify eSpeak is installed:

```bash
which espeak
espeak "Hello, this is a test"
```

If installed correctly, you should hear the test message spoken.
