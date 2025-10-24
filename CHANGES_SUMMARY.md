# Movie Selection Fix - Changes Summary

## Issues Found from Logs

From `hal_voice_assistant.log` at 03:16:48:
- User asked: "Play movie about barbarian"
- System selected: **Millennium.mp4** (WRONG)
- Should have selected: **Red Sonja.mp4** (CORRECT)

## Root Causes

1. **Pseudo-function interception was broken** (FIXED)
   - Code only checked for `"select_movie"`
   - Agent called `"media-server.select_movie"` (with server prefix)
   - Interception failed → tried to call as real MCP tool → "Unknown tool"

2. **Selection prompt was too complex** (FIXED)
   - Original had numbered lists, multiple IMPORTANT instructions
   - Too much structure confused the small model
   - User tested `exaone3.5:2.4b` with simple prompt → worked correctly!

## Changes Made

### 1. Fixed Pseudo-function Interception
**File**: `hal_voice_assistant.py:387`

**Before:**
```python
if function_name == "select_movie":
```

**After:**
```python
if function_name == "select_movie" or function_name.endswith(".select_movie"):
```

### 2. Simplified Selection Prompt
**File**: `hal_voice_assistant.py:410-415`

**Before:**
```
The user requested: "Play movie about barbarian."

Available movies:
1. Airplane!.mp4
2. Millennium.mp4
3. Nobody.mp4
4. Red Sonja.mp4
5. Superman.mp4

Based ONLY on the movie titles above, which movie best matches the user's request?

IMPORTANT: Choose from the list above. Do NOT make up movies. Consider what each title suggests the movie is about.

Respond with ONLY the exact filename from the list (e.g., "Red Sonja.mp4"), nothing else.
```

**After:**
```
Of the movies "Airplane!.mp4", "Millennium.mp4", "Nobody.mp4", "Red Sonja.mp4", "Superman.mp4", which one best matches: Play movie about barbarian.

Respond with only the filename from the list above, nothing else.
```

**Why**: User tested `exaone3.5:2.4b` and found simpler prompts work better. The model correctly identified Red Sonja when given: "of the movies "superman","airplane","red sonja" which one is about a barbarian"

### 3. Enhanced Logging
**File**: `hal_voice_assistant.py:421-435`

Now logs:
- Full selection prompt sent to LLM
- Model name used for selection
- Complete LLM response (not just extracted filename)

### 4. Fixed Example Movie Names in System Prompt
**File**: `hal_voice_assistant.py:322-324`

**Before:** Used "Superman.mp4" as example (could be a real movie)
**After:** Uses "nonexistantmovie.mp4" (canary value)

If "nonexistantmovie.mp4" is ever selected, we know the agent is using examples from the prompt instead of real data.

## Testing

Ready to test! The new prompt format matches the user's successful test case.

Expected behavior:
1. User: "play movie about barbarian"
2. Intent matcher detects "about" → triggers agent mode
3. Agent calls `list_movies` → gets movie list
4. Agent calls `select_movie` (or `media-server.select_movie`)
5. Code intercepts (now works with server prefix!)
6. Simplified prompt sent to LLM
7. Should select: **Red Sonja.mp4**
8. Agent calls `play_movie` with correct filename
9. Logs show full selection prompt and reasoning
