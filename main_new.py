"""
Voice Kiosk Main Application
Integrates all subsystems with Eel frontend
"""
import eel
import asyncio
import logging
import json
from pathlib import Path

# Import configuration
from config import get_config
from logging_config import setup_logging

# Import subsystems
from event_loop import EventLoopCoordinator, AppStatus
from subsystem_manager import SubsystemManager
from ollama_client import OllamaClient
from tool_processor import ToolProcessor
from system_prompt import SystemPrompt

# Setup logging first
config = get_config()
logger = setup_logging(config.LOG_LEVEL, config.LOG_FILE)

# Initialize Eel
logger.info("Initializing Eel framework")
eel.init('web')

# Global instances
event_coordinator = None
subsystem_manager = None
ollama_client = None
tool_processor = None
system_prompts = None
main_loop = None  # Reference to main event loop

# Global application state (synced with frontend)
app_state = {
    'status': 'BOOT',  # Maps to AppStatus enum
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

# Wake word listener task
wake_word_task = None


def schedule_coroutine(coro):
    """Schedule a coroutine to run in the main event loop (thread-safe)"""
    if main_loop and not main_loop.is_closed():
        asyncio.run_coroutine_threadsafe(coro, main_loop)
    else:
        logger.error("Cannot schedule coroutine: main loop not available")


# ============================================================================
# Initialization Functions
# ============================================================================

async def initialize_application():
    """Initialize all application subsystems"""
    global event_coordinator, subsystem_manager, ollama_client, tool_processor, system_prompts

    logger.info("=" * 80)
    logger.info("VOICE KIOSK APPLICATION INITIALIZATION")
    logger.info("=" * 80)

    try:
        # Validate configuration
        logger.info("Validating configuration...")
        config.validate()
        logger.info("Configuration validation passed")

        # Create event loop coordinator
        logger.info("Creating event loop coordinator...")
        event_coordinator = EventLoopCoordinator(config)
        logger.info("Event loop coordinator created")

        # Register state callbacks
        register_state_callbacks()

        # Create subsystem manager
        logger.info("Creating subsystem manager...")
        subsystem_manager = SubsystemManager(config, event_coordinator)
        logger.info("Subsystem manager created")

        # Initialize all subsystems
        logger.info("Initializing subsystems...")
        success = await subsystem_manager.initialize_all()

        if not success:
            logger.error("Subsystem initialization failed!")
            raise RuntimeError("Failed to initialize subsystems")

        logger.info("All subsystems initialized successfully")

        # Get references to key subsystems
        ollama_client = subsystem_manager.ollama_client
        tool_processor = subsystem_manager.tool_processor

        # Load system prompts
        logger.info("Loading system prompts...")
        system_prompts = SystemPrompt(config)
        logger.info(f"System prompts loaded (agent: {config.OLLAMA_AGENT_MODEL}, conversation: {config.OLLAMA_CONVERSATION_MODEL})")

        # Start event loop coordinator
        logger.info("Starting event loop coordinator...")
        event_coordinator.create_task(
            event_coordinator.run(),
            name="event_loop_coordinator"
        )
        logger.info("Event loop coordinator started")

        logger.info("=" * 80)
        logger.info("APPLICATION INITIALIZATION COMPLETE")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"Fatal error during initialization: {e}", exc_info=True)
        return False


def register_state_callbacks():
    """Register callbacks for state transitions"""
    logger.info("Registering state callbacks...")

    # Callback for IDLE state - start wake word listener
    async def on_idle(metadata):
        logger.info("Entered IDLE state - starting wake word listener")
        await start_wake_word_listener()

    # Callback for RECORDING state
    async def on_recording(metadata):
        logger.info("Entered RECORDING state")
        # Stop wake word listener
        if subsystem_manager and subsystem_manager.wake_word_detector:
            await subsystem_manager.stop_wake_word_listening()
            # Brief delay to ensure audio device is fully released
            delay = config.WAKE_WORD_DEVICE_RELEASE_DELAY
            logger.info(f"Waiting {delay}s for audio device release...")
            await asyncio.sleep(delay)
            logger.info("Audio device released, ready for recording")

    # Callback for THINKING state
    async def on_thinking(metadata):
        logger.info("Entered THINKING state")

    # Callback for SPEAKING state
    async def on_speaking(metadata):
        logger.info("Entered SPEAKING state")

    event_coordinator.register_state_callback(AppStatus.IDLE, on_idle)
    event_coordinator.register_state_callback(AppStatus.RECORDING, on_recording)
    event_coordinator.register_state_callback(AppStatus.THINKING, on_thinking)
    event_coordinator.register_state_callback(AppStatus.SPEAKING, on_speaking)

    logger.info("State callbacks registered")


# ============================================================================
# Wake Word Detection
# ============================================================================

async def start_wake_word_listener():
    """Start listening for wake word"""
    global wake_word_task

    if not subsystem_manager or not subsystem_manager.wake_word_detector:
        logger.error("Cannot start wake word listener: detector not initialized")
        return

    logger.info("Starting wake word listener...")

    try:
        # Define callback for wake word detection
        async def on_wake_word_detected():
            logger.info("!" * 80)
            logger.info("WAKE WORD DETECTED!")
            logger.info("!" * 80)

            # Transition to recording state
            await event_coordinator.transition_state(AppStatus.RECORDING)

            # Update UI
            update_app_state({
                'status': 'RECORDING',
                'show_face': False,
                'status_message': True,
                'internal_message': 'Listening...',
                'recorded_message': '',
                'backend_response': []
            })

            # Start recording
            await handle_recording()

        # Start wake word detection
        wake_word_task = await subsystem_manager.start_wake_word_listening(on_wake_word_detected)
        logger.info("Wake word listener started successfully")

    except Exception as e:
        logger.error(f"Error starting wake word listener: {e}", exc_info=True)


# ============================================================================
# Audio Recording & Transcription
# ============================================================================

async def handle_recording():
    """Handle audio recording and transcription"""
    logger.info("Starting audio recording process...")

    try:
        # Record audio
        logger.info("Recording audio...")
        audio_file = await subsystem_manager.record_audio()

        if not audio_file:
            logger.error("Recording failed - no audio file returned")
            await handle_recording_error("Recording failed")
            return

        logger.info(f"Audio recorded successfully: {audio_file}")

        # Transition to processing state
        await event_coordinator.transition_state(AppStatus.PROCESSING_RECORDING)
        update_app_state({
            'status': 'PROCESSING_RECORDING',
            'show_face': True,
            'face': 'thinking',
            'status_message': False
        })

        # Transcribe audio
        logger.info("Transcribing audio...")
        transcribed_text = await subsystem_manager.transcribe_audio(audio_file)

        if not transcribed_text:
            logger.error("Transcription failed - no text returned")
            await handle_recording_error("Could not understand audio")
            return

        logger.info(f"Transcription complete: '{transcribed_text}'")

        # Update state with transcribed message
        update_app_state({
            'recorded_message': transcribed_text
        })

        # Process with LLM
        await process_user_input(transcribed_text)

    except Exception as e:
        logger.error(f"Error in recording/transcription pipeline: {e}", exc_info=True)
        await handle_recording_error(str(e))


async def handle_recording_error(error_message: str):
    """Handle recording/transcription errors"""
    logger.error(f"Recording error: {error_message}")

    update_app_state({
        'status': 'IDLE',
        'show_face': True,
        'face': 'dead',
        'status_message': True,
        'internal_message': f'Error: {error_message}'
    })

    # Transition back to idle
    await event_coordinator.transition_state(AppStatus.IDLE)


# ============================================================================
# LLM Processing
# ============================================================================

async def process_user_input(user_input: str):
    """Process user input through agent loop and conversation model"""
    logger.info("=" * 80)
    logger.info(f"Processing user input: '{user_input}'")
    logger.info("=" * 80)

    try:
        # Transition to thinking state
        await event_coordinator.transition_state(AppStatus.THINKING)
        update_app_state({
            'status': 'THINKING',
            'face': 'reading',
            'show_face': True
        })

        # Phase 1: Agent loop with tool calling
        logger.info("Phase 1: Running agent loop...")
        agent_result = await run_agent_loop(user_input)
        logger.info(f"Agent loop complete. Result: {agent_result}")

        # Phase 2: Generate natural language response
        logger.info("Phase 2: Generating conversation response...")
        await generate_conversation_response(user_input, agent_result)

    except Exception as e:
        logger.error(f"Error processing user input: {e}", exc_info=True)
        await handle_processing_error(str(e))


async def run_agent_loop(user_input: str):
    """Run agent loop with tool calling"""
    logger.info("Starting agent loop...")

    try:
        # Get agent system prompt configuration
        agent_config = system_prompts.agent

        logger.info(f"Agent prompt loaded")
        logger.info(f"Using model: {agent_config['model_name']}")

        # Run agent loop
        result = await tool_processor.agent_loop(
            user_input,
            ollama_client,
            agent_config['prompt_text'],
            max_iterations=config.AGENT_MAX_ITERATIONS,
            model=agent_config['model_name']
        )

        logger.info(f"Agent loop completed with result: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in agent loop: {e}", exc_info=True)
        return f"Error in agent processing: {e}"


async def generate_conversation_response(user_input: str, agent_result: str):
    """Generate natural language response using conversation model"""
    logger.info("Generating conversation response...")

    try:
        # Transition to speaking state
        await event_coordinator.transition_state(AppStatus.SPEAKING)
        update_app_state({
            'status': 'SPEAKING',
            'finished_streaming': False,
            'show_face': False,
            'status_message': False,
            'backend_response': []
        })

        # Get conversation system prompt configuration
        conversation_config = system_prompts.conversation

        # Build conversation context
        messages = [
            {"role": "system", "content": conversation_config['prompt_text']},
            {"role": "user", "content": user_input}
        ]

        if agent_result and agent_result != "No tasks executed":
            messages.append({
                "role": "assistant",
                "content": f"I performed these actions: {agent_result}"
            })

        logger.info(f"Streaming response from {conversation_config['model_name']}...")

        # Stream response
        response_buffer = ""
        response_words = []

        async for chunk in ollama_client.stream_response(
            conversation_config['model_name'],
            messages,
            format=conversation_config['format']
        ):
            response_buffer += chunk

            # Try to parse words and stream them
            try:
                # Split by spaces for word-by-word streaming
                words = response_buffer.split()
                if len(words) > len(response_words):
                    new_words = words[len(response_words):]
                    response_words.extend(new_words)

                    # Add new words with trailing spaces
                    app_state['backend_response'].extend([w + " " for w in new_words])
                    eel.updateState(app_state)()

                    logger.debug(f"Streamed {len(new_words)} new word(s)")

            except Exception as e:
                logger.debug(f"Error during streaming: {e}")

        # Parse final JSON response
        try:
            response_data = json.loads(response_buffer)
            message = response_data.get('message', response_buffer)
            feeling = response_data.get('feeling', 'happy')

            logger.info(f"Response complete. Feeling: {feeling}")
            logger.info(f"Full message: {message}")

            # Update final state
            update_app_state({
                'finished_streaming': True,
                'reaction': feeling,
                'show_face': True,
                'face': 'love' if feeling == 'happy' else 'idle'
            })

            # Add to conversation history
            app_state['conversation_history'].append({
                'user': user_input,
                'assistant': message,
                'feeling': feeling
            })

            # Wait a moment before returning to idle
            await asyncio.sleep(2)

            # Transition back to idle
            await event_coordinator.transition_state(AppStatus.IDLE)
            update_app_state({
                'status': 'IDLE'
            })

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse conversation response JSON: {e}")
            logger.error(f"Raw response: {response_buffer}")

            # Still mark as complete
            update_app_state({
                'finished_streaming': True,
                'status': 'IDLE'
            })
            await event_coordinator.transition_state(AppStatus.IDLE)

    except Exception as e:
        logger.error(f"Error generating conversation response: {e}", exc_info=True)
        await handle_processing_error(str(e))


async def handle_processing_error(error_message: str):
    """Handle LLM processing errors"""
    logger.error(f"Processing error: {error_message}")

    update_app_state({
        'status': 'IDLE',
        'show_face': True,
        'face': 'dead',
        'backend_response': [f"Sorry, I encountered an error: {error_message}"],
        'finished_streaming': True
    })

    await event_coordinator.transition_state(AppStatus.IDLE)


# ============================================================================
# State Management Helpers
# ============================================================================

def update_app_state(updates: dict):
    """Update app state and notify frontend"""
    app_state.update(updates)
    eel.updateState(app_state)()
    logger.debug(f"State updated: {updates}")


# ============================================================================
# Eel Exposed Functions (called from frontend)
# ============================================================================

@eel.expose
def get_app_state():
    """Get current application state for frontend"""
    logger.debug(f"Frontend requested app state: {app_state['status']}")
    return app_state


@eel.expose
def handle_click():
    """Handle screen tap based on current state"""
    current_status = app_state['status']
    logger.info(f"Screen clicked in state: {current_status}")

    if current_status == 'BOOT':
        schedule_coroutine(complete_boot_sequence())
    elif current_status == 'IDLE':
        schedule_coroutine(_wake_app())
    elif current_status == 'RECORDING':
        # Could implement stop recording manually
        logger.info("Recording in progress, waiting for silence...")
    elif current_status == 'SPEAKING':
        schedule_coroutine(_stop_speaking())
    elif current_status == 'SCREENSAVER':
        schedule_coroutine(_wake_from_screensaver())

    # Reset screensaver timeout
    if event_coordinator:
        event_coordinator.reset_activity_timer()


@eel.expose
def initiate_app():
    """Initialize the application (boot sequence)"""
    logger.info("Initiating app from frontend")
    schedule_coroutine(complete_boot_sequence())


async def complete_boot_sequence():
    """Complete the boot sequence"""
    logger.info("Starting boot sequence...")

    try:
        update_app_state({
            'status': 'THINKING',
            'show_face': False,
            'status_message': True,
            'internal_message': 'Initializing systems...',
            'backend_response': []
        })

        # Simulate boot time
        await asyncio.sleep(1)

        # Generate greeting
        logger.info("Generating boot greeting...")
        update_app_state({
            'status': 'SPEAKING',
            'finished_streaming': False,
            'status_message': False,
            'show_face': False,
            'backend_response': []
        })

        # Simple greeting
        greeting_words = ["Hello!", "I'm", "your", "AI", "voice", "assistant.", "Say", "my", "wake", "word", "to", "activate", "me."]
        for word in greeting_words:
            app_state['backend_response'].append(word + " ")
            eel.updateState(app_state)()
            await asyncio.sleep(0.1)

        await asyncio.sleep(1)

        # Transition to idle
        if event_coordinator:
            await event_coordinator.transition_state(AppStatus.IDLE)
        update_app_state({
            'status': 'IDLE',
            'finished_streaming': True,
            'show_face': True,
            'face': 'idle'
        })

        logger.info("Boot sequence complete")

    except Exception as e:
        logger.error(f"Boot sequence error: {e}", exc_info=True)
        update_app_state({
            'face': 'dead',
            'status': 'IDLE',
            'show_face': True
        })


@eel.expose
def start_recording():
    """Start voice recording (called from frontend)"""
    logger.info("start_recording called from frontend")
    # Recording is triggered by wake word detection
    # This could be used for manual activation


@eel.expose
def stop_recording():
    """Stop voice recording (called from frontend)"""
    logger.info("stop_recording called from frontend")
    # Recording automatically stops on silence


@eel.expose
def stop_speaking():
    """Stop current speech"""
    logger.info("Stopping speech")
    schedule_coroutine(_stop_speaking())


async def _stop_speaking():
    """Stop speaking async"""
    update_app_state({
        'status': 'IDLE',
        'backend_response': [],
        'recorded_message': '*Interrupted*',
        'finished_streaming': True,
        'show_face': True,
        'face': 'idle'
    })
    if event_coordinator:
        await event_coordinator.transition_state(AppStatus.IDLE)


@eel.expose
def wake_app():
    """Wake app from idle state (manual activation)"""
    logger.info("Waking app manually")
    schedule_coroutine(_wake_app())


async def _wake_app():
    """Wake app async"""
    if event_coordinator:
        await event_coordinator.transition_state(AppStatus.RECORDING)
    update_app_state({
        'status': 'RECORDING',
        'show_face': False,
        'status_message': True,
        'internal_message': 'Listening...'
    })
    await handle_recording()


@eel.expose
def wake_from_screensaver():
    """Wake from screensaver"""
    logger.info("Waking from screensaver")
    schedule_coroutine(_wake_from_screensaver())


async def _wake_from_screensaver():
    """Wake from screensaver async"""
    if event_coordinator:
        await event_coordinator.transition_state(AppStatus.IDLE)
    update_app_state({
        'status': 'IDLE',
        'show_face': True,
        'face': 'idle'
    })


# ============================================================================
# Main Entry Point
# ============================================================================

async def async_main():
    """Async main function"""
    logger.info("Starting async_main()")

    # Initialize application
    success = await initialize_application()

    if not success:
        logger.error("Application initialization failed, exiting")
        return

    logger.info("Application ready!")

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        # Shutdown
        logger.info("Shutting down application...")
        if subsystem_manager:
            await subsystem_manager.shutdown()
        if event_coordinator:
            await event_coordinator.shutdown()
        logger.info("Shutdown complete")


if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("VOICE KIOSK APPLICATION STARTING")
    logger.info("=" * 80)

    # Initialize asyncio loop and store reference
    main_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(main_loop)
    logger.info(f"Main event loop created: {main_loop}")

    # Start async initialization in background
    main_loop.create_task(async_main())

    # Run event loop in a separate thread
    import threading

    def run_event_loop():
        """Run event loop in background thread"""
        logger.info("Starting event loop in background thread")
        main_loop.run_forever()
        logger.info("Event loop stopped")

    loop_thread = threading.Thread(target=run_event_loop, daemon=True)
    loop_thread.start()
    logger.info("Event loop thread started")

    # Give initialization a moment to start
    import time
    time.sleep(2)

    # Start Eel (blocks until window closes)
    try:
        logger.info("Starting Eel web interface...")
        eel.start('index.html',
                  size=(config.UI_WIDTH, config.UI_HEIGHT),
                  mode='chrome',
                  port=config.EEL_PORT,
                  block=True,
                  cmdline_args=[
                      '--kiosk' if config.UI_KIOSK_MODE else '',
                      '--disable-features=VizDisplayCompositor',
                      '--autoplay-policy=no-user-gesture-required'
                  ])
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        logger.info("Shutting down event loop...")
        main_loop.call_soon_threadsafe(main_loop.stop)
        loop_thread.join(timeout=5)
        logger.info("Application exit")
