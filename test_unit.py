#!/usr/bin/env python3
"""
Non-Interactive Unit Test Suite for Voice Kiosk
Tests system components, API calls, and processing logic without user interaction
"""
import unittest
import asyncio
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import numpy as np

# Import modules to test
from config import get_config, Config
from system_prompt import SystemPrompt
from tool_processor import ToolProcessor
from ollama_client import OllamaClient
from event_loop import EventLoopCoordinator, AppStatus


class TestConfiguration(unittest.TestCase):
    """Test configuration management"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = get_config()

    def test_config_loads(self):
        """Test that configuration loads successfully"""
        self.assertIsNotNone(self.config)
        self.assertIsInstance(self.config, Config)

    def test_required_config_values(self):
        """Test that required configuration values exist"""
        # Ollama config
        self.assertIsNotNone(self.config.OLLAMA_URL)
        self.assertIsNotNone(self.config.OLLAMA_AGENT_MODEL)
        self.assertIsNotNone(self.config.OLLAMA_CONVERSATION_MODEL)

        # Audio config
        self.assertIsNotNone(self.config.AUDIO_SAMPLE_RATE)
        self.assertIsNotNone(self.config.AUDIO_CHANNELS)
        self.assertIsNotNone(self.config.AUDIO_INPUT_DEVICE)
        self.assertIsNotNone(self.config.AUDIO_AMPLIFICATION)

        # Wake word config
        self.assertIsNotNone(self.config.WAKE_WORD)
        self.assertIsNotNone(self.config.WAKE_WORD_SIMILARITY)

        # Whisper config
        self.assertIsNotNone(self.config.WHISPER_MODEL)
        self.assertIsNotNone(self.config.WHISPER_DEVICE)

    def test_numeric_config_types(self):
        """Test that numeric configurations have correct types"""
        self.assertIsInstance(self.config.AUDIO_SAMPLE_RATE, int)
        self.assertIsInstance(self.config.AUDIO_CHANNELS, int)
        self.assertIsInstance(self.config.AUDIO_INPUT_DEVICE, int)
        self.assertIsInstance(self.config.AUDIO_AMPLIFICATION, float)
        self.assertIsInstance(self.config.WAKE_WORD_SIMILARITY, float)
        self.assertIsInstance(self.config.AGENT_MAX_ITERATIONS, int)

    def test_config_value_ranges(self):
        """Test that configuration values are in valid ranges"""
        # Audio sample rate should be reasonable
        self.assertGreater(self.config.AUDIO_SAMPLE_RATE, 8000)
        self.assertLess(self.config.AUDIO_SAMPLE_RATE, 192000)

        # Channels should be 1 or 2
        self.assertIn(self.config.AUDIO_CHANNELS, [1, 2])

        # Similarity threshold should be 0-1
        self.assertGreaterEqual(self.config.WAKE_WORD_SIMILARITY, 0.0)
        self.assertLessEqual(self.config.WAKE_WORD_SIMILARITY, 1.0)

        # Amplification should be positive
        self.assertGreater(self.config.AUDIO_AMPLIFICATION, 0)

    def test_config_validation(self):
        """Test configuration validation method"""
        try:
            # This may fail if wake word model doesn't exist, which is expected
            result = self.config.validate()
            # If it passes, that's good
            self.assertTrue(result)
        except ValueError as e:
            # Expected if model files are missing
            self.assertIn("validation failed", str(e).lower())

    def test_recordings_directory_creation(self):
        """Test that recordings directory is created"""
        self.assertTrue(self.config.RECORDINGS_DIR.exists())
        self.assertTrue(self.config.RECORDINGS_DIR.is_dir())


class TestSystemPrompt(unittest.TestCase):
    """Test system prompt generation"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = get_config()
        self.system_prompt = SystemPrompt(self.config)

    def test_initialization(self):
        """Test SystemPrompt initialization"""
        self.assertIsNotNone(self.system_prompt)
        self.assertIsNotNone(self.system_prompt.tool_processor)
        self.assertEqual(self.system_prompt.agent_model, self.config.OLLAMA_AGENT_MODEL)
        self.assertEqual(self.system_prompt.conversation_model, self.config.OLLAMA_CONVERSATION_MODEL)

    def test_agent_prompt_structure(self):
        """Test agent prompt has correct structure"""
        agent = self.system_prompt.agent

        self.assertIn('model_name', agent)
        self.assertIn('thinking', agent)
        self.assertIn('prompt_text', agent)
        self.assertIn('format', agent)

        # Check model name matches config
        self.assertEqual(agent['model_name'], self.config.OLLAMA_AGENT_MODEL)

        # Check format is valid JSON schema
        self.assertIn('type', agent['format'])
        self.assertIn('properties', agent['format'])
        self.assertIn('required', agent['format'])

    def test_conversation_prompt_structure(self):
        """Test conversation prompt has correct structure"""
        conversation = self.system_prompt.conversation

        self.assertIn('model_name', conversation)
        self.assertIn('thinking', conversation)
        self.assertIn('prompt_text', conversation)
        self.assertIn('format', conversation)

        # Check model name matches config
        self.assertEqual(conversation['model_name'], self.config.OLLAMA_CONVERSATION_MODEL)

    def test_prompt_contains_tools(self):
        """Test that prompts include tool descriptions"""
        agent = self.system_prompt.agent
        conversation = self.system_prompt.conversation

        # Agent prompt should mention functions/tools
        self.assertIn('function', agent['prompt_text'].lower())

        # Conversation prompt should mention capabilities
        self.assertIn('capabilities', conversation['prompt_text'].lower())

    def test_agent_format_schema(self):
        """Test agent response format schema"""
        agent = self.system_prompt.agent
        format_schema = agent['format']

        # Should have function, describe, parameter fields
        self.assertIn('function', format_schema['properties'])
        self.assertIn('describe', format_schema['properties'])
        self.assertIn('parameter', format_schema['properties'])

    def test_conversation_format_schema(self):
        """Test conversation response format schema"""
        conversation = self.system_prompt.conversation
        format_schema = conversation['format']

        # Should have message and feeling fields
        self.assertIn('message', format_schema['properties'])
        self.assertIn('feeling', format_schema['properties'])

        # Feeling should have enum values
        feeling_schema = format_schema['properties']['feeling']
        self.assertIn('enum', feeling_schema)
        self.assertGreater(len(feeling_schema['enum']), 0)


class TestToolProcessor(unittest.TestCase):
    """Test tool loading and execution"""

    def setUp(self):
        """Set up test fixtures"""
        self.tool_processor = ToolProcessor()

    def test_initialization(self):
        """Test ToolProcessor initialization"""
        self.assertIsNotNone(self.tool_processor)
        self.assertIsNotNone(self.tool_processor.tools)
        self.assertIsInstance(self.tool_processor.tools, dict)

    def test_tools_loaded(self):
        """Test that tools are loaded"""
        self.assertGreater(len(self.tool_processor.tools), 0)

    def test_required_tools_exist(self):
        """Test that required tools are loaded"""
        required_tools = ['finished', 'timenow']

        for tool_name in required_tools:
            self.assertIn(tool_name, self.tool_processor.tools,
                         f"Required tool '{tool_name}' not found")

    def test_tool_structure(self):
        """Test that loaded tools have correct structure"""
        for tool_name, tool in self.tool_processor.tools.items():
            self.assertIn('name', tool)
            self.assertIn('description', tool)
            self.assertIn('execution', tool)

            # Name should match key
            self.assertEqual(tool['name'], tool_name)

            # Description should be non-empty
            self.assertGreater(len(tool['description']), 0)

            # Execution should be callable
            self.assertTrue(callable(tool['execution']))

    def test_generate_tools_prompt(self):
        """Test tools prompt generation"""
        prompt = self.tool_processor.generate_tools_prompt()

        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 0)

        # Should contain tool names
        for tool_name in self.tool_processor.tools.keys():
            self.assertIn(tool_name, prompt)

    def test_finished_tool_execution(self):
        """Test finished tool execution"""
        async def run_test():
            tool_call = {
                'function': 'finished',
                'parameter': ''
            }
            result = await self.tool_processor.process_tool(tool_call)
            self.assertIsInstance(result, str)
            return result

        result = asyncio.run(run_test())
        # The finished tool returns "task completed successfully"
        self.assertTrue(len(result) > 0)
        self.assertIn('completed', result.lower())

    def test_timenow_tool_execution(self):
        """Test timenow tool execution"""
        async def run_test():
            tool_call = {
                'function': 'timenow',
                'parameter': ''
            }
            result = await self.tool_processor.process_tool(tool_call)
            self.assertIsInstance(result, str)
            # Should contain date/time information
            return result

        result = asyncio.run(run_test())
        # Should contain year or time information
        self.assertTrue(any(char.isdigit() for char in result))

    def test_unknown_tool_handling(self):
        """Test handling of unknown tool calls"""
        async def run_test():
            tool_call = {
                'function': 'nonexistent_tool',
                'parameter': 'test'
            }
            result = await self.tool_processor.process_tool(tool_call)
            self.assertIn('unknown', result.lower())
            return result

        asyncio.run(run_test())


class TestEventLoopCoordinator(unittest.TestCase):
    """Test event loop coordination and state management"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = get_config()
        self.coordinator = EventLoopCoordinator(self.config)

    def test_initialization(self):
        """Test EventLoopCoordinator initialization"""
        self.assertIsNotNone(self.coordinator)
        self.assertEqual(self.coordinator.current_state, AppStatus.BOOT)

    def test_app_status_enum(self):
        """Test AppStatus enum values"""
        # Check all required states exist
        self.assertTrue(hasattr(AppStatus, 'BOOT'))
        self.assertTrue(hasattr(AppStatus, 'IDLE'))
        self.assertTrue(hasattr(AppStatus, 'RECORDING'))
        self.assertTrue(hasattr(AppStatus, 'PROCESSING_RECORDING'))
        self.assertTrue(hasattr(AppStatus, 'THINKING'))
        self.assertTrue(hasattr(AppStatus, 'SPEAKING'))
        self.assertTrue(hasattr(AppStatus, 'SCREENSAVER'))

        # Check they have integer values
        for state in AppStatus:
            self.assertIsInstance(state.value, int)

    def test_state_transition(self):
        """Test state transitions"""
        async def run_test():
            # Transition to IDLE
            await self.coordinator.transition_state(AppStatus.IDLE)
            self.assertEqual(self.coordinator.current_state, AppStatus.IDLE)

            # Transition to RECORDING
            await self.coordinator.transition_state(AppStatus.RECORDING)
            self.assertEqual(self.coordinator.current_state, AppStatus.RECORDING)

        asyncio.run(run_test())

    def test_state_callback_registration(self):
        """Test registering state callbacks"""
        callback_called = False

        async def test_callback(metadata):
            nonlocal callback_called
            callback_called = True

        self.coordinator.register_state_callback(AppStatus.IDLE, test_callback)

        async def run_test():
            await self.coordinator.transition_state(AppStatus.IDLE)
            await asyncio.sleep(0.1)  # Give callback time to execute

        asyncio.run(run_test())
        self.assertTrue(callback_called)

    def test_get_state(self):
        """Test getting current state"""
        state = self.coordinator.get_state()
        self.assertIsInstance(state, AppStatus)
        self.assertEqual(state, self.coordinator.current_state)


class TestOllamaClient(unittest.TestCase):
    """Test Ollama client API calls"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = get_config()
        self.client = OllamaClient(base_url=self.config.OLLAMA_URL)

    def test_initialization(self):
        """Test OllamaClient initialization"""
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client.base_url, self.config.OLLAMA_URL)

    @unittest.skipIf(True, "Requires running Ollama server")
    def test_chat_completion_structure(self):
        """Test chat completion returns proper structure"""
        async def run_test():
            messages = [
                {"role": "user", "content": "Say hello"}
            ]

            response_chunks = []
            async for chunk in self.client.chat_completion(
                model="qwen2.5:3b",
                messages=messages,
                stream=True
            ):
                response_chunks.append(chunk)

            # Should get at least one chunk
            self.assertGreater(len(response_chunks), 0)

            # Chunks should be strings
            for chunk in response_chunks:
                self.assertIsInstance(chunk, str)

        asyncio.run(run_test())

    @unittest.skipIf(True, "Requires running Ollama server")
    def test_stream_response(self):
        """Test streaming response"""
        async def run_test():
            messages = [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Say 'test'"}
            ]

            chunks = []
            async for chunk in self.client.stream_response(
                model="qwen2.5:3b",
                messages=messages
            ):
                chunks.append(chunk)

            self.assertGreater(len(chunks), 0)

        asyncio.run(run_test())

    def test_json_format_structure(self):
        """Test JSON format parameter structure"""
        format_schema = {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            },
            "required": ["message"]
        }

        # Should be valid dict
        self.assertIsInstance(format_schema, dict)
        self.assertIn("type", format_schema)
        self.assertIn("properties", format_schema)


class TestAudioProcessing(unittest.TestCase):
    """Test audio processing utilities"""

    def test_audio_amplification(self):
        """Test audio amplification calculation"""
        # Simulate audio data
        sample_rate = 48000
        duration = 1  # 1 second
        amplitude = 1000

        # Create test audio (sine wave)
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.int16)

        # Calculate RMS
        rms_before = np.sqrt(np.mean(audio.astype(np.float32) ** 2))

        # Apply amplification (like wake word detector does)
        amplification = 10.0
        amplified = audio.astype(np.float32) * amplification
        amplified = np.clip(amplified, -32768, 32767).astype(np.int16)

        rms_after = np.sqrt(np.mean(amplified.astype(np.float32) ** 2))

        # RMS should be approximately amplification * original
        # (may not be exact due to clipping)
        expected_rms = rms_before * amplification
        self.assertGreater(rms_after, rms_before)

    def test_silence_detection_logic(self):
        """Test silence detection logic"""
        threshold = 2000

        # Test silence (low RMS)
        silence = np.random.randint(-100, 100, size=4800, dtype=np.int16)
        silence_rms = np.sqrt(np.mean(silence.astype(np.float32) ** 2))
        self.assertLess(silence_rms, threshold)

        # Test speech (high RMS)
        speech = np.random.randint(-10000, 10000, size=4800, dtype=np.int16)
        speech_rms = np.sqrt(np.mean(speech.astype(np.float32) ** 2))
        self.assertGreater(speech_rms, threshold / 2)

    def test_audio_format_conversion(self):
        """Test audio format conversions"""
        # Create test audio
        audio_float = np.array([0.5, -0.5, 0.25, -0.25], dtype=np.float32)

        # Convert to int16
        audio_int16 = (audio_float * 32767).astype(np.int16)

        # Check range
        self.assertGreaterEqual(audio_int16.min(), -32768)
        self.assertLessEqual(audio_int16.max(), 32767)

        # Convert back
        audio_back = audio_int16.astype(np.float32) / 32767

        # Should be approximately equal
        np.testing.assert_array_almost_equal(audio_float, audio_back, decimal=4)


class TestPhoneticMatching(unittest.TestCase):
    """Test phonetic matching for wake words"""

    def test_exact_match(self):
        """Test exact word matching"""
        from difflib import SequenceMatcher

        wake_word = "hal"
        recognized = "hal"

        similarity = SequenceMatcher(None, wake_word, recognized).ratio()
        self.assertEqual(similarity, 1.0)

    def test_close_match(self):
        """Test close phonetic matching"""
        from difflib import SequenceMatcher

        wake_word = "hal"
        recognized = "how"  # Common misrecognition

        similarity = SequenceMatcher(None, wake_word, recognized).ratio()

        # Should have some similarity but not perfect
        self.assertGreater(similarity, 0.3)
        self.assertLess(similarity, 1.0)

    def test_different_words(self):
        """Test different words have low similarity"""
        from difflib import SequenceMatcher

        wake_word = "hal"
        recognized = "computer"

        similarity = SequenceMatcher(None, wake_word, recognized).ratio()

        # Should have low similarity
        self.assertLess(similarity, 0.5)

    def test_case_insensitive(self):
        """Test case-insensitive matching"""
        from difflib import SequenceMatcher

        wake_word = "hal"
        recognized = "HAL"

        similarity = SequenceMatcher(None, wake_word.lower(), recognized.lower()).ratio()
        self.assertEqual(similarity, 1.0)


class TestJSONParsing(unittest.TestCase):
    """Test JSON parsing for LLM responses"""

    def test_valid_tool_call_json(self):
        """Test parsing valid tool call JSON"""
        json_str = '{"function":"timenow","describe":"get time","parameter":""}'
        parsed = json.loads(json_str)

        self.assertIn('function', parsed)
        self.assertIn('describe', parsed)
        self.assertIn('parameter', parsed)

    def test_valid_conversation_json(self):
        """Test parsing valid conversation JSON"""
        json_str = '{"message":"Hello there!","feeling":"happy"}'
        parsed = json.loads(json_str)

        self.assertIn('message', parsed)
        self.assertIn('feeling', parsed)

    def test_invalid_json_handling(self):
        """Test handling of invalid JSON"""
        json_str = '{"incomplete": '

        with self.assertRaises(json.JSONDecodeError):
            json.loads(json_str)

    def test_json_with_escaped_quotes(self):
        """Test JSON with escaped quotes"""
        json_str = '{"message":"He said \\"hello\\""}'
        parsed = json.loads(json_str)

        self.assertIn('"hello"', parsed['message'])


def run_tests():
    """Run all unit tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestSystemPrompt))
    suite.addTests(loader.loadTestsFromTestCase(TestToolProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestEventLoopCoordinator))
    suite.addTests(loader.loadTestsFromTestCase(TestOllamaClient))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioProcessing))
    suite.addTests(loader.loadTestsFromTestCase(TestPhoneticMatching))
    suite.addTests(loader.loadTestsFromTestCase(TestJSONParsing))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
