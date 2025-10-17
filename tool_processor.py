import asyncio
import logging
import json
import importlib
import os
from pathlib import Path
from typing import Dict, List, Any, Callable

logger = logging.getLogger(__name__)

class ToolProcessor:
    def __init__(self):
        """Initialize tool processor and load tools"""
        logger.info("Initializing ToolProcessor")
        self.tools = self._load_tools()
        logger.info(f"ToolProcessor initialized with {len(self.tools)} tools")

    def _load_tools(self) -> Dict[str, Dict]:
        """Dynamically load tools from tools directory"""
        logger.info("Loading tools from tools directory...")
        tools = {}

        tools_dir = Path(__file__).parent / 'tools'
        if not tools_dir.exists():
            logger.warning(f"Tools directory not found: {tools_dir}")
            return tools

        # Find all tool files
        tool_files = list(tools_dir.glob('*_tool.py'))
        logger.info(f"Found {len(tool_files)} tool file(s)")

        for tool_file in tool_files:
            try:
                # Import the tool module
                module_name = f"tools.{tool_file.stem}"
                logger.debug(f"Importing tool module: {module_name}")

                tool_module = importlib.import_module(module_name)

                # Get tool definition
                if hasattr(tool_module, 'tool_def'):
                    tool_def = tool_module.tool_def
                    tool_name = tool_def['name']

                    tools[tool_name] = {
                        "name": tool_name,
                        "description": tool_def['description'],
                        "params": tool_def.get('params', ''),
                        "execution": tool_def['execution'],
                        "dangerous": False
                    }

                    logger.info(f"Loaded tool: {tool_name} - {tool_def['description']}")
                else:
                    logger.warning(f"Tool module {module_name} missing 'tool_def' attribute")

            except Exception as e:
                logger.error(f"Error loading tool from {tool_file}: {e}", exc_info=True)

        logger.info(f"Tool loading complete: {len(tools)} tool(s) loaded")
        return tools
    
    def get_tools_list(self) -> Dict[str, Dict]:
        """Get list of available tools"""
        return self.tools
    
    def generate_tools_prompt(self) -> str:
        """Generate tools description for prompts"""
        tools_list = []
        for tool in self.tools.values():
            if tool['params']:
                tools_list.append(f"- {tool['name']}({tool['params']}): {tool['description']}")
            else:
                tools_list.append(f"- {tool['name']}: {tool['description']}")
        return "\n".join(tools_list)
    
    async def process_tool(self, tool_call: Dict) -> str:
        """Process a tool call"""
        function_name = tool_call.get('function', '')
        parameter = tool_call.get('parameter', '')
        
        logger.info(f"Processing tool: {function_name}('{parameter}')")
        
        if function_name in self.tools:
            try:
                tool_func = self.tools[function_name]['execution']
                result = await tool_func(parameter)
                return result
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                return f"Error executing {function_name}: {str(e)}"
        else:
            logger.warning(f"Unknown tool: {function_name}")
            return f"Unknown tool: {function_name}"
    
    async def agent_loop(self, user_input: str, ollama_client, system_prompt: str,
                        max_iterations: int = 5, model: str = "qwen2.5:3b") -> str:
        """Run agent loop with tool calling

        Args:
            user_input: User's input text
            ollama_client: Ollama client instance
            system_prompt: System prompt for the agent
            max_iterations: Maximum number of iterations
            model: Model to use for agent (default: qwen2.5:3b)
        """
        conversation_history = []
        cumulative_result = ""
        iterations = 0

        conversation_history.append({"role": "user", "content": user_input})

        while iterations < max_iterations:
            iterations += 1

            # Get AI response with tool call
            response = ""
            async for chunk in ollama_client.stream_response(
                model,
                [{"role": "system", "content": system_prompt}] + conversation_history,
                format={
                    "type": "object",
                    "properties": {
                        "function": {"type": "string"},
                        "describe": {"type": "string"}, 
                        "parameter": {"type": "string"}
                    },
                    "required": ["function", "describe", "parameter"]
                }
            ):
                response += chunk
                
            try:
                tool_call = json.loads(response)
                function_name = tool_call.get('function', '')
                
                logger.info(f"Agent wants to call: {function_name}('{tool_call.get('parameter', '')}')")
                
                if function_name == 'finished':
                    break
                    
                # Execute tool
                tool_result = await self.process_tool(tool_call)
                cumulative_result += f"Step {iterations}: {tool_result}\n"
                
                # Add to conversation
                conversation_history.append({
                    "role": "assistant", 
                    "content": response
                })
                conversation_history.append({
                    "role": "user",
                    "content": f"Tool result: {tool_result}. Continue if needed."
                })
                
            except json.JSONDecodeError:
                logger.error("Failed to parse tool call JSON")
                break
                
        return cumulative_result if cumulative_result else "No tasks executed"

