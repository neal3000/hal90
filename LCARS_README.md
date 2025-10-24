# HAL LCARS Interface - Star Trek TNG Theme

A Star Trek: The Next Generation inspired interface for the HAL voice assistant control system.

## What's New

Your config-driven UI now has a **full LCARS (Library Computer Access/Retrieval System)** theme, matching the iconic Star Trek TNG aesthetic.

## Features

✅ **Authentic LCARS Design**
- Rounded panel corners (signature LCARS look)
- Classic TNG color palette (orange, blue, violet, red, butterscotch)
- Data cascade animations (scrolling numbers)
- Curved button shapes
- LCARS typography and spacing

✅ **Touch-Optimized**
- Large touch targets (60px+ height)
- Active state feedback
- No hover dependencies
- Touch sound effects (LCARS beeps)

✅ **Full Integration**
- Uses same `ui-config.json` as regular UI
- Same MCP backend
- All features work (buttons, lists, popups, navigation)
- Just different styling!

## Quick Start

### Run LCARS Demo

```bash
cd /home/hal/hal/voice-kiosk
python3 ui_demo_lcars.py
```

Open browser to: **http://localhost:8080/ui-lcars.html**

## Files

### New Files
- `web/ui-lcars.html` - LCARS themed HTML wrapper
- `web/ui-renderer-lcars.js` - LCARS-specific renderer
- `ui_demo_lcars.py` - Demo launcher

### Uses Existing
- `ui-config.json` - Same config file (no changes needed!)
- `theme/assets/classic.css` - Original LCARS CSS
- `theme/assets/beep2.mp3` - LCARS beep sound

## LCARS Color Palette

The interface uses authentic TNG colors:

| Color | Hex | Usage |
|-------|-----|-------|
| **Orange** | `#f90` | Primary buttons, text |
| **Blue** | `#89f` | Headings, accents |
| **Violet** | `#c9f` | Back buttons, labels |
| **Red** | `#c44` | Danger/stop actions |
| **Butterscotch** | `#f96` | Action buttons |
| **Gold** | `#fa0` | Special accents |

## Button Styles

The renderer automatically maps your config styles to LCARS classes:

| Config Style | LCARS Appearance |
|--------------|------------------|
| `primary-button` | Orange rounded button |
| `back-button` | Violet compact button |
| `action-button` | Butterscotch button |
| `secondary-button` | Blue button |

## Example Config

Your existing `ui-config.json` works as-is! The LCARS renderer applies theme automatically.

```json
{
  "type": "button",
  "name": "Movies",
  "style": "primary-button",
  "action": {"type": "navigate", "target": "movies-screen"}
}
```

Becomes: **Large orange LCARS button with "MOVIES" text**

## Screen Layout

### LCARS Frame Elements

```
┌─────────────────────────────────────────┐
│ HAL    LCARS • CONTROL    [Colored Bars]│ ← Top frame
├───────┬─────────────────────────────────┤
│ 03    │                                 │
│ 04    │  Your Dynamic Content Here      │
│ 05    │  (Buttons, Lists, etc.)         │ ← Main area
│ 06    │                                 │
│ 07    │                                 │
│ 08    │                                 │
│ 09    │                                 │
│ 10    │                                 │
├───────┴─────────────────────────────────┤
│ Footer                    [Colored Bars]│ ← Bottom frame
└─────────────────────────────────────────┘
```

### Sidebar Panels

The left sidebar panels are decorative but labeled:
- **03** - NCC1701 (Enterprise registry)
- **04** - MEDIA
- **05** - LIGHTS
- **06** - WEATHER
- **07** - SENSORS
- **08** - CMPTR (Computer)
- **09** - AUX (Auxiliary)
- **10** - SYS (System)

## Component Appearance

### Buttons
- Rounded capsule shape (30px border-radius)
- Bold uppercase text
- Letter spacing for readability
- Color-coded by function
- Touch feedback (scale + brightness)
- LCARS beep on press

### Lists
- Grid layout with rounded items
- Blue left border accent
- Title + subtitle formatting
- Hover/touch effects
- "NO DATA AVAILABLE" placeholder

### Text
- Uppercase headings (blue)
- Orange body text
- Status boxes with colored borders
- LCARS typography

### Popups
- Black background
- Blue border with glow
- Centered modal
- Semi-transparent overlay

## Sound Effects

The interface plays authentic LCARS beeps on:
- Button presses
- Navigation
- Popup open/close

Sounds are from the original LCARS theme (`beep2.mp3`).

## Customization

### Change Colors

Edit `web/ui-lcars.html` CSS variables:

```css
:root {
    --lcars-orange: #f90;  /* Primary color */
    --lcars-blue: #89f;    /* Headings */
    --lcars-violet: #c9f;  /* Accents */
    /* ... etc ... */
}
```

### Adjust Button Sizes

```css
.lcars-button {
    padding: 15px 40px;     /* Increase for larger */
    font-size: 1.2rem;      /* Increase for bigger text */
    min-width: 200px;       /* Minimum width */
    min-height: 60px;       /* Minimum height */
}
```

### Change Layout

The LCARS frame uses the `classic-standard` layout from the theme. To use a different layout:

1. Check `/home/hal/hal/voice-kiosk/theme/` for other options:
   - `classic-ultra.html` - More elaborate
   - `nemesis-blue-standard.html` - Blue theme
   - `lower-decks.html` - Modern animated style

2. Copy the HTML structure to `ui-lcars.html`

3. Update CSS link if needed

## Differences from Regular UI

| Feature | Regular UI | LCARS UI |
|---------|-----------|----------|
| **Theme** | Modern gradient | Star Trek TNG |
| **Colors** | Purple gradient | Orange/Blue/Violet |
| **Buttons** | Rounded squares | Capsule shapes |
| **Typography** | Clean sans-serif | Bold uppercase |
| **Sounds** | None | LCARS beeps |
| **Frame** | Simple container | LCARS panels |
| **Config** | Same `ui-config.json` | Same `ui-config.json` |

## Comparison

### Regular Demo
```bash
python3 ui_demo.py  # Modern clean interface
# http://localhost:8080/ui-demo.html
```

### LCARS Demo
```bash
python3 ui_demo_lcars.py  # Star Trek TNG interface
# http://localhost:8080/ui-lcars.html
```

**Both use the same config and backend!**

## Tips

### 1. Touch Screen
- LCARS was designed for touch screens
- All buttons meet 60px+ minimum
- Active states provide clear feedback

### 2. Fullscreen Mode
Press **F11** in browser for immersive kiosk experience.

### 3. Custom Labels
Edit the sidebar panel labels in `ui-lcars.html`:

```html
<div class="panel-4">04<span class="hop">-MEDIA</span></div>
<div class="panel-5">05<span class="hop">-LIGHTS</span></div>
```

Change `-MEDIA`, `-LIGHTS`, etc. to your preferences.

### 4. Banner Text
Change the top banner:

```html
<div class="banner">LCARS &#149; CONTROL</div>
```

Replace `CONTROL` with any text (e.g., `ENTERPRISE`, `VOYAGER`, `HAL`).

### 5. Data Cascade
The animated scrolling numbers are in the HTML. They're purely decorative but add authenticity. To disable:

```css
.data-cascade-wrapper {
    display: none;
}
```

## Integration with Voice Assistant

To use LCARS interface with full voice assistant:

1. Add Eel functions to `hal_voice_assistant.py`:
   ```python
   @eel.expose
   def load_ui_config():
       with open('ui-config.json', 'r') as f:
           return json.load(f)

   @eel.expose
   def call_mcp(server, tool, params):
       # ... existing MCP call code ...
   ```

2. Change start page:
   ```python
   eel.start('ui-lcars.html', size=(1280, 800))
   ```

3. Both voice and LCARS touch interface work simultaneously!

## Troubleshooting

### No LCARS Theme
- Check browser console for CSS loading errors
- Verify `theme/assets/classic.css` exists
- Check relative paths in HTML

### No Sounds
- Browser may block autoplay
- User interaction required first
- Check `theme/assets/beep2.mp3` exists

### Styling Issues
- Clear browser cache
- Check CSS specificity conflicts
- Verify LCARS classes applied correctly

## Easter Eggs

The LCARS theme includes some fun details:

- **Panel 03**: `NCC1701` - USS Enterprise registry
- **Panel numbers**: Reference classic Trek episodes
- **Data cascade**: Includes `LV426` (Aliens reference!)
- **Panel text**: `8675309` (80s pop culture)

## Next Steps

1. **Test on touch screen** - Deploy to Pi and test
2. **Customize colors** - Match your preferences
3. **Add custom panels** - Extend LCARS frame
4. **Create themes** - Multiple LCARS variants
5. **Add animations** - More dynamic effects

## Credits

- **LCARS Template**: [www.TheLCARS.com](https://www.thelcars.com) by Jim Robertus
- **HAL Integration**: Custom config-driven renderer
- **Star Trek**: TNG LCARS design © Paramount

## Live Long and Prosper 🖖

Your HAL system now has the same interface used on the USS Enterprise-D!

---

For regular UI documentation, see: `UI_CONFIG_GUIDE.md`
