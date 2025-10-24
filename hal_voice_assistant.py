#!/usr/bin/env python3
"""
HAL Voice Assistant with Eel GUI
Combines Voice Pipeline V2 + MCP Tools + LLM
"""
import eel
import asyncio
import logging
import sys
import threading
import json
from pathlib import Path
import pyttsx3

# Add parent directory to path for HAL imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config
from voice_pipeline_v2 import VoicePipelineV2

# Import HAL MCP components
from hal_mcp_manager import HALMCPManager
from hal_intent_matcher import HALIntentMatcher
import ollama

# Setup logging - configure root logger to catch all subsystem logs
log_file = Path(__file__).parent / 'hal_voice_assistant.log'
logging.basicConfig(
    level=logging.DEBUG,  # Capture all log levels
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stderr),  # Write to stderr
        logging.FileHandler(log_file, mode='w')  # Also write to file
    ],
    force=True  # Force reconfiguration even if already configured
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to: {log_file}")

# Set specific log levels for noisy libraries
logging.getLogger('eel').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('mcp').setLevel(logging.INFO)

# Initialize Eel
eel.init('web')

# Global state
app_state = {
    'listening': False,
    'status': 'initializing',
    'wake_word': 'hal',
    'language': 'en'
}

# Components
voice_pipeline = None
mcp_manager = None
intent_matcher = None
ollama_client = None
config = None
voice_loop_thread = None
voice_loop_event_loop = None
mcp_thread = None  # Thread running MCP event loop
mcp_event_loop = None  # Event loop where MCP manager lives
tts_engine = None  # TTS engine


def run_mcp_thread():
    """Run MCP manager in its own thread with persistent event loop"""
    global mcp_event_loop, mcp_manager, config

    # Create new event loop for this thread
    mcp_event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(mcp_event_loop)

    logger.info("MCP thread started")

    async def init_mcp():
        global mcp_manager

        # Initialize MCP Manager
        logger.info("🔌 Initializing MCP tools...")
        mcp_manager = HALMCPManager()

        # Load MCP servers
        import json
        mcp_config_path = config.MCP_SERVERS_CONFIG if hasattr(config, 'MCP_SERVERS_CONFIG') else '../mcp-servers.json'
        with open(mcp_config_path, 'r') as f:
            mcp_config = json.load(f)
            servers_config = mcp_config.get("mcpServers", mcp_config)

        await mcp_manager.connect_servers(servers_config)
        logger.info(f"✅ Connected to {len(mcp_manager.sessions)} MCP servers")

        # Keep event loop running
        while True:
            await asyncio.sleep(1)

    try:
        mcp_event_loop.run_until_complete(init_mcp())
    except Exception as e:
        logger.error(f"MCP thread error: {e}", exc_info=True)
    finally:
        mcp_event_loop.close()
        logger.info("MCP thread stopped")

def initialize_tts():
    """Initialize Text-to-Speech engine"""
    global tts_engine, config

    try:
        logger.info("Initializing TTS engine...")
        tts_engine = pyttsx3.init()

        # Configure from settings
        tts_engine.setProperty('rate', config.TTS_RATE)
        tts_engine.setProperty('volume', config.TTS_VOLUME)

        # Set voice if specified
        if config.TTS_VOICE:
            voices = tts_engine.getProperty('voices')
            for voice in voices:
                if config.TTS_VOICE in voice.id:
                    tts_engine.setProperty('voice', voice.id)
                    logger.info(f"TTS voice set to: {voice.id}")
                    break

        logger.info("✅ TTS engine initialized")
        return True
    except Exception as e:
        logger.error(f"TTS initialization failed: {e}")
        return False


def speak(text):
    """Speak text using TTS (non-blocking)"""
    global tts_engine

    if not tts_engine:
        logger.warning("TTS not initialized, skipping speak")
        return

    try:
        logger.info(f"🔊 Speaking: {text[:100]}...")
        tts_engine.say(text)
        tts_engine.runAndWait()
    except Exception as e:
        logger.error(f"TTS speak error: {e}")


async def initialize_system():
    """Initialize all systems"""
    global voice_pipeline, intent_matcher, ollama_client, config, mcp_thread

    try:
        eel_log("🚀 Initializing HAL Voice Assistant...")

        # Load config
        config = get_config()
        app_state['wake_word'] = config.WAKE_WORD

        # Initialize Voice Pipeline
        eel_log("🎤 Initializing voice pipeline...")
        voice_pipeline = VoicePipelineV2(config)
        if not await voice_pipeline.initialize():
            raise Exception("Voice pipeline initialization failed")
        eel_log("✅ Voice pipeline ready")

        # Initialize TTS
        eel_log("🔊 Initializing text-to-speech...")
        if initialize_tts():
            eel_log("✅ TTS ready")
        else:
            eel_log("⚠️  TTS initialization failed (will continue without speech)")

        # Start MCP manager in its own thread
        eel_log("🔌 Starting MCP manager thread...")
        mcp_thread = threading.Thread(target=run_mcp_thread, daemon=True)
        mcp_thread.start()

        # Wait for MCP manager to be initialized
        timeout = 10
        for i in range(timeout * 10):
            await asyncio.sleep(0.1)
            if mcp_manager is not None:
                eel_log(f"✅ MCP manager ready")
                break
        else:
            raise Exception("MCP manager initialization timeout")

        # Initialize Intent Matcher
        intent_mapping_path = config.INTENT_MAPPING if hasattr(config, 'INTENT_MAPPING') else '../intent-mapping.json'
        intent_matcher = HALIntentMatcher(mapping_file=intent_mapping_path)
        eel_log(f"✅ Loaded {len(intent_matcher.intents)} intents")

        # Initialize Ollama client
        ollama_url = config.OLLAMA_URL if hasattr(config, 'OLLAMA_URL') else "http://localhost:11434"
        ollama_client = ollama.Client(host=ollama_url)
        eel_log(f"✅ Ollama client ready ({ollama_url})")

        app_state['status'] = 'ready'
        eel_update_status('ready', 'Ready - Say "{}" to activate'.format(app_state['wake_word']))

        return True

    except Exception as e:
        logger.error(f"Initialization failed: {e}", exc_info=True)
        eel_log(f"❌ Initialization failed: {e}")
        app_state['status'] = 'error'
        return False


async def voice_loop():
    """Main voice interaction loop"""
    global voice_pipeline, app_state

    logger.info("🎤 Voice loop started!")
    eel_log("🎤 Voice loop started!")

    while app_state['listening']:
        try:
            # Update UI
            logger.info(f"👂 Listening for wake word: {app_state['wake_word']}")
            eel_update_status('listening', f'Listening for "{app_state["wake_word"]}"...')

            # Wait for wake word and get transcription
            logger.info("Calling listen_and_transcribe()...")
            text = await voice_pipeline.listen_and_transcribe()

            if not text:
                logger.info("No text received, continuing...")
                continue

            logger.info("="*80)
            logger.info(f"📝 TRANSCRIPTION: '{text}'")
            logger.info("="*80)

            # Filter out TTS feedback (when microphone picks up the speaker output)
            # Common phrases from agent responses that shouldn't be processed as commands
            tts_feedback_phrases = [
                "completed successfully",
                "operations completed",
                "task completed",
                "request completed",
                "all done",
                "finished successfully"
            ]
            text_lower = text.lower()
            if any(phrase in text_lower for phrase in tts_feedback_phrases):
                logger.warning(f"⚠️  Ignoring TTS feedback: '{text}'")
                eel_log(f"⚠️  Filtered TTS echo")
                continue

            # Update UI with transcription
            eel_update_transcript(text)
            eel_update_status('processing', 'Processing your request...')

            # Process the command
            response = await process_command(text)

            # Update UI with response
            eel_update_response(response)
            eel_update_status('speaking', 'Speaking response...')

            # Speak response using TTS
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, speak, response)

            # Wait longer to ensure TTS audio has finished and microphone buffer is clear
            # This prevents the microphone from picking up the TTS output as a new command
            await asyncio.sleep(3.0)  # Increased from 0.5s to prevent audio feedback loop

        except Exception as e:
            logger.error(f"Voice loop error: {e}", exc_info=True)
            eel_log(f"❌ Error: {e}")
            await asyncio.sleep(2)

    logger.info("🛑 Voice loop stopped")
    eel_log("🛑 Voice loop stopped")


async def resolve_movie_filename(partial_name: str) -> str:
    """
    Resolve a partial movie name to a full filename by fuzzy matching against available movies

    Args:
        partial_name: Partial movie name (e.g., "superman")

    Returns:
        Full filename (e.g., "Superman.mp4") or original if no match found
    """
    try:
        # Call list_movies to get available movies
        logger.debug(f"Resolving movie filename for: {partial_name}")

        # Call MCP tool on MCP event loop
        future = asyncio.run_coroutine_threadsafe(
            mcp_manager.call_tool("media-server", "list_movies", {}),
            mcp_event_loop
        )
        result = future.result(timeout=10)

        # Parse the result - it's in text format with numbered list
        # Format: "1. Filename.mp4\n   Path: ...\n   Size: ...\n   Type: ...\n"
        import re
        movie_names = []

        # Extract movie filenames from numbered list (e.g., "1. Superman.mp4")
        for line in result.split('\n'):
            # Match lines like "1. Superman.mp4" or "5. Superman.mp4"
            match = re.match(r'^\d+\.\s+(.+\.(mp4|mkv|avi|mov))\s*$', line.strip())
            if match:
                movie_names.append(match.group(1))

        if not movie_names:
            logger.warning(f"No movie files found in list_movies result")
            logger.debug(f"Result: {result[:500]}")
            return partial_name

        logger.debug(f"Found {len(movie_names)} movies: {movie_names}")

        # Fuzzy match the partial name against movie filenames
        partial_lower = partial_name.lower()
        best_match = None
        best_score = 0

        for movie_name in movie_names:
            movie_name_lower = movie_name.lower()

            # Remove extension for comparison
            movie_base = movie_name_lower.rsplit('.', 1)[0] if '.' in movie_name_lower else movie_name_lower

            # Simple fuzzy matching - check if partial name is in movie name
            if partial_lower in movie_base:
                # Score by length difference (prefer closer matches)
                score = 100 - abs(len(movie_base) - len(partial_lower))
                if score > best_score:
                    best_score = score
                    best_match = movie_name
            # Exact match
            elif partial_lower == movie_base:
                best_match = movie_name
                break

        if best_match:
            logger.info(f"Matched '{partial_name}' to '{best_match}'")
            return best_match
        else:
            logger.warning(f"No movie match found for '{partial_name}'")
            return partial_name

    except Exception as e:
        logger.error(f"Error resolving movie filename: {e}", exc_info=True)
        return partial_name


async def use_llm_agent(user_text: str) -> str:
    """
    Use LLM agent with tool calling to handle complex requests

    Args:
        user_text: User's request

    Returns:
        Agent's response after tool execution
    """
    try:
        # Get list of available MCP tools
        all_tools = mcp_manager.get_all_tools()

        # Build tools description for prompt
        tools_desc = []
        for tool_info in all_tools:
            server = tool_info.get("server", "")
            tool_name = tool_info.get("tool", "")
            description = tool_info.get("description", "")
            tools_desc.append(f"- {server}.{tool_name}: {description}")

        tools_prompt = "\n".join(tools_desc)

        # System prompt for agent
        system_prompt = f"""You are an expert at breaking down complex user requests into function calls.

Available functions:
{tools_prompt}

Respond with JSON only:
{{"function":"function_name","describe":"brief intent","parameter":"value_or_json"}}

IMPORTANT RULES:
1. You must actually CALL the functions, not just describe what you would do
2. Only call "finished" AFTER you have called all necessary functions
3. For media-server.play_movie, use ONLY the filename (e.g. "nonexistantmovie.mp4"), NOT the full path
4. When list_movies shows "1. nonexistantmovie.mp4", use "nonexistantmovie.mp4" as the filename parameter
5. For movie selection: First call list_movies, then call "select_movie" to let the system pick the best match from available movies"""

        # Run agent loop
        logger.info("="*80)
        logger.info(f"🤖 STARTING LLM AGENT")
        logger.info(f"   User query: {user_text}")
        logger.info("="*80)

        conversation = [{"role": "user", "content": user_text}]
        max_iterations = 5

        for iteration in range(max_iterations):
            logger.info("-"*80)
            logger.info(f"🔄 AGENT ITERATION {iteration + 1}/{max_iterations}")
            logger.info("-"*80)

            # Get LLM response with structured output
            model = config.OLLAMA_AGENT_MODEL if hasattr(config, 'OLLAMA_AGENT_MODEL') else 'qwen2.5:3b'

            logger.info(f"💬 LLM CALL")
            logger.info(f"   Model: {model}")
            logger.info(f"   System prompt:")
            logger.info("-"*80)
            logger.info(system_prompt)
            logger.info("-"*80)
            logger.info(f"   Conversation messages:")
            for i, msg in enumerate(conversation):
                logger.info(f"   Message {i+1} ({msg['role']}): {msg['content'][:500]}")
            logger.info("-"*80)

            response = ollama_client.chat(
                model=model,
                messages=[{"role": "system", "content": system_prompt}] + conversation,
                format={
                    "type": "object",
                    "properties": {
                        "function": {"type": "string"},
                        "describe": {"type": "string"},
                        "parameter": {"type": "string"}
                    },
                    "required": ["function", "describe", "parameter"]
                }
            )

            tool_call = response['message']['content']
            logger.info(f"💬 LLM RESPONSE: {tool_call}")

            # Parse tool call
            import json
            try:
                call_data = json.loads(tool_call)
                function_name = call_data.get("function", "")
                describe = call_data.get("describe", "")
                parameter_str = call_data.get("parameter", "{}")

                logger.info(f"Agent calling: {function_name} - {describe}")
                eel_log(f"🤖 {describe}")

                # Check if finished
                if function_name == "finished":
                    return describe

                # Handle special "select_movie" function (with or without server prefix)
                if function_name == "select_movie" or function_name.endswith(".select_movie"):
                    # Extract movie list from conversation history
                    movie_list = []
                    for msg in reversed(conversation):
                        if msg['role'] == 'user' and 'Tool result:' in msg['content']:
                            # Parse movie list from previous list_movies result
                            result_text = msg['content']
                            if 'Available movies:' in result_text or '.mp4' in result_text or '.mkv' in result_text:
                                # Extract movie filenames
                                import re
                                matches = re.findall(r'\d+\.\s+([^\n]+)', result_text)
                                if matches:
                                    movie_list = matches
                                    break

                    if movie_list:
                        # Ask LLM to select best match
                        logger.info("="*80)
                        logger.info(f"🎬 EXPLICIT MOVIE SELECTION")
                        logger.info(f"   User wants: {user_text}")
                        logger.info(f"   Available movies: {movie_list}")
                        logger.info("="*80)

                        # Create simple movie list without numbering
                        movie_titles = ', '.join([f'"{m}"' for m in movie_list])

                        selection_prompt = f"""Of the movies {movie_titles}, which one best matches: {user_text}

Respond with only the filename from the list above, nothing else."""

                        logger.info(f"📝 SELECTION PROMPT:")
                        logger.info("-"*80)
                        logger.info(selection_prompt)
                        logger.info("-"*80)

                        selection_response = ollama_client.chat(
                            model=model,
                            messages=[{"role": "user", "content": selection_prompt}]
                        )

                        selected_movie = selection_response['message']['content'].strip()
                        logger.info(f"🎬 LLM SELECTED: {selected_movie}")
                        logger.info(f"   Model used: {model}")
                        logger.info(f"   Full LLM response: {selection_response['message']['content']}")
                        logger.info("="*80)

                        # Add to conversation
                        conversation.append({"role": "assistant", "content": tool_call})
                        conversation.append({
                            "role": "user",
                            "content": f"Selected movie: {selected_movie}\n\nNow play this movie using media-server.play_movie"
                        })
                        continue
                    else:
                        logger.warning("No movie list found in conversation history")
                        conversation.append({"role": "assistant", "content": tool_call})
                        conversation.append({
                            "role": "user",
                            "content": "Error: No movie list available. Please call list_movies first."
                        })
                        continue

                # Parse function name (format: server.tool)
                if "." in function_name:
                    server_name, tool_name = function_name.split(".", 1)
                else:
                    logger.warning(f"Invalid function format: {function_name}")
                    continue

                # Parse parameters
                try:
                    params = json.loads(parameter_str) if parameter_str else {}
                except json.JSONDecodeError:
                    params = {"filename": parameter_str} if parameter_str else {}

                # Execute MCP tool on MCP thread
                logger.info("="*80)
                logger.info(f"🔧 MCP CALL (from agent)")
                logger.info(f"   Server: {server_name}")
                logger.info(f"   Tool: {tool_name}")
                logger.info(f"   Parameters: {params}")
                logger.info(f"   Call point: hal_voice_assistant.py:use_llm_agent")
                logger.info("="*80)

                future = asyncio.run_coroutine_threadsafe(
                    mcp_manager.call_tool(server_name, tool_name, params),
                    mcp_event_loop
                )
                tool_result = future.result(timeout=30)

                logger.info("="*80)
                logger.info(f"✅ MCP RESULT: {tool_result[:500] if len(tool_result) > 500 else tool_result}")
                logger.info("="*80)

                # Add to conversation
                conversation.append({"role": "assistant", "content": tool_call})
                conversation.append({
                    "role": "user",
                    "content": f"Tool result: {tool_result}\n\nContinue if needed, or call 'finished' if done."
                })

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse agent response: {e}")
                return "Sorry, I had trouble understanding how to help with that."

        return "Task completed"

    except Exception as e:
        logger.error(f"LLM agent error: {e}", exc_info=True)
        return f"Sorry, I encountered an error: {str(e)}"


async def process_command(user_text: str) -> str:
    """
    Process user command through MCP tools or LLM

    Args:
        user_text: Transcribed user speech

    Returns:
        Response text
    """
    logger.info(f"👤 User: {user_text}")
    eel_log(f"👤 User: {user_text}")

    try:
        # Try to match to MCP tool
        match = intent_matcher.match(user_text)

        if match:
            intent_name, intent_data = match
            logger.info(f"🎯 Matched intent: {intent_name}")
            eel_log(f"🎯 Using MCP tool: {intent_name}")

            # Extract parameters
            params = intent_matcher.extract_params(user_text, intent_data)
            server_name, tool_name = intent_matcher.get_tool_info(intent_data)

            # Special handling for play_movie - convert partial name to full filename
            if tool_name == "play_movie" and "filename" in params:
                filename = params["filename"]

                # If filename contains words like "about", "with", this is a description, use smart selection
                if any(word in filename.lower() for word in ["about", "with", "featuring", "starring"]):
                    logger.info(f"Filename '{filename}' is a description, using smart movie selection")
                    eel_log(f"🤖 Analyzing your request...")

                    # Get list of available movies
                    future = asyncio.run_coroutine_threadsafe(
                        mcp_manager.call_tool("media-server", "list_movies", {}),
                        mcp_event_loop
                    )
                    movies_result = future.result(timeout=30)

                    # Extract movie filenames from result
                    import re
                    movie_list = re.findall(r'\d+\.\s+([^\n]+\.mp4)', movies_result)

                    if movie_list:
                        logger.info("="*80)
                        logger.info(f"🎬 SMART MOVIE SELECTION")
                        logger.info(f"   User query: {user_text}")
                        logger.info(f"   Available movies: {movie_list}")
                        logger.info("="*80)

                        # Create simple selection prompt
                        movie_titles = ', '.join([f'"{m}"' for m in movie_list])
                        selection_prompt = f"""Of the movies {movie_titles}, which one best matches: {user_text}

Respond with only the filename from the list above, nothing else."""

                        logger.info(f"📝 SELECTION PROMPT:")
                        logger.info("-"*80)
                        logger.info(selection_prompt)
                        logger.info("-"*80)

                        # Ask LLM to select
                        model = config.OLLAMA_AGENT_MODEL if hasattr(config, 'OLLAMA_AGENT_MODEL') else 'qwen2.5:7b'
                        selection_response = ollama_client.chat(
                            model=model,
                            messages=[{"role": "user", "content": selection_prompt}]
                        )

                        selected_movie = selection_response['message']['content'].strip()
                        # Clean up response (remove quotes, extra text)
                        for movie in movie_list:
                            if movie.lower() in selected_movie.lower():
                                selected_movie = movie
                                break

                        logger.info(f"🎬 LLM SELECTED: {selected_movie}")
                        logger.info(f"   Model used: {model}")
                        logger.info(f"   Full LLM response: {selection_response['message']['content']}")
                        logger.info("="*80)

                        params["filename"] = selected_movie
                        eel_log(f"🎬 Selected: {selected_movie}")
                    else:
                        logger.warning("Could not extract movie list, falling back to agent")
                        agent_result = await use_llm_agent(user_text)
                        return agent_result
                else:
                    params["filename"] = await resolve_movie_filename(filename)
                    logger.info(f"Resolved movie filename: {params['filename']}")

            # Execute MCP tool - must run on MCP event loop since MCP sessions were created there
            logger.info("="*80)
            logger.info(f"🔧 MCP CALL")
            logger.info(f"   Server: {server_name}")
            logger.info(f"   Tool: {tool_name}")
            logger.info(f"   Parameters: {params}")
            logger.info(f"   Call point: hal_voice_assistant.py:process_command")
            logger.info("="*80)

            # Check if we're already in the MCP event loop
            try:
                current_loop = asyncio.get_running_loop()
                if current_loop == mcp_event_loop:
                    # Already in MCP loop, can call directly
                    result = await mcp_manager.call_tool(server_name, tool_name, params)
                else:
                    # Different loop, use run_coroutine_threadsafe
                    future = asyncio.run_coroutine_threadsafe(
                        mcp_manager.call_tool(server_name, tool_name, params),
                        mcp_event_loop
                    )
                    result = future.result(timeout=30)  # 30 second timeout
            except RuntimeError:
                # No running loop, use run_coroutine_threadsafe
                future = asyncio.run_coroutine_threadsafe(
                    mcp_manager.call_tool(server_name, tool_name, params),
                    mcp_event_loop
                )
                result = future.result(timeout=30)  # 30 second timeout

            logger.info("="*80)
            logger.info(f"✅ MCP RESULT: {result[:500] if len(result) > 500 else result}")
            logger.info("="*80)

            # Check if MCP call failed or returned error
            if result and ("error" in result.lower() or "not found" in result.lower() or "failed" in result.lower()):
                logger.warning(f"MCP tool returned error, trying LLM agent...")
                eel_log(f"⚠️ Tool failed, using LLM agent...")

                # Use LLM agent to interpret and retry
                agent_result = await use_llm_agent(user_text)
                return agent_result

            return result

        else:
            # No tool match - use LLM agent
            logger.info(f"💭 No tool match, using LLM agent...")
            eel_log("💭 Using LLM agent...")

            agent_result = await use_llm_agent(user_text)
            return agent_result

    except Exception as e:
        logger.error(f"Command processing error: {e}", exc_info=True)
        return f"Sorry, I encountered an error: {str(e)}"


# Eel exposed functions
@eel.expose
def get_status():
    """Get current system status"""
    return app_state

def run_voice_loop_in_thread():
    """Run voice loop in a separate thread with its own asyncio event loop"""
    global voice_loop_event_loop

    # Create new event loop for this thread
    voice_loop_event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(voice_loop_event_loop)

    logger.info("Voice loop thread started")

    try:
        # Run the voice loop
        voice_loop_event_loop.run_until_complete(voice_loop())
    except Exception as e:
        logger.error(f"Voice loop thread error: {e}", exc_info=True)
    finally:
        voice_loop_event_loop.close()
        logger.info("Voice loop thread stopped")

@eel.expose
def toggle_listening():
    """Toggle listening on/off"""
    global voice_loop_thread

    app_state['listening'] = not app_state['listening']
    logger.info(f"Toggle listening: {app_state['listening']}")

    if app_state['listening']:
        # Start voice loop in background thread
        logger.info("Starting voice loop thread...")
        voice_loop_thread = threading.Thread(target=run_voice_loop_in_thread, daemon=True)
        voice_loop_thread.start()
        logger.info("Voice loop thread started")
        return True
    else:
        logger.info("Stopping voice loop...")
        # The loop will stop when app_state['listening'] becomes False
        return False

@eel.expose
def update_wake_word(new_wake_word):
    """Update wake word"""
    try:
        app_state['wake_word'] = new_wake_word
        if voice_pipeline:
            voice_pipeline.change_wake_word(new_wake_word)
        eel_log(f"✅ Wake word changed to: {new_wake_word}")
        return True
    except Exception as e:
        eel_log(f"❌ Failed to change wake word: {e}")
        return False

@eel.expose
def update_language(language):
    """Update transcription language"""
    try:
        app_state['language'] = language
        if voice_pipeline:
            voice_pipeline.change_language(language)
        eel_log(f"✅ Language changed to: {language}")
        return True
    except Exception as e:
        eel_log(f"❌ Failed to change language: {e}")
        return False


# JavaScript callbacks (call JS from Python)
def eel_update_status(status, message):
    """Update UI status"""
    try:
        eel.updateStatus(status, message)
    except:
        pass

def eel_update_transcript(text):
    """Update transcript display"""
    try:
        eel.updateTranscript(text)
    except:
        pass

def eel_update_response(text):
    """Update response display"""
    try:
        eel.updateResponse(text)
    except:
        pass

def eel_log(message):
    """Add log message to UI"""
    try:
        eel.addLog(message)
    except:
        pass


async def generate_mapping_mode():
    """Generate intent mapping from MCP servers"""
    print("=" * 60)
    print("🔧 HAL Intent Mapping Generator")
    print("=" * 60)

    # Import mapping generator
    import sys
    sys.path.append('/home/hal/hal')
    from hal_mapping_generator import HALMappingGenerator

    # Initialize MCP manager
    manager = HALMCPManager()

    # Load servers config
    mcp_servers_config = config.MCP_SERVERS_CONFIG
    print(f"\n📂 Loading MCP servers from: {mcp_servers_config}")
    with open(mcp_servers_config, 'r') as f:
        config_data = json.load(f)

    # Handle both formats: direct config or wrapped in "mcpServers"
    if "mcpServers" in config_data:
        servers_config = config_data["mcpServers"]
    else:
        servers_config = config_data

    # Connect to servers
    await manager.connect_servers(servers_config)

    # Discover all tools
    all_tools = manager.get_all_tools()

    if not all_tools:
        print("❌ No tools found. Make sure MCP servers are configured correctly.")
        await manager.cleanup()
        return

    print(f"\n📊 Found {len(all_tools)} tools across {len(manager.sessions)} servers:")
    for tool in all_tools:
        print(f"   - {tool['server']}.{tool['tool']}")

    # Generate mapping using LLM
    generator = HALMappingGenerator(
        model=config.OLLAMA_AGENT_MODEL if hasattr(config, 'OLLAMA_AGENT_MODEL') else 'exaone3.5:2.4b',
        ollama_url=config.OLLAMA_URL if hasattr(config, 'OLLAMA_URL') else 'http://localhost:11434'
    )
    mapping = await generator.generate_mapping(all_tools)

    # Save mapping
    output_file = config.MCP_INTENT_MAPPING
    with open(output_file, 'w') as f:
        json.dump(mapping, f, indent=2)

    print(f"\n✅ Intent mapping saved to: {output_file}")

    # Display summary based on format
    if "servers" in mapping:
        # v2 format
        total_intents = sum(len(server_data.get("intents", {})) for server_data in mapping["servers"].values())
        print(f"📋 Generated {len(mapping['servers'])} servers with {total_intents} total intents:")

        for server_name, server_data in mapping["servers"].items():
            intents = server_data.get("intents", {})
            print(f"\n   🎯 {server_name}: {len(intents)} intents")
            print(f"      Scope: {server_data.get('scope', 'N/A')[:80]}...")
            print(f"      User keywords: {server_data.get('userScope', 'N/A')[:80]}")

            # Show first 2 intents for this server
            for intent_name, intent_data in list(intents.items())[:2]:
                print(f"        • {intent_name}: {intent_data.get('description', 'N/A')[:60]}")
    else:
        # v1 format
        print(f"📋 Generated {len(mapping)} intents:")
        for intent_name, intent_data in list(mapping.items())[:5]:
            print(f"\n   🎯 {intent_name}:")
            print(f"      Description: {intent_data.get('description', 'N/A')}")
            print(f"      Keywords: {', '.join(intent_data.get('keywords', []))}")
            print(f"      Tool: {intent_data['server']}.{intent_data['tool']}")

        if len(mapping) > 5:
            print(f"\n   ... and {len(mapping) - 5} more")

    print(f"\n💡 Edit {output_file} to customize the mappings")
    print(f"💡 Then run: python hal_voice_assistant.py")

    await manager.cleanup()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="HAL Voice Assistant - AI-powered voice control interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate intent mapping from MCP servers
  python hal_voice_assistant.py --generate-mapping

  # Run HAL Voice Assistant (default)
  python hal_voice_assistant.py
        """
    )

    parser.add_argument(
        "--generate-mapping",
        action="store_true",
        help="Generate intent mapping from MCP servers and exit"
    )

    args = parser.parse_args()

    # If generating mapping, do that and exit
    if args.generate_mapping:
        # Need to load config first
        global config
        config = get_config()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(generate_mapping_mode())
        return 0

    # Otherwise run normal voice assistant
    logger.info("=" * 60)
    logger.info("HAL Voice Assistant Starting...")
    logger.info("=" * 60)

    # Initialize system
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    success = loop.run_until_complete(initialize_system())

    if not success:
        logger.error("Failed to initialize system")
        return 1

    # Start Eel (this will block and run the event loop)
    try:
        logger.info("Starting Eel GUI on http://localhost:8080")
        eel.start('index.html', size=(1024, 768), port=8080, block=True)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        app_state['listening'] = False

    return 0


if __name__ == "__main__":
    sys.exit(main())
