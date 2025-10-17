# Testing Quick Start Guide

## TL;DR

```bash
# Run all automated tests (fast, no mic needed)
python3 test_unit.py

# Run hardware tests (requires microphone)
python3 test_interactive.py

# Run everything
./run_tests.sh all
```

---

## When to Run Which Tests

### Just Installed? Start Here:
```bash
# 1. Verify software components
python3 test_unit.py

# 2. Calibrate your microphone
python3 test_interactive.py
# Pay attention to Test 2 (gain calibration)
```

### Wake Word Not Working?
```bash
python3 test_interactive.py
# Focus on:
# - Test 2: Check microphone gain
# - Test 3: Test wake word detection
```

### Before Going Live:
```bash
# Run the complete pipeline test
python3 test_interactive.py
# Make sure Test 6 (End-to-End) passes!
```

---

## Test Cheat Sheet

### Non-Interactive Tests (`test_unit.py`)
| Test Category | What It Checks | Time |
|---------------|----------------|------|
| Configuration | .env settings load correctly | < 1s |
| System Prompts | LLM prompts generated properly | < 1s |
| Tools | All tools load and execute | 1-2s |
| State Machine | App states transition correctly | < 1s |
| Audio Math | Amplification calculations work | < 1s |

**Total Time:** ~5 seconds

### Interactive Tests (`test_interactive.py`)
| Test # | Name | What You Do | Time |
|--------|------|-------------|------|
| 1 | Device Detection | Nothing (automatic) | 5s |
| 2 | **Gain Calibration** ⭐ | Speak for 5 seconds | 30s |
| 3 | Wake Word | Say wake word | 30s |
| 4 | Recording | Speak a sentence | 30s |
| 5 | Speech-to-Text | Say test phrase | 1min |
| 6 | **Full Pipeline** ⭐ | Complete interaction | 1min |

**Total Time:** ~5 minutes

---

## Most Important Tests

### 🔥 Test 2: Microphone Gain Calibration
**Why:** Sets correct amplification for your microphone
**Goal:** Get amplified RMS between 2000-30000
**If fails:** Adjust `AUDIO_AMPLIFICATION` in `.env`

### 🔥 Test 6: End-to-End Pipeline
**Why:** Validates complete system works
**What:** Wake word → Record → Transcribe
**If passes:** System is ready to use!

---

## Quick Fixes

### "Wake word not detected"
```bash
# Lower the similarity threshold in .env
WAKE_WORD_SIMILARITY=0.4  # was 0.6
```

### "Microphone too quiet"
```bash
# Increase amplification in .env
AUDIO_AMPLIFICATION=500.0  # was 300.0
```

### "Microphone too loud/clipping"
```bash
# Decrease amplification in .env
AUDIO_AMPLIFICATION=150.0  # was 300.0
```

### "Transcription fails"
```bash
# Try smaller/faster model in .env
WHISPER_MODEL=tiny.en  # was base.en
```

---

## Reading Test Output

### Unit Tests
```
Ran 40 tests in 0.132s
OK (skipped=2)
```
✅ = Ready to proceed

```
FAILED (failures=1, skipped=2)
```
❌ = Check error message, fix issue

### Interactive Tests
```
✅ PASS: Microphone Gain Calibration
  Amplified RMS: 15234.5
  Status: ✅ GOOD - Levels are optimal
```
✅ = Perfect!

```
❌ FAIL: Wake Word Detection
  Wake word not detected - check gain levels
```
❌ = Follow the recommendation shown

---

## CI/CD

Unit tests can run in CI/CD:
```yaml
- name: Test
  run: python3 test_unit.py
```

Interactive tests **cannot** run in CI/CD (need hardware).

---

## Need Help?

1. Read the error message carefully
2. Check recommendations in test output
3. See [TESTING.md](TESTING.md) for detailed guide
4. Check `voice_kiosk.log` for more details

---

## Examples

### Example 1: First Time Setup
```bash
# Step 1: Check software
python3 test_unit.py
# Should see: OK (skipped=2)

# Step 2: Test hardware
python3 test_interactive.py
# Follow prompts, speak when asked

# Step 3: If Test 2 shows low gain:
# Edit .env: AUDIO_AMPLIFICATION=500.0
# Re-run: python3 test_interactive.py
```

### Example 2: Debug Wake Word
```bash
# Run interactive tests
python3 test_interactive.py

# If Test 2 passes but Test 3 fails:
# - Lower WAKE_WORD_SIMILARITY to 0.4
# - Re-run tests
```

### Example 3: Quick Validation
```bash
# Before demo/deployment
./run_tests.sh all

# Both should pass:
# ✅ Unit tests: PASSED
# ✅ Interactive tests: PASSED
```

---

That's it! Start with `python3 test_unit.py` and go from there.
