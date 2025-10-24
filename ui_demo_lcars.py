#!/usr/bin/env python3
"""
LCARS UI Demo - Star Trek TNG themed interface
Uses the same backend as ui_demo.py but with LCARS HTML/CSS
"""

import eel
import json
import asyncio
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from hal_mcp_manager import HALMCPManager

# Initialize Eel
eel.init('web')

# Global MCP manager
mcp_manager = None
mcp_event_loop = None


@eel.expose
def load_ui_config():
    """Load UI configuration from JSON file"""
    config_file = Path(__file__).parent / 'ui-config.json'

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        print(f"✅ Loaded UI config: {len(config.get('screens', {}))} screens")
        return config
    except Exception as e:
        print(f"❌ Error loading UI config: {e}")
        return {
            "version": "1.0",
            "initial_screen": "error",
            "screens": {
                "error": {
                    "title": "Error",
                    "components": [
                        {
                            "type": "text",
                            "content": f"Failed to load config: {e}",
                            "style": {"color": "red", "fontSize": "18px"}
                        }
                    ]
                }
            }
        }


@eel.expose
def call_mcp(server, tool, params):
    """Call MCP tool through the manager"""
    global mcp_manager, mcp_event_loop

    print(f"🔧 MCP Call: {server}.{tool} with params: {params}")

    try:
        if not mcp_manager or not mcp_event_loop:
            return "Error: MCP not initialized"

        future = asyncio.run_coroutine_threadsafe(
            mcp_manager.call_tool(server, tool, params),
            mcp_event_loop
        )

        result = future.result(timeout=30)
        print(f"✅ MCP Result: {result[:100]}...")
        return result

    except Exception as e:
        error_msg = f"MCP Error: {e}"
        print(f"❌ {error_msg}")
        return error_msg


async def init_mcp():
    """Initialize MCP manager and connect to servers"""
    global mcp_manager

    print("🔌 Initializing MCP servers...")

    mcp_manager = HALMCPManager()

    mcp_config_file = Path(__file__).parent.parent / 'mcp-servers.json'

    try:
        with open(mcp_config_file, 'r') as f:
            config_data = json.load(f)

        servers_config = config_data.get("mcpServers", config_data)

        await mcp_manager.connect_servers(servers_config)
        print(f"✅ Connected to {len(mcp_manager.sessions)} MCP servers")

    except Exception as e:
        print(f"⚠️  MCP initialization failed: {e}")


def start_mcp_event_loop():
    """Start asyncio event loop for MCP in a separate thread"""
    global mcp_event_loop

    import threading

    def run_loop():
        global mcp_event_loop
        mcp_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(mcp_event_loop)

        mcp_event_loop.run_until_complete(init_mcp())
        mcp_event_loop.run_forever()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()

    print("🔄 MCP event loop started in background thread")


def main():
    """Start the LCARS UI demo"""
    print("="*60)
    print("🖖 HAL LCARS Interface - Star Trek TNG Style")
    print("="*60)

    # Start MCP event loop
    start_mcp_event_loop()

    # Wait for MCP to initialize
    import time
    time.sleep(2)

    # Start Eel with LCARS interface
    print("\n🚀 Starting LCARS interface...")
    print("   Open your browser to: http://localhost:8080/ui-lcars.html")
    print("   Press Ctrl+C to exit")
    print("="*60)

    try:
        eel.start('ui-lcars.html', size=(1280, 800), port=8080)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down... Live long and prosper.")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == '__main__':
    main()
