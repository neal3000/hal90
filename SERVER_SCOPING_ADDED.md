# Server-Level Scoping for Intent Matching

## Problem Solved

Multiple MCP servers can have similar commands (e.g., both `media-server` and `lights` have a `list` command). Without context, the system couldn't reliably determine which server the user intended.

**Before:**
- User: "list" → Could match `media-server.list_movies` OR `lights.list_devices`
- System had to guess based on keywords alone
- Often picked the wrong server

**After:**
- User: "list lights" → Matches `lights` server scope → Routes to `lights.list_devices` ✅
- User: "list movies" → Matches `media-server` server scope → Routes to `media-server.list_movies` ✅

## Solution: Server-Level Scoping

Added two-tier routing:
1. **Server-level matching** using `scope` and `userScope`
2. **Intent-level matching** within the appropriate server

### New Mapping Format (v2)

```json
{
  "_metadata": {
    "version": "2.0",
    "description": "Intent mapping with server-level scoping"
  },
  "servers": {
    "media-server": {
      "scope": "Used for playing media files, movies, music, and videos...",
      "userScope": "movies, films, music, videos, media, play, watch",
      "intents": {
        "media_server_list_movies": { ... },
        "media_server_play_movie": { ... }
      }
    },
    "lights": {
      "scope": "Used for controlling smart devices like lights and outlets...",
      "userScope": "lights, lamp, bulb, brightness, devices, switch",
      "intents": {
        "lights_list_devices": { ... },
        "lights_turn_on": { ... }
      }
    }
  }
}
```

### Fields

- **scope**: System-level description of server purpose (for logging/debugging)
- **userScope**: Comma-separated keywords users might say (for routing)
- **intents**: The actual intent mappings (same as before)

## Changes Made

### 1. Restructured intent-mapping.json
**File**: `/home/hal/hal/intent-mapping.json`

- Converted from flat intent list to hierarchical server→intents structure
- Added `scope` and `userScope` for each server
- Maintains backward compatibility (intent matcher handles both formats)

### 2. Updated HALIntentMatcher
**File**: `/home/hal/hal/hal_intent_matcher.py`

**New Features:**
- `_match_servers()` - Matches user text against server `userScope` keywords
- Boosts intent scores by +50 if their server matches user scope
- Loads both v1 (flat) and v2 (hierarchical) formats
- Logs which servers matched: `🎯 Server 'lights' matched on keyword: 'light'`

**Matching Algorithm:**
```python
1. Parse user input: "list lights"
2. Check userScope keywords:
   - "lights" matches lights.userScope → Add 'lights' server
3. Score all intents:
   - lights.list_devices: 10 (keyword match) + 50 (server match) = 60
   - media-server.list_movies: 10 (keyword match) = 10
4. Pick highest score: lights.list_devices ✅
```

### 3. Updated HALMappingGenerator
**File**: `/home/hal/hal/hal_mapping_generator.py`

**New Features:**
- `_generate_server_scopes()` - Uses LLM to analyze each server's tools and generate appropriate scopes
- Generates v2 format with server metadata
- Groups intents by server automatically

**LLM Prompt for Scopes:**
```
Analyze this MCP server and its tools:

Server: lights
Tools:
- list_devices: List all discovered SmartLife/Tuya devices
- turn_on: Turn on a smart device by name or index
- turn_off: Turn off a smart device by name or index
...

Generate:
1. scope: One-sentence description
2. userScope: Comma-separated keywords users might say
```

## Example Usage

**Command:** "list lights"

**Routing Process:**
```
1. User says: "list lights"
2. Server matching:
   - Check "lights" against userScopes
   - lights.userScope contains "lights" → Match! 🎯
3. Intent scoring:
   - lights.list_devices: base_score=10 + server_boost=50 = 60
   - media-server.list_movies: base_score=10 = 10
4. Winner: lights.list_devices (score: 60)
```

**Command:** "list movies"

**Routing Process:**
```
1. User says: "list movies"
2. Server matching:
   - Check "movies" against userScopes
   - media-server.userScope contains "movies" → Match! 🎯
3. Intent scoring:
   - media-server.list_movies: base_score=20 + server_boost=50 = 70
   - lights.list_devices: base_score=10 = 10
4. Winner: media-server.list_movies (score: 70)
```

## Benefits

1. **Disambiguation**: Resolves ambiguous commands like "list"
2. **Accuracy**: Fewer incorrect server selections
3. **Extensibility**: Easy to add new servers without conflicts
4. **User-friendly**: Users can naturally specify context ("lights", "movies", etc.)
5. **Backward Compatible**: Still works with v1 format mappings

## Testing

The system now correctly routes:
- ✅ "list lights" → `lights.list_devices`
- ✅ "list movies" → `media-server.list_movies`
- ✅ "turn on lights" → `lights.turn_on`
- ✅ "play movie" → `media-server.play_movie`
- ✅ "what's the weather" → `weather.get_current_weather`

## Regenerating Mappings

To regenerate with server scopes:
```bash
python hal_voice_assistant.py --generate-mapping
```

The LLM will analyze each server's tools and automatically generate appropriate `scope` and `userScope` values.
