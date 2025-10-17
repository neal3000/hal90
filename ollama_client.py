from typing import List, Dict, Optional, Union  # Common typing imports
import aiohttp
import json
import logging
from typing import AsyncGenerator, Dict, Any

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        
    async def chat_completion(self, model: str, messages: List[Dict], 
                            stream: bool = False, 
                            format: Dict = None,
                            thinking: bool = False) -> AsyncGenerator[str, None]:
        """Send chat completion request to Ollama"""
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "num_predict": 512,
                "temperature": 0.7,
                "top_p": 0.9,
            }
        }
        
        if format:
            payload["format"] = format
        if thinking is not None:
            payload["thinking"] = thinking
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/api/chat", 
                                      json=payload, 
                                      timeout=aiohttp.ClientTimeout(total=60)) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ollama API error: {error_text}")
                        yield json.dumps({"error": f"API error: {error_text}"})
                        return
                        
                    if stream:
                        async for line in response.content:
                            if line:
                                line_text = line.decode('utf-8').strip()
                                if line_text:
                                    try:
                                        chunk_data = json.loads(line_text)
                                        if 'message' in chunk_data and 'content' in chunk_data['message']:
                                            yield chunk_data['message']['content']
                                    except json.JSONDecodeError:
                                        logger.warning(f"Invalid JSON chunk: {line_text}")
                    else:
                        data = await response.json()
                        yield data['message']['content']
                        
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            yield json.dumps({"error": str(e)})
            
    async def generate_response(self, model: str, prompt: str, 
                              system: str = None) -> str:
        """Generate a simple response (non-streaming)"""
        messages = [{"role": "user", "content": prompt}]
        if system:
            messages.insert(0, {"role": "system", "content": system})
            
        response = ""
        async for chunk in self.chat_completion(model, messages, stream=False):
            response = chunk
            
        return response
        
    async def stream_response(self, model: str, messages: List[Dict], 
                            format: Dict = None) -> AsyncGenerator[str, None]:
        """Stream response from Ollama"""
        async for chunk in self.chat_completion(model, messages, stream=True, format=format):
            yield chunk

