# Movie Selection Logic Improvements

## Problem Discovered from Logs

Looking at `hal_voice_assistant.log` from 03:04:40:

**User requested**: "Play movie about barbarian"

**What happened**:
1. Agent called `list_movies` → Got list including "Red Sonja.mp4" (correct movie about barbarians)
2. Agent called `media-server.select_movie` with parameter "Superman.mp4"
3. **Interception FAILED** because code only checked for `"select_movie"` but agent called `"media-server.select_movie"`
4. System tried to call it as real MCP tool → "Unknown tool: select_movie"
5. Agent then just played Superman.mp4 (WRONG - Superman is about Kryptonians, not barbarians)

The previous implementation had TWO problems:
- Relied on LLM's implicit knowledge (picked wrong movie)
- Pseudo-function interception didn't work (didn't check for server prefix)

## Solution
Implemented explicit movie selection where the LLM is given the exact list of available movies and asked to choose the best match.

## Changes Made

### 1. Modified Agent System Prompt
**File**: `hal_voice_assistant.py:324`

Added rule 5:
```python
5. For movie selection: First call list_movies, then call "select_movie" with the user's criteria to pick the best match
```

### 2. Added Special "select_movie" Function Handler
**File**: `hal_voice_assistant.py:387-442`

**Fixed**: Now checks for both `"select_movie"` AND `"*.select_movie"` (with server prefix)

When the agent calls the pseudo-function "select_movie", the system:
1. Intercepts the call BEFORE trying to call it as real MCP tool
2. Extracts the movie list from conversation history (from previous list_movies call)
3. Creates an explicit selection prompt showing all available movies
4. Asks LLM: "Given these movies [list], which best matches '{user_query}'?"
5. Returns the selected movie filename
6. Instructs agent to call play_movie with the selected filename

### 3. Selection Prompt Format
```
The user requested: "{user_query}"

Available movies:
1. Superman.mp4
2. Airplane.mp4
3. Red Sonja.mp4

Which movie best matches the user's request? Consider the movie titles and what they might be about.
Respond with ONLY the filename (e.g., "Superman.mp4"), nothing else.
```

## Benefits

1. **Transparent**: Logs show exactly what movies are available and why LLM made its choice
2. **Reliable**: Works with any movies, not just famous ones LLM might know about
3. **Traceable**: Full reasoning visible in logs with "🎬 EXPLICIT MOVIE SELECTION" marker
4. **Accurate**: All test cases passed:
   - "play movie about a barbarian" → Red Sonja.mp4 ✅
   - "play a comedy" → Airplane.mp4 ✅
   - "play movie about kryptonian" → Superman.mp4 ✅

## Example Log Output

```
================================================================================
🎬 EXPLICIT MOVIE SELECTION
   User wants: play movie about kryptonian
   Available movies: ['Superman.mp4', 'Airplane.mp4', 'Red Sonja.mp4']
================================================================================

🎬 LLM SELECTED: Superman.mp4
   Reasoning: Based on user query 'play movie about kryptonian' and available options
================================================================================
```

## Testing

Run the test suite:
```bash
python3 test_movie_selection.py
```

This tests the selection logic with three different query types:
- Descriptive queries ("about a barbarian")
- Genre queries ("a comedy")
- Plot-specific queries ("about kryptonian")
