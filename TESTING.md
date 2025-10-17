# Voice Kiosk Testing Guide

This document describes the testing suites available for the Voice Kiosk project.

## Test Suites

### 1. Non-Interactive Unit Tests (`test_unit.py`)

Automated tests that verify system components without requiring user interaction.

**What it tests:**
- ✅ Configuration loading and validation
- ✅ System prompt generation
- ✅ Tool loading and execution
- ✅ Event loop state management
- ✅ Ollama client initialization
- ✅ Audio processing calculations
- ✅ Phonetic matching algorithms
- ✅ JSON parsing and formatting

**Run unit tests:**
```bash
python3 test_unit.py
# or
./run_tests.sh unit
```

**Requirements:**
- No microphone needed
- No user interaction
- Can run on any system
- Fast execution (< 1 minute)

---

### 2. Interactive Hardware Tests (`test_interactive.py`)

Interactive tests that verify hardware setup and require user participation.

**What it tests:**

#### Test 1: Audio Device Detection
- Lists all available audio input devices
- Verifies configured device exists
- Shows device capabilities

#### Test 2: Microphone Gain Calibration ⭐
- Measures microphone input levels
- Calculates RMS with amplification
- Provides recommendations for AUDIO_AMPLIFICATION setting
- **Important:** Use this to calibrate your microphone!

#### Test 3: Wake Word Detection
- Tests if wake word is recognized
- Validates similarity threshold
- User says wake word, system detects it

#### Test 4: Audio Recording
- Tests audio recording with silence detection
- Verifies recording stops after silence
- Saves audio file for inspection

#### Test 5: Speech-to-Text
- Tests Whisper transcription
- User speaks a test phrase
- Verifies transcription accuracy

#### Test 6: End-to-End Pipeline ⭐
- Complete voice interaction flow
- Wake word → Record → Transcribe
- **Important:** Validates full system integration!

**Run interactive tests:**
```bash
python3 test_interactive.py
# or
./run_tests.sh interactive
```

**Requirements:**
- Working microphone
- Quiet environment
- User must speak when prompted
- Takes 5-10 minutes

---

## Quick Start

### Run All Tests
```bash
./run_tests.sh all
```

This will:
1. Run all unit tests first (automated)
2. Prompt to run interactive tests
3. Show summary of results

### Run Specific Test Type
```bash
# Only unit tests (fast, automated)
./run_tests.sh unit

# Only interactive tests (requires user)
./run_tests.sh interactive
```

---

## Test Scenarios

### Scenario 1: Initial Setup
**Goal:** Verify system is configured correctly

1. Run unit tests to verify configuration:
   ```bash
   python3 test_unit.py
   ```

2. Run interactive tests to calibrate hardware:
   ```bash
   python3 test_interactive.py
   ```

3. Pay special attention to **Test 2: Microphone Gain Calibration**
   - If RMS is too low, increase `AUDIO_AMPLIFICATION` in `.env`
   - If RMS is too high, decrease `AUDIO_AMPLIFICATION`
   - Target: 2000-30000 RMS after amplification

### Scenario 2: Wake Word Not Working
**Goal:** Diagnose wake word detection issues

1. Run **Test 2: Microphone Gain Calibration**
   - Verify amplified RMS is > 2000
   - If not, increase `AUDIO_AMPLIFICATION`

2. Run **Test 3: Wake Word Detection**
   - If not detected, try lowering `WAKE_WORD_SIMILARITY` (e.g., 0.5 or 0.4)
   - Check that you're saying the wake word clearly

3. Check logs for recognition attempts:
   - Look for "Recognized: 'word'" in logs
   - See what the system is hearing

### Scenario 3: Transcription Inaccurate
**Goal:** Verify speech-to-text is working

1. Run **Test 5: Speech-to-Text**
   - Speak clearly and at normal volume
   - Check transcription accuracy

2. If poor transcription:
   - Verify microphone gain (Test 2)
   - Try different Whisper model (edit `.env`)
   - Check for background noise

### Scenario 4: Complete System Validation
**Goal:** Verify entire pipeline before deployment

1. Run all unit tests:
   ```bash
   python3 test_unit.py
   ```
   All tests should pass.

2. Run **Test 6: End-to-End Pipeline**
   This validates the complete interaction flow.

3. If successful, system is ready for use!

---

## Interpreting Results

### Unit Test Results
```
test_config_loads (test_unit.TestConfiguration) ... ok
test_required_config_values (test_unit.TestConfiguration) ... ok
...
----------------------------------------------------------------------
Ran 35 tests in 0.845s

OK
```

- **OK** = All tests passed ✅
- **FAILED** = One or more tests failed ❌
- Look at error messages for specific failures

### Interactive Test Results

Each test shows:
- ✅ PASS - Test succeeded
- ❌ FAIL - Test failed (with reason)
- ⏭️  SKIP - Test skipped (inconclusive)

Example output:
```
✅ PASS: Audio Device Detection
  Found 3 input device(s), configured device is available

✅ PASS: Microphone Gain Calibration
  Amplified RMS: 15234.5
  Status: ✅ GOOD - Levels are optimal
```

### Common Issues and Solutions

#### "Device unavailable" error
- Another application is using the microphone
- Kill other audio applications
- Restart the test

#### "Wake word not detected"
- Microphone gain too low
- Run Test 2 and adjust `AUDIO_AMPLIFICATION`
- Lower `WAKE_WORD_SIMILARITY` threshold

#### "Transcription failed"
- Whisper model not loaded
- Check `WHISPER_MODEL` in `.env`
- Try smaller model: `tiny.en` or `base.en`

#### Unit tests fail on "validation"
- Wake word model files missing
- Download model to `./models/vosk-model-small-en-us-0.15`
- This is expected if models aren't installed yet

---

## Continuous Testing

### During Development
Run unit tests frequently:
```bash
python3 test_unit.py
```

Fast feedback on code changes.

### Before Deployment
Run full test suite:
```bash
./run_tests.sh all
```

Ensures everything works end-to-end.

### After Configuration Changes
Run interactive tests:
```bash
python3 test_interactive.py
```

Especially after changing:
- `AUDIO_AMPLIFICATION`
- `WAKE_WORD_SIMILARITY`
- `AUDIO_INPUT_DEVICE`
- Whisper model settings

---

## Advanced Testing

### Testing Specific Components

#### Test Configuration Only
```python
python3 -c "from test_unit import TestConfiguration; import unittest; unittest.main(module='test_unit', argv=['', 'TestConfiguration'], exit=False)"
```

#### Test Tools Only
```python
python3 -c "from test_unit import TestToolProcessor; import unittest; unittest.main(module='test_unit', argv=['', 'TestToolProcessor'], exit=False)"
```

### Debugging Failed Tests

Enable verbose logging:
```bash
LOG_LEVEL=DEBUG python3 test_unit.py
```

Run single interactive test:
```python
# Edit test_interactive.py, comment out unwanted tests in run_all_tests()
python3 test_interactive.py
```

### Custom Test Scenarios

Create your own test script:
```python
#!/usr/bin/env python3
from config import get_config
from whisper_service import WhisperService
import asyncio

async def my_test():
    config = get_config()
    whisper = WhisperService(
        model_name=config.WHISPER_MODEL,
        device=config.WHISPER_DEVICE,
        compute_type=config.WHISPER_COMPUTE_TYPE
    )

    result = await whisper.transcribe("path/to/audio.wav")
    print(f"Result: {result}")

asyncio.run(my_test())
```

---

## Test Coverage

### Unit Tests Coverage
- Configuration: 8 tests
- System Prompts: 7 tests
- Tool Processor: 6 tests
- Event Loop: 5 tests
- Ollama Client: 3 tests (2 require server)
- Audio Processing: 3 tests
- Phonetic Matching: 4 tests
- JSON Parsing: 4 tests

**Total: 40 unit tests**

### Interactive Tests Coverage
- Audio Device Detection
- Microphone Gain Calibration
- Wake Word Detection
- Audio Recording
- Speech-to-Text
- End-to-End Pipeline

**Total: 6 interactive tests**

---

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Unit Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run unit tests
        run: python3 test_unit.py
```

Note: Interactive tests cannot run in CI/CD (require hardware).

---

## Support

If tests fail and you can't resolve the issue:

1. Check the error messages carefully
2. Review this guide for common solutions
3. Check `voice_kiosk.log` for detailed logs
4. Verify your `.env` configuration
5. Ensure all dependencies are installed

For microphone issues:
- Run `python3 test_interactive.py` and focus on Test 1 and Test 2
- These will help diagnose hardware problems

For software issues:
- Run `python3 test_unit.py` to identify component failures
- Check import errors or missing dependencies
