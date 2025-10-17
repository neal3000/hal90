# Test Suite Summary

## Overview

Two comprehensive test suites have been created for the Voice Kiosk project:

1. **Non-Interactive Unit Tests** (`test_unit.py`) - 40 automated tests
2. **Interactive Hardware Tests** (`test_interactive.py`) - 6 user-guided tests

## Test Files Created

```
voice-kiosk/
├── test_unit.py                 # Non-interactive unit tests
├── test_interactive.py          # Interactive hardware tests
├── run_tests.sh                 # Test runner script
├── TESTING.md                   # Detailed testing guide
├── TESTING_QUICK_START.md      # Quick reference
└── TEST_SUMMARY.md             # This file
```

---

## Non-Interactive Unit Tests (`test_unit.py`)

### Test Coverage: 40 Tests

#### 1. Configuration Tests (6 tests)
- ✅ Configuration loads successfully
- ✅ Required values exist
- ✅ Numeric types are correct
- ✅ Values are in valid ranges
- ✅ Validation method works
- ✅ Recordings directory created

#### 2. System Prompt Tests (6 tests)
- ✅ SystemPrompt initializes with config
- ✅ Agent prompt has correct structure
- ✅ Conversation prompt has correct structure
- ✅ Prompts include tool descriptions
- ✅ Agent format schema is valid
- ✅ Conversation format schema is valid

#### 3. Tool Processor Tests (7 tests)
- ✅ ToolProcessor initializes
- ✅ Tools are loaded dynamically
- ✅ Required tools exist (finished, timenow)
- ✅ Tool structure is correct
- ✅ Tools prompt generation works
- ✅ Finished tool executes
- ✅ Timenow tool executes
- ✅ Unknown tool handling works

#### 4. Event Loop Coordinator Tests (5 tests)
- ✅ Coordinator initializes
- ✅ AppStatus enum values exist
- ✅ State transitions work
- ✅ State callbacks register
- ✅ Get state method works

#### 5. Ollama Client Tests (3 tests)
- ✅ Client initializes
- ⏭️  Chat completion (requires Ollama server)
- ⏭️  Stream response (requires Ollama server)
- ✅ JSON format structure is valid

#### 6. Audio Processing Tests (3 tests)
- ✅ Audio amplification calculations
- ✅ Format conversions (float ↔ int16)
- ✅ Silence detection logic

#### 7. Phonetic Matching Tests (4 tests)
- ✅ Exact word matching (hal = hal)
- ✅ Close match detection (hal ≈ how)
- ✅ Different word detection (low similarity)
- ✅ Case-insensitive matching

#### 8. JSON Parsing Tests (4 tests)
- ✅ Valid tool call JSON parses
- ✅ Valid conversation JSON parses
- ✅ Invalid JSON raises error
- ✅ Escaped quotes handled

### Running Unit Tests

```bash
python3 test_unit.py
```

**Expected Output:**
```
Ran 40 tests in 0.132s
OK (skipped=2)
```

**Time:** < 1 second

---

## Interactive Hardware Tests (`test_interactive.py`)

### Test Coverage: 6 Tests

#### Test 1: Audio Device Detection
**Purpose:** Verify audio input devices are available
- Lists all input devices
- Checks configured device exists
- Shows device capabilities

**User Action:** None (automatic)
**Time:** ~5 seconds

---

#### Test 2: Microphone Gain Calibration ⭐
**Purpose:** Measure and calibrate microphone input levels

**What it does:**
- Records 5 seconds of speech
- Calculates RMS levels (raw and amplified)
- Compares to silence threshold
- Provides amplification recommendations

**User Action:** Speak normally for 5 seconds

**What to look for:**
```
📊 Audio Level Analysis:
  Raw audio RMS:        42.3
  Amplified RMS:        12690.5
  Status: ✅ GOOD - Levels are optimal
```

**Target:** Amplified RMS between 2000-30000

**Time:** ~30 seconds

---

#### Test 3: Wake Word Detection
**Purpose:** Verify wake word is recognized

**What it does:**
- Starts wake word detector
- Listens for 15 seconds
- Detects if wake word is spoken

**User Action:** Say the wake word (e.g., "hal")

**What to look for:**
```
🎤 Listening for 'hal'... (15 seconds)
   Say: 'hal'

✓ Wake word detected!
✅ PASS: Wake Word Detection
```

**Time:** ~30 seconds

---

#### Test 4: Audio Recording
**Purpose:** Test audio recording with silence detection

**What it does:**
- Starts recording
- Records until silence detected
- Saves audio file
- Shows recording duration

**User Action:** Speak a sentence, then pause

**What to look for:**
```
🎤 Recording - SPEAK NOW!

✓ Recording saved: /tmp/voice_kiosk_recordings/recording_xxx.wav
  Duration: 3.2s
  File size: 307,200 bytes

✅ PASS: Audio Recording
```

**Time:** ~30 seconds

---

#### Test 5: Speech-to-Text
**Purpose:** Verify transcription accuracy

**What it does:**
- Records test phrase
- Transcribes with Whisper
- Shows transcription result

**User Action:** Say "The quick brown fox jumps over the lazy dog"

**What to look for:**
```
📝 Transcription:
  'the quick brown fox jumps over the lazy dog'

  Expected: 'The quick brown fox jumps over the lazy dog'
  Match: 9/9 words (100%)

✅ PASS: Speech-to-Text
```

**Time:** ~1 minute

---

#### Test 6: End-to-End Pipeline ⭐
**Purpose:** Validate complete voice interaction flow

**What it does:**
1. Listens for wake word
2. Records command after detection
3. Transcribes recording

**User Action:**
1. Say wake word
2. Say a command after detection

**What to look for:**
```
🎤 Step 1: Listening for wake word 'hal'...
   ✓ Wake word detected!

🎤 Step 2: Recording your command...
   ✓ Recording complete

⏳ Step 3: Transcribing...
   ✓ Transcription: 'what time is it'

✅ PASS: End-to-End Pipeline
```

**Time:** ~1 minute

---

### Running Interactive Tests

```bash
python3 test_interactive.py
```

**Expected Flow:**
1. Welcome message
2. Press Enter to start
3. Test 1 runs automatically
4. Tests 2-6 require user interaction
5. Summary at end

**Total Time:** ~5-10 minutes

---

## Test Runner Script (`run_tests.sh`)

Convenient wrapper for running tests:

```bash
# Run all tests
./run_tests.sh all

# Run only unit tests
./run_tests.sh unit

# Run only interactive tests
./run_tests.sh interactive
```

---

## Documentation Files

### TESTING.md (Comprehensive Guide)
- Detailed test descriptions
- Troubleshooting scenarios
- Configuration recommendations
- Common issues and solutions
- CI/CD integration examples

### TESTING_QUICK_START.md (Quick Reference)
- TL;DR commands
- Most important tests highlighted
- Quick fixes for common issues
- Example workflows

### TEST_SUMMARY.md (This File)
- Overview of test suites
- Complete test coverage list
- Expected outputs
- Time estimates

---

## Quick Start

### First Time Setup
```bash
# 1. Run unit tests
python3 test_unit.py

# 2. Calibrate hardware
python3 test_interactive.py
```

### Regular Testing
```bash
# Quick validation
python3 test_unit.py

# Full validation
./run_tests.sh all
```

### Debugging Issues
```bash
# Focus on specific issue
python3 test_interactive.py
# Follow test recommendations
```

---

## Test Results Interpretation

### Unit Tests
```
Ran 40 tests in 0.132s
OK (skipped=2)
```
✅ **All systems operational**

```
FAILED (failures=2, skipped=2)
```
❌ **Check error messages**

### Interactive Tests
```
Results:
  ✅ Passed:  6/6
  ❌ Failed:  0/6

🎉 All tests passed!
```
✅ **Hardware configured correctly**

```
Results:
  ✅ Passed:  4/6
  ❌ Failed:  2/6

⚠️  Some tests failed.
```
❌ **Check recommendations in output**

---

## Common Issues

### Issue: Wake word not detected
**Solution:**
1. Run Test 2 - check gain levels
2. Lower `WAKE_WORD_SIMILARITY` in `.env`
3. Increase `AUDIO_AMPLIFICATION` if RMS too low

### Issue: Microphone too quiet
**Solution:**
1. Run Test 2 to see current RMS
2. Increase `AUDIO_AMPLIFICATION` in `.env`
3. Test recommends exact value

### Issue: Unit tests fail
**Solution:**
1. Check error message
2. Verify dependencies installed
3. Check `.env` configuration

---

## Success Criteria

### System Ready for Use When:
- ✅ All unit tests pass (40/40)
- ✅ Test 2 shows good gain levels
- ✅ Test 6 (End-to-End) passes
- ✅ No critical errors in logs

### Minimum Passing:
- ✅ Unit tests: 38+ pass (OK if model files missing)
- ✅ Interactive: Test 2 and Test 6 pass

---

## Maintenance

### Run Before Each Release:
```bash
./run_tests.sh all
```

### Run After Config Changes:
```bash
python3 test_interactive.py
```

### Run During Development:
```bash
python3 test_unit.py
```

---

## Statistics

**Total Tests:** 46
- Unit: 40 tests
- Interactive: 6 tests

**Test Time:**
- Unit: ~1 second
- Interactive: ~5-10 minutes
- Total: ~10 minutes

**Lines of Test Code:**
- test_unit.py: ~620 lines
- test_interactive.py: ~660 lines
- Total: ~1,280 lines

**Coverage:**
- Configuration ✅
- System Prompts ✅
- Tool System ✅
- State Machine ✅
- LLM Client ✅
- Audio Processing ✅
- Wake Word Detection ✅
- Speech-to-Text ✅
- End-to-End Pipeline ✅

---

## Next Steps

1. **Run unit tests** to verify software: `python3 test_unit.py`
2. **Run interactive tests** to calibrate hardware: `python3 test_interactive.py`
3. **Adjust settings** based on test recommendations
4. **Verify with Test 6** (End-to-End Pipeline)
5. **Deploy** when all tests pass!

---

For detailed information, see [TESTING.md](TESTING.md).
For quick reference, see [TESTING_QUICK_START.md](TESTING_QUICK_START.md).
