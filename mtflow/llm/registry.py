from typing import Callable

from pfund_plugins.utils import generate_schema_from_docstring


class FunctionRegistry:
    def __init__(self):
        self._registry = {}  # {category: {function_name: function_dict}}
        self._categories = {}  # {category: description}
    
    @property
    def categories(self) -> dict:
        return self._categories

    def add_category(self, category: str, description: str = ""):
        """Adds a new category with an optional description."""
        if category not in self._categories:
            self._categories[category] = description
            self._registry[category] = {}
    
    def register(self, func: Callable, category: str, prompt: str='', endpoint: str=''):
        '''
        Args:
            prompt: prompt is used as an extension to the function's docstring.
                think of it as providing guidance to LLM on how to use the function.
            endpoint: API endpoint. If provided, LLM will call the function via the API endpoint instead of calling the function directly.
        '''
        if category not in self._categories:
            raise ValueError(f"Category '{category}' does not exist. Please add it using `add_category()` first.")
        self._registry[category][func.__name__] = {
            'function': func,
            'description': func.__doc__ + f'\n {prompt}',
            'schema': generate_schema_from_docstring(func),
            'endpoint': endpoint or func.__name__.replace('_', '-'),
        }

    def get_registered_function(self, category: str, func_name: str) -> dict | None:
        """Retrieves a function from a given category."""
        return self._registry.get(category, {}).get(func_name, None)

    def get_functions_by_category(self, category: str) -> dict:
        """Returns all functions within a specific category."""
        return self._registry.get(category, {})
    