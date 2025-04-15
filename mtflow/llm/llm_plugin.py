from typing import Callable

import os
import warnings

from pfund_plugins.base_plugin import BasePlugin
from pfund_plugins.function_registry import FunctionRegistry
from pfund_plugins.llm.literals import tFREE_LLM_PROVIDERS

with warnings.catch_warnings():
    warnings.filterwarnings("ignore",category=DeprecationWarning)
    import litellm


class LLMPlugin(BasePlugin):
    DEFAULT_MODELS = {
        'gemini': 'gemini-2.0-flash',  # https://ai.google.dev/pricing
        'groq': 'llama-3.2-90b-text-preview',
        'mistral': 'mistral-large-latest',
    }
    def __init__(self, provider: tFREE_LLM_PROVIDERS | str, model: str=''):
        super().__init__('llm')
        self.provider: str = provider.lower()
        assert self.provider in self.get_llm_providers(), f'Invalid provider: {self.provider}'
        assert f'{self.provider}_api_key'.upper() in os.environ, f'API key for {self.provider} is not set'
        if model:
            model = model.lower()
        elif self.provider in self.DEFAULT_MODELS:
            model = self.DEFAULT_MODELS[self.provider]
        else:
            raise ValueError(f'No model found for {self.provider}, please specify one')
        self.model: str = model
        self._function_registry = FunctionRegistry()

    @staticmethod
    def get_llm_providers():
        return [provider.value for provider in litellm.LlmProviders]

    @staticmethod
    def get_free_llm_api_key(provider: tFREE_LLM_PROVIDERS) -> str | None:
        if provider == 'groq':
            return 'https://console.groq.com/keys'
        elif provider == 'mistral':
            return 'https://console.mistral.ai/api-keys'
        elif provider == 'gemini':
            return 'https://ai.google.dev/gemini-api/docs/api-key'
    
    def _get_function_tools(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": func_dict['function'],
                    "description": func_dict['description'],
                    "parameters": func_dict['schema'],
                }
            }
            for func_dict in self._function_registry
        ]
    
    def ask(self, message: str, context="") -> str:
        # TODO
        # function_tools = self._get_function_tools()
        response = litellm.completion(
            model='/'.join([self.provider, self.model]), 
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": message}
            ] if context else [{"role": "user", "content": message}],
            # tools=function_tools,
        )
        return response.choices[0].message.content
    
    def register(self, func: Callable, prompt: str='', endpoint: str=''):
        '''
        Register a function to be used in the LLM.
        '''
        self._function_registry.register(func, prompt=prompt, endpoint=endpoint)
