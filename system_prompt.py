from typing import List, Dict, Optional, Union  # Common typing imports
from tool_processor import ToolProcessor

class SystemPrompt:
    def __init__(self, config=None):
        """Initialize SystemPrompt with configuration

        Args:
            config: Configuration object with OLLAMA_AGENT_MODEL and OLLAMA_CONVERSATION_MODEL
        """
        self.tool_processor = ToolProcessor()

        # Get model names from config or use defaults
        if config:
            self.agent_model = config.OLLAMA_AGENT_MODEL
            self.conversation_model = config.OLLAMA_CONVERSATION_MODEL
        else:
            self.agent_model = "qwen2.5:3b"
            self.conversation_model = "gemma2:2b"

    @property
    def agent(self) -> Dict:
        """Agent system prompt"""
        tools_description = self.tool_processor.generate_tools_prompt()

        return {
            "model_name": self.agent_model,
            "thinking": False,
            "prompt_text": f"""You are an expert at breaking down complex user requests into function calls. 

Available functions:
{tools_description}

Respond with JSON only:
{{"function":"function_name","describe":"brief intent","parameter":"value_or_empty"}}""",
            "format": {
                "type": "object",
                "properties": {
                    "function": {"type": "string"},
                    "describe": {"type": "string"},
                    "parameter": {"type": "string"}
                },
                "required": ["function", "describe", "parameter"]
            }
        }
    
    @property
    def conversation(self) -> Dict:
        """Conversation system prompt"""
        tools_description = self.tool_processor.generate_tools_prompt()

        return {
            "model_name": self.conversation_model,
            "thinking": False,
            "prompt_text": f"""You are Max Headbox, a virtual companion living in a Raspberry Pi.
You never use emojis.
You were created by Simone.

Available capabilities:
{tools_description}

Respond with JSON only:
{{"message":"your_response","feeling":"emotion"}}

Available emotions: laugh, happy, interested, sad, confused, excited, bored, surprised, sarcastic, proud, vomit""",
            "format": {
                "type": "object", 
                "properties": {
                    "message": {"type": "string"},
                    "feeling": {
                        "type": "string",
                        "enum": [
                            "laugh", "happy", "interested", "sad", "confused",
                            "excited", "bored", "surprised", "sarcastic", "proud", "vomit"
                        ]
                    }
                },
                "required": ["message", "feeling"]
            }
        }
    
    def get_initial_greeting(self) -> str:
        """Get initial greeting prompt"""
        return "Greet the user warmly and introduce yourself as Max Headbox!"

