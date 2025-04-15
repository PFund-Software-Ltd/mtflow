from typing import TypedDict


class SchemaProperty(TypedDict):
    type: str  # Data type (e.g., "string", "integer", "boolean")
    description: str  # Description of the parameter
    enum: list[str] | None  # Allowed values (if applicable)


class SchemaType(TypedDict):
    type: str  # Always "object" for function parameters
    properties: dict[str, SchemaProperty]  # Defines function parameters
    required: list[str]  # Required parameters
