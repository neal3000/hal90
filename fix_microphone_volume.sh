#!/bin/bash
# Fix USB Microphone Volume

echo "=========================================="
echo "USB Microphone Volume Fix"
echo "=========================================="
echo

# Find USB audio card
echo "Finding USB audio device..."
CARD_NUM=$(arecord -l | grep -i "USB" | head -1 | sed 's/card \([0-9]\).*/\1/')

if [ -z "$CARD_NUM" ]; then
    echo "ERROR: No USB audio device found!"
    echo "Please check that your USB microphone is connected."
    exit 1
fi

echo "Found USB audio device: card $CARD_NUM"
echo

# Show current settings
echo "Current audio settings:"
amixer -c $CARD_NUM

echo
echo "=========================================="
echo "Setting microphone volume to maximum..."
echo "=========================================="
echo

# Try to set capture volume to maximum
amixer -c $CARD_NUM set Mic 100% 2>/dev/null || echo "Mic control not available"
amixer -c $CARD_NUM set Capture 100% 2>/dev/null || echo "Capture control not available"
amixer -c $CARD_NUM set 'Mic Capture' 100% 2>/dev/null || echo "Mic Capture control not available"

# Unmute if muted
amixer -c $CARD_NUM set Mic unmute 2>/dev/null || true
amixer -c $CARD_NUM set Capture unmute 2>/dev/null || true
amixer -c $CARD_NUM set Capture cap 2>/dev/null || true

echo
echo "=========================================="
echo "New audio settings:"
echo "=========================================="
amixer -c $CARD_NUM

echo
echo "Volume boost applied!"
echo
echo "To test microphone, run:"
echo "  arecord -D hw:$CARD_NUM,0 -d 5 -f S16_LE -r 48000 test.wav && aplay test.wav"
echo
