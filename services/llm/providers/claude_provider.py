import json
import os
import urllib.request
import urllib.error

from .base import BaseLLMProvider

class ClaudeProvider(BaseLLMProvider):
    """
    Provider for the Anthropic Claude API.
    Expects ANTHROPIC_API_KEY environment variable.
    """

    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: str = None):
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.api_url = "https://api.anthropic.com/v1/messages"
        
        if not self.api_key:
            import warnings
            warnings.warn("ClaudeProvider initialized without ANTHROPIC_API_KEY. Calls will fail.")

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Sends a generation request to the Anthropic Messages API.
        """
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set.")

        model_to_use = kwargs.get("model", self.model)
        
        # The Messages API requires an array of messages
        payload = {
            "model": model_to_use,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            self.api_url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': self.api_key,
                'anthropic-version': '2023-06-01'
            }
        )

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                # Extract the text content from the first content block
                content_blocks = result.get("content", [])
                text_content = "".join([block.get("text", "") for block in content_blocks if block.get("type") == "text"])
                return text_content
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise RuntimeError(f"Claude API HTTP Error {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Could not connect to Anthropic API. Error: {e}")
