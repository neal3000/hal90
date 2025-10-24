# Config-Driven UI System

A flexible, touch-optimized UI system for HAL voice assistant that generates interfaces from JSON configuration.

## Overview

This system allows you to define complete user interfaces in JSON without writing HTML/CSS/JavaScript. Perfect for kiosk applications and touch screens.

## Quick Start

### 1. Run the Demo

```bash
cd /home/hal/hal/voice-kiosk
python3 ui_demo.py
```

Open browser to: http://localhost:8080/ui-demo.html

### 2. Edit the Config

Edit `ui-config.json` to customize the interface.

### 3. Test

Changes to `ui-config.json` take effect on page reload (F5).

## Configuration Structure

```json
{
  "version": "1.0",
  "initial_screen": "home",
  "styles": { ... },
  "screens": { ... }
}
```

## Component Types

### 1. Button

```json
{
  "type": "button",
  "name": "Movies",
  "style": "primary-button",
  "action": {
    "type": "navigate",
    "target": "movies-screen"
  }
}
```

**Properties**:
- `name`: Button text
- `style`: Named style or inline style object
- `action`: What happens when clicked

### 2. Text

```json
{
  "type": "text",
  "id": "status-text",
  "content": "Ready",
  "style": "heading"
}
```

**Properties**:
- `content`: Text to display (supports `{item.name}` interpolation)
- `id`: Optional ID for targeting with actions
- `style`: Named style or inline style object

### 3. List

```json
{
  "type": "list",
  "id": "movie-list",
  "style": "grid-list",
  "autoLoad": {
    "type": "mcp",
    "server": "media-server",
    "tool": "list_movies",
    "params": {}
  },
  "itemTemplate": {
    "type": "card",
    "components": [...]
  },
  "onSelect": {
    "type": "popup",
    "components": [...]
  }
}
```

**Properties**:
- `id`: Required - used to populate list
- `style`: List container styling
- `autoLoad`: Action to run on screen load
- `itemTemplate`: How to render each item
- `onSelect`: Action when item is clicked

### 4. Image

```json
{
  "type": "image",
  "src": "/icons/bulb.png",
  "alt": "Light bulb",
  "style": {
    "width": "64px",
    "height": "64px"
  }
}
```

### 5. Container

```json
{
  "type": "container",
  "layout": "horizontal",
  "wrap": true,
  "components": [
    {...},
    {...}
  ]
}
```

**Layouts**:
- `horizontal`: Flexbox row
- `vertical`: Flexbox column

### 6. Spacer

```json
{
  "type": "spacer",
  "height": "20px"
}
```

## Action Types

### Navigate

Switch to another screen:

```json
{
  "type": "navigate",
  "target": "movies-screen"
}
```

### MCP Call

Call MCP tool and populate target:

```json
{
  "type": "mcp",
  "server": "media-server",
  "tool": "list_movies",
  "params": {},
  "target": "movie-list",
  "onComplete": {
    "type": "navigate",
    "target": "home"
  }
}
```

**Properties**:
- `server`: MCP server name
- `tool`: Tool to call
- `params`: Parameters (supports interpolation)
- `target`: ID of element to populate with result
- `onComplete`: Optional action to run after success

### Popup

Show modal popup:

```json
{
  "type": "popup",
  "title": "Confirm",
  "components": [
    {
      "type": "text",
      "content": "Are you sure?"
    },
    {
      "type": "button",
      "name": "Yes",
      "action": {"type": "close_popup"}
    }
  ]
}
```

### Close Popup

```json
{
  "type": "close_popup"
}
```

### Refresh List

Reload list data:

```json
{
  "type": "refresh_list",
  "target": "device-list"
}
```

## Template Interpolation

Use `{variable.property}` to insert data:

### In Lists

```json
{
  "type": "text",
  "content": "{item.name}"
}
```

Context: `{item}` = current list item

### In Selections

```json
{
  "type": "button",
  "name": "Play",
  "action": {
    "type": "mcp",
    "server": "media-server",
    "tool": "play_movie",
    "params": {
      "filename": "{selected.name}"
    }
  }
}
```

Context: `{selected}` = clicked list item

## Styling

### Named Styles

Define in `styles` section:

```json
{
  "styles": {
    "primary-button": {
      "backgroundColor": "#667eea",
      "fontSize": "24px",
      "padding": "20px 40px"
    }
  }
}
```

Use by name:

```json
{
  "type": "button",
  "style": "primary-button"
}
```

### Inline Styles

```json
{
  "type": "text",
  "style": {
    "fontSize": "18px",
    "color": "#666"
  }
}
```

**Note**: Use camelCase for property names (e.g., `backgroundColor`, not `background-color`)

## Touch Optimization

### Recommended Button Sizes

```json
{
  "minWidth": "88px",
  "minHeight": "88px",
  "touchAction": "manipulation"
}
```

Apple recommends 44x44pt minimum (88px on retina).

### Prevent Double-Tap Zoom

```css
touchAction: "manipulation"
```

### Active State Feedback

```json
{
  "transition": "all 0.2s"
}
```

Renderer automatically adds scale transform on press.

## Common Patterns

### Menu Screen

```json
{
  "type": "container",
  "layout": "vertical",
  "components": [
    {"type": "button", "name": "Option 1", "action": {...}},
    {"type": "spacer", "height": "20px"},
    {"type": "button", "name": "Option 2", "action": {...}}
  ]
}
```

### List with Actions

```json
{
  "type": "list",
  "id": "items",
  "itemTemplate": {
    "components": [
      {"type": "text", "content": "{item.name}"},
      {
        "type": "container",
        "layout": "horizontal",
        "components": [
          {"type": "button", "name": "Edit", "action": {...}},
          {"type": "button", "name": "Delete", "action": {...}}
        ]
      }
    ]
  }
}
```

### Confirmation Dialog

```json
{
  "type": "popup",
  "title": "Confirm",
  "components": [
    {"type": "text", "content": "Delete {selected.name}?"},
    {
      "type": "container",
      "layout": "horizontal",
      "components": [
        {
          "type": "button",
          "name": "Delete",
          "action": {
            "type": "mcp",
            "server": "...",
            "tool": "delete",
            "params": {"id": "{selected.id}"},
            "onComplete": {"type": "close_popup"}
          }
        },
        {
          "type": "button",
          "name": "Cancel",
          "action": {"type": "close_popup"}
        }
      ]
    }
  ]
}
```

### Loading State

```json
{
  "type": "list",
  "id": "items",
  "autoLoad": {
    "type": "mcp",
    "server": "...",
    "tool": "list_items"
  }
}
```

Shows "No items" until data loads.

## Advanced Features

### Action Chaining

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

First scans, then lists devices.

### Complex Templates

```json
{
  "itemTemplate": {
    "type": "card",
    "components": [
      {"type": "image", "src": "{item.poster}"},
      {"type": "text", "content": "{item.name}"},
      {"type": "text", "content": "{item.year}"},
      {
        "type": "container",
        "layout": "horizontal",
        "components": [
          {"type": "button", "name": "Play", "action": {...}},
          {"type": "button", "name": "Info", "action": {...}}
        ]
      }
    ]
  }
}
```

## Troubleshooting

### Config Not Loading

Check browser console (F12) for errors. Common issues:
- JSON syntax error (missing comma, quotes)
- File path incorrect
- Server not running

### List Not Populating

1. Check MCP call works: look at Python console
2. Check target ID matches list ID
3. Check data format (should be array or parseable text)

### Styles Not Applied

- Named styles must be defined in `styles` section
- Inline styles use camelCase
- Check browser console for CSS errors

### Touch Not Working

- Ensure `touchAction: "manipulation"` is set
- Check button size meets minimum (88px)
- Test on actual touch device (mouse hover doesn't exist on touch)

## Integration with hal_voice_assistant.py

To integrate into main voice assistant:

1. Add `load_ui_config()` and `call_mcp()` functions
2. Change Eel start page to `ui-demo.html`
3. UI will coexist with voice interface

Both systems can call MCP simultaneously.

## File Structure

```
voice-kiosk/
├── ui-config.json           # UI definition
├── ui_demo.py               # Standalone demo
├── web/
│   ├── ui-demo.html         # HTML page
│   └── ui-renderer.js       # JavaScript renderer
└── UI_CONFIG_GUIDE.md       # This file
```

## Next Steps

1. **Customize Styles**: Edit colors, fonts, sizes in `styles` section
2. **Add Screens**: Create new screens for different functions
3. **Test on Touch**: Deploy to Pi with touch screen
4. **Add Icons**: Create `/web/icons/` directory for images
5. **Integrate Voice**: Merge with `hal_voice_assistant.py`

## Examples

See `ui-config.json` for complete examples of:
- ✅ Multi-screen navigation
- ✅ MCP integration
- ✅ List selection with popups
- ✅ Action chaining
- ✅ Touch-optimized layouts
- ✅ Color pickers
- ✅ Playback controls

## Support

For questions or issues, check:
1. Browser console (F12) for JavaScript errors
2. Python console for MCP errors
3. This guide for configuration reference
