# TODO: store prompt in delta lake for version control



import functools

PROMPT_REGISTRY = {}  # Stores function prompts for lookup

def prompted(llm_prompt: str):
    """Decorator to extend a function's docstring with an LLM-friendly prompt."""
    def decorator(func):
        # Extend the function's docstring
        original_doc = func.__doc__ or ""
        extended_doc = f"{original_doc}\n\n🔹 **LLM Prompt:** {llm_prompt}"
        func.__doc__ = extended_doc  # Modify the function docstring dynamically
        
        # Register the function in the prompt registry
        PROMPT_REGISTRY[func.__name__] = {
            "func": func,
            "doc": extended_doc,
            "llm_prompt": llm_prompt,
        }

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper
    return decorator
