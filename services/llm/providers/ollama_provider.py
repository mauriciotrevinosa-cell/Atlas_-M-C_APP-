import json
import urllib.request
import urllib.error
from typing import Optional

from .base import BaseLLMProvider

class OllamaProvider(BaseLLMProvider):
    """
    Provider for a local Ollama instance.
    Defaults to the standard port: http://localhost:11434
    """

    def __init__(self, model: str = "qwen2.5", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api/generate"

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Sends a synchronous generation request to Ollama and returns the aggregated text.
        By default, it disables streaming to simplify parsing for the agents.
        """
        
        # Merge kwargs to allow overriding model per request if needed
        model_to_use = kwargs.get("model", self.model)
        
        payload = {
            "model": model_to_use,
            "prompt": prompt,
            "stream": False
        }
        
        # Inject optional parameters like temperature if provided
        if "temperature" in kwargs:
            payload["options"] = {"temperature": kwargs["temperature"]}

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            self.api_url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get("response", "")
                
        except urllib.error.URLError as e:
            # Re-raise with a clearer message for debugging
            raise ConnectionError(f"Could not connect to Ollama at {self.api_url}. Is Ollama running? Error: {e}")
