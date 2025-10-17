import eel
from typing import List, Dict, Optional, Union  # Common typing imports
import voice_kiosk
import json
import logging
from ollama_client import OllamaClient  
from tool_processor import ToolProcessor
from system_prompt import SystemPrompt

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Eel
eel.init('web')

# Global application state
app_state = {
    'status': 'BOOT',  # RECORDING, IDLE, THINKING, BOOT, PROCESSING_RECORDING, SPEAKING, SCREENSAVER
    'recorded_message': '',
    'backend_response': [],
    'finished_streaming': False,
    'reaction': None,
    'show_face': True,
    'face': 'idle',
    'status_message': True,
    'internal_message': '',
    'conversation_history': [],
    'agent_history': []
}

@eel.expose
def get_app_state():
    """Get current application state for frontend"""
    logger.info(f"get_app_state {app_state}")
    return app_state

@eel.expose
def handle_click():
    """Handle screen tap based on current state"""
    current_status = app_state['status']
    
    if current_status == 'BOOT':
        initiate_app()
    elif current_status == 'IDLE':
        wake_app()
    elif current_status == 'RECORDING':
        stop_recording()
    elif current_status == 'SPEAKING':
        stop_speaking()
    elif current_status == 'SCREENSAVER':
        wake_from_screensaver()
    
    # Reset screensaver timeout
    eel.resetScreensaverTimeout()(lambda: None)

@eel.expose
def initiate_app():
    """Initialize the application (equivalent to your boot sequence)"""
    try:
        app_state.update({
            'status': 'THINKING',
            'show_face': False,
            'status_message': True,
            'internal_message': 'Loading...',
            'backend_response': []
        })
        
        # TODO: Implement your boot logic here
        # This would call Ollama and set up initial state
        
        eel.updateState(app_state)()
        
        # Simulate boot completion
        import asyncio
        asyncio.create_task(complete_boot_sequence())
        
    except Exception as e:
        logger.error(f"Boot error: {e}")
        app_state.update({'face': 'dead', 'status': ''})
        eel.updateState(app_state)()

async def complete_boot_sequence():
    """Complete the boot sequence"""
    await asyncio.sleep(2)
    
    app_state.update({
        'status': 'SPEAKING',
        'finished_streaming': False,
        'status_message': False,
        'show_face': False,
        'backend_response': ['Welcome! ', 'I am your AI assistant. ', 'Tap to speak with me.']
    })
    eel.updateState(app_state)()
    
    await asyncio.sleep(3)
    
    app_state.update({
        'status': 'IDLE',
        'finished_streaming': True,
        'show_face': True,
        'face': 'idle'
    })
    eel.updateState(app_state)()

@eel.expose
def start_recording():
    """Start voice recording"""
    try:
        app_state.update({
            'show_face': False,
            'status': 'RECORDING',
            'status_message': True,
            'internal_message': 'Listening...'
        })
        eel.updateState(app_state)()
        
        # TODO: Integrate with your voice recording backend
        logger.info("Recording started")
        
    except Exception as e:
        logger.error(f"Recording error: {e}")

@eel.expose
def stop_recording():
    """Stop voice recording and process"""
    try:
        # Simulate recording processing
        app_state.update({
            'status': 'PROCESSING_RECORDING',
            'show_face': True,
            'status_message': False,
            'face': 'thinking',
            'reaction': None
        })
        eel.updateState(app_state)()
        
        # Simulate AI processing
        process_recorded_message("Hello there!")
        
    except Exception as e:
        logger.error(f"Stop recording error: {e}")

def process_recorded_message(message):
    """Process the recorded message through AI"""
    app_state['recorded_message'] = message
    app_state.update({
        'status': 'THINKING',
        'face': 'reading'
    })
    eel.updateState(app_state)()
    
    # TODO: Integrate with your AI logic
    # This would call your agentRequest or processConversation equivalent
    
    # Simulate AI response
    import asyncio
    asyncio.create_task(simulate_ai_response(message))

async def simulate_ai_response(message):
    """Simulate AI processing and response"""
    await asyncio.sleep(2)
    
    # Start "speaking"
    app_state.update({
        'status': 'SPEAKING',
        'finished_streaming': False,
        'status_message': False,
        'show_face': False,
        'backend_response': ['You said: "', message, '". ', 'That is very interesting! ']
    })
    eel.updateState(app_state)()
    
    # Stream response
    await asyncio.sleep(1)
    app_state['backend_response'].extend(['I am thinking ', 'about what you said... '])
    eel.updateState(app_state)()
    
    await asyncio.sleep(1)
    app_state['backend_response'].extend(['Well, ', 'that was quite fascinating!'])
    eel.updateState(app_state)()
    
    # Finish streaming
    await asyncio.sleep(1)
    app_state.update({
        'finished_streaming': True,
        'reaction': 'happy',
        'status': 'IDLE',
        'show_face': True,
        'face': 'love'
    })
    eel.updateState(app_state)()

@eel.expose
def stop_speaking():
    """Stop current speech"""
    logger.info("Stopping speech")
    # TODO: Implement speech interruption
    app_state.update({
        'status': 'IDLE',
        'backend_response': [],
        'recorded_message': '*Interrupted*',
        'finished_streaming': True
    })
    eel.updateState(app_state)()

@eel.expose
def wake_app():
    """Wake app from idle state"""
    logger.info("Waking app")
    start_recording()

@eel.expose
def wake_from_screensaver():
    """Wake from screensaver"""
    app_state.update({
        'status': 'IDLE',
        'show_face': False
    })
    eel.updateState(app_state)()

if __name__ == '__main__':
    # Start the kiosk app
    eel.start('index.html', 
              size=(1024, 768), 
              mode='chrome',
              port=8080,
              cmdline_args=[
                  '--kiosk', 
                  '--disable-features=VizDisplayCompositor',
                  '--autoplay-policy=no-user-gesture-required'
              ])
