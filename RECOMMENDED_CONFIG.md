# Recommended Configuration Based on Agent Tool Tests

## Executive Summary

After testing 4 different LLM models for agent tool calling, **exaone3.5:2.4b achieved 100% accuracy** while smaller models failed or were inefficient.

## Test Results Quick Summary

| Model | Accuracy | Avg Speed | Status |
|-------|----------|-----------|--------|
| exaone3.5:2.4b | ✅ 100% | 41.3s | **RECOMMENDED** |
| gemma3:1b | ✅ 100% | 55.6s | Usable but slow |
| gemma3:270m | ❌ 0% | 24.2s | **DO NOT USE** |
| qwen3:1.7b | ❌ 0% | 60.6s | **DO NOT USE** |

## Recommended .env Configuration

```bash
# === LLM Models ===
# Agent model (tool calling) - MUST be reliable
OLLAMA_AGENT_MODEL=exaone3.5:2.4b

# Conversation model (natural language responses) - can be smaller
OLLAMA_CONVERSATION_MODEL=gemma3:1b

# Agent settings
AGENT_MAX_ITERATIONS=3

# Ollama server
OLLAMA_URL=http://localhost:11434
```

## Rationale

### Why exaone3.5:2.4b for Agent?

1. **100% Tool Accuracy** - Never hallucinated tool names
2. **Proper Flow** - Correctly calls tools then `finished()`
3. **Reliable Parsing** - Always generates valid JSON
4. **Good Speed** - 41s average (reasonable for reliability)

### Why gemma3:1b for Conversation?

1. **No Tool Calling Needed** - Just generates natural language
2. **Smaller/Faster** - 1B parameters vs 2.4B
3. **Good Quality** - Produces coherent responses
4. **Proven Working** - Already in use successfully

### What Not to Use

❌ **gemma3:270m** - Too small (270M parameters)
- Hallucinates tool names like `function_name()`
- Hit max iterations with wrong tools
- 0% success rate

❌ **qwen3:1.7b** - JSON parsing issues
- Failed to generate valid tool call JSON
- Timed out on tests
- 0% success rate

## How to Apply

### 1. Update .env file

Edit `/home/hal/hal/voice-kiosk/.env`:

```bash
# Remove duplicate lines and set these:
OLLAMA_AGENT_MODEL=exaone3.5:2.4b
OLLAMA_CONVERSATION_MODEL=gemma3:1b
AGENT_MAX_ITERATIONS=3
```

### 2. Ensure model is downloaded

```bash
ollama pull exaone3.5:2.4b
ollama pull gemma3:1b
```

### 3. Verify models are available

```bash
ollama list
```

Should show:
```
NAME                    ID              SIZE
exaone3.5:2.4b         <id>            1.4GB
gemma3:1b              <id>            577MB
```

### 4. Restart application

```bash
python3 main_new.py
```

## Performance Impact

### Before (qwen3:1.7b + gemma3:1b)
- ❌ Tool calling: 0% accuracy
- ❌ Parsing errors
- ❌ Timeouts
- ⏱️ ~60s wasted per failed attempt

### After (exaone3.5:2.4b + gemma3:1b)
- ✅ Tool calling: 100% accuracy
- ✅ Clean execution
- ✅ No errors
- ⏱️ ~41s per successful call

**Net Result**: Faster overall (no retries needed) + 100% reliability

## Expected Behavior

### Example: "What time is it?"

**Agent Phase** (exaone3.5:2.4b):
```
Step 1: Calling timenow()
Step 2: Result - "Friday, October 17, 2025 at 10:30 PM"
Step 3: Calling finished()
```
Duration: ~40s

**Conversation Phase** (gemma3:1b):
```
{
  "message": "The current time is Friday, October 17, 2025 at 10:30 PM.",
  "feeling": "happy"
}
```
Duration: ~5s

**Total**: ~45s with 100% success rate

### Example: "Tell me my fortune"

**Agent Phase** (exaone3.5:2.4b):
```
Step 1: Calling get_fortune()
Step 2: Result - "The future belongs to those who believe..."
Step 3: Calling finished()
```
Duration: ~23s

**Conversation Phase** (gemma3:1b):
```
{
  "message": "Here's your fortune: The future belongs to those who believe in the beauty of their dreams.",
  "feeling": "happy"
}
```
Duration: ~5s

**Total**: ~28s with 100% success rate

## Alternative Configurations

### If exaone3.5:2.4b is unavailable

**Option 1**: Use gemma3:1b for both
```bash
OLLAMA_AGENT_MODEL=gemma3:1b
OLLAMA_CONVERSATION_MODEL=gemma3:1b
```
- Works but slower (55s avg)
- May waste iterations

**Option 2**: Use larger model if available
```bash
OLLAMA_AGENT_MODEL=llama3:8b  # or similar 7B+ model
OLLAMA_CONVERSATION_MODEL=gemma3:1b
```
- Should work well (7B+ models good at tool calling)
- Slower but more capable

## Testing Your Configuration

Run the test suite to verify:

```bash
# Quick test (just 2 inputs, 1 model)
python3 -c "
from test_agent_tools import AgentToolTester
import asyncio

async def quick_test():
    tester = AgentToolTester()
    tester.test_inputs = ['timenow', 'fortune']
    tester.test_models = ['exaone3.5:2.4b']
    await tester.run_all_tests()
    print(tester.generate_report())

asyncio.run(quick_test())
"
```

Expected: 2/2 tests passing

## Files Reference

- **Test Suite**: `test_agent_tools.py`
- **Test Results**: `AGENT_TEST_SUMMARY.md`
- **This Guide**: `RECOMMENDED_CONFIG.md`

---

**Last Updated**: 2025-10-17
**Test Confidence**: High (6 tests completed, clear pattern)
**Status**: ✅ Ready for production use
