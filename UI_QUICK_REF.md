# UI Config Quick Reference

## Run Demo
```bash
cd /home/hal/hal/voice-kiosk
python3 ui_demo.py
# Open: http://localhost:8080/ui-demo.html
```

## Component Cheat Sheet

### Button
```json
{"type": "button", "name": "Text", "style": "...", "action": {...}}
```

### Text
```json
{"type": "text", "id": "status", "content": "Text here", "style": "..."}
```

### List
```json
{
  "type": "list",
  "id": "list-id",
  "style": "grid-list",
  "autoLoad": {"type": "mcp", "server": "...", "tool": "..."},
  "onSelect": {...}
}
```

### Image
```json
{"type": "image", "src": "/path.png", "alt": "...", "style": {...}}
```

### Container
```json
{
  "type": "container",
  "layout": "horizontal",
  "components": [...]
}
```

### Spacer
```json
{"type": "spacer", "height": "20px"}
```

## Action Cheat Sheet

### Navigate
```json
{"type": "navigate", "target": "screen-id"}
```

### MCP Call
```json
{
  "type": "mcp",
  "server": "media-server",
  "tool": "play_movie",
  "params": {"filename": "movie.mp4"},
  "target": "result-id",
  "onComplete": {...}
}
```

### Popup
```json
{
  "type": "popup",
  "title": "Title",
  "components": [...]
}
```

### Close Popup
```json
{"type": "close_popup"}
```

### Refresh List
```json
{"type": "refresh_list", "target": "list-id"}
```

## Interpolation

- In lists: `{item.property}`
- In selections: `{selected.property}`
- Nested: `{item.user.name}`

Example:
```json
{"content": "Name: {item.name}, Size: {item.size}"}
```

## Common Patterns

### Menu Button
```json
{
  "type": "button",
  "name": "Movies",
  "style": "primary-button",
  "action": {"type": "navigate", "target": "movies-screen"}
}
```

### Back Button
```json
{
  "type": "button",
  "name": "← Back",
  "style": "back-button",
  "action": {"type": "navigate", "target": "home"}
}
```

### Load Data Button
```json
{
  "type": "button",
  "name": "Load",
  "action": {
    "type": "mcp",
    "server": "...",
    "tool": "...",
    "target": "list-id"
  }
}
```

### Selectable List
```json
{
  "type": "list",
  "id": "items",
  "autoLoad": {"type": "mcp", "server": "...", "tool": "..."},
  "onSelect": {
    "type": "popup",
    "title": "Selected",
    "components": [
      {"type": "text", "content": "You picked: {selected.name}"}
    ]
  }
}
```

### Action with Confirmation
```json
{
  "onSelect": {
    "type": "popup",
    "title": "Confirm",
    "components": [
      {"type": "text", "content": "Delete {selected.name}?"},
      {
        "type": "button",
        "name": "Yes",
        "action": {
          "type": "mcp",
          "server": "...",
          "tool": "delete",
          "params": {"id": "{selected.id}"},
          "onComplete": {"type": "close_popup"}
        }
      }
    ]
  }
}
```

### Chained Actions
```json
{
  "type": "mcp",
  "server": "lights",
  "tool": "scan_devices",
  "target": "status",
  "onComplete": {
    "type": "mcp",
    "server": "lights",
    "tool": "list_devices",
    "target": "device-list"
  }
}
```

## Styling Quick Tips

### Named Style
```json
{
  "styles": {
    "big-button": {
      "fontSize": "32px",
      "padding": "30px 60px",
      "backgroundColor": "#667eea"
    }
  }
}
```
Use: `"style": "big-button"`

### Inline Style
```json
"style": {
  "fontSize": "18px",
  "color": "#666",
  "padding": "10px"
}
```

### Touch Optimized
```json
{
  "minWidth": "88px",
  "minHeight": "88px",
  "touchAction": "manipulation",
  "transition": "all 0.2s"
}
```

## File Locations

- Config: `/home/hal/hal/voice-kiosk/ui-config.json`
- Renderer: `/home/hal/hal/voice-kiosk/web/ui-renderer.js`
- Demo: `/home/hal/hal/voice-kiosk/ui_demo.py`
- HTML: `/home/hal/hal/voice-kiosk/web/ui-demo.html`

## Debugging

### Check Config Syntax
```bash
python3 -m json.tool ui-config.json
```

### Browser Console
Press F12 → Console tab
Look for errors in red

### Python Logs
Look for:
- `✅ Loaded UI config`
- `🔧 MCP Call:`
- `✅ MCP Result:`

## MCP Servers

Available servers (check `/home/hal/hal/mcp-servers.json`):

- **media-server**: list_movies, play_movie, pause_playback, stop_playback
- **weather**: get_current_weather, get_weather_forecast
- **lights**: list_devices, turn_on, turn_off, set_color

## Troubleshooting

**Config not loading?**
- Check JSON syntax (commas, quotes)
- Run: `python3 -m json.tool ui-config.json`

**List not populating?**
- Check MCP call works (Python console)
- Check target ID matches list ID
- Check data is array or parseable text

**Button not working?**
- Check action syntax
- Check browser console for errors
- Verify MCP server is connected

**Styles not applying?**
- Use camelCase (backgroundColor not background-color)
- Named styles must be in "styles" section
- Check browser console for CSS errors

## Example Screens

See `ui-config.json` for complete examples:
- Home menu
- Movie browser with selection
- Light control with color picker
- Weather display

## Need More Help?

Read full docs:
- `UI_CONFIG_GUIDE.md` - Complete reference
- `UI_SYSTEM_SUMMARY.md` - Architecture overview
