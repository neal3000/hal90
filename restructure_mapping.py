#!/usr/bin/env python3
"""
Restructure intent-mapping.json to include server-level scopes
"""
import json
from pathlib import Path

# Load current mapping
mapping_file = Path(__file__).parent.parent / 'intent-mapping.json'
with open(mapping_file, 'r') as f:
    old_mapping = json.load(f)

# Define server scopes
server_metadata = {
    "media-server": {
        "scope": "Used for playing media files, movies, music, and videos. Controls video playback including play, pause, stop, seek, and chapter navigation.",
        "userScope": "movies, films, music, videos, media, play, watch, playback, video, movie, film"
    },
    "weather": {
        "scope": "Used for finding weather information, forecasts, and current conditions for any location.",
        "userScope": "weather, temperature, forecast, rain, sunny, cloudy, conditions, climate"
    },
    "lights": {
        "scope": "Used for controlling smart home devices like lights, lamps, bulbs, and outlets. Can turn on/off, change colors, and check status.",
        "userScope": "lights, lamp, bulb, brightness, smart device, outlet, switch, color, devices, light"
    }
}

# Group intents by server
intents_by_server = {}
for intent_name, intent_data in old_mapping.items():
    server = intent_data.get("server", "unknown")
    if server not in intents_by_server:
        intents_by_server[server] = {}
    intents_by_server[server][intent_name] = intent_data

# Create new structure
new_mapping = {
    "_metadata": {
        "version": "2.0",
        "description": "Intent mapping with server-level scoping for better command routing"
    },
    "servers": {}
}

# Add each server with its metadata and intents
for server, intents in intents_by_server.items():
    server_info = server_metadata.get(server, {
        "scope": f"Server for {server} functionality",
        "userScope": server
    })

    new_mapping["servers"][server] = {
        "scope": server_info["scope"],
        "userScope": server_info["userScope"],
        "intents": intents
    }

# Save new mapping
output_file = Path(__file__).parent.parent / 'intent-mapping-v2.json'
with open(output_file, 'w') as f:
    json.dump(new_mapping, f, indent=2)

print(f"✅ Created new mapping: {output_file}")
print(f"📊 Servers: {len(new_mapping['servers'])}")
for server, data in new_mapping['servers'].items():
    print(f"   - {server}: {len(data['intents'])} intents")
print(f"\n💡 Review the file, then:")
print(f"   mv {output_file} {mapping_file}")
