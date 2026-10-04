"""Shared boundary for provider adapters; user data never becomes instructions."""

from typing import Any, Protocol


class StructuredModel(Protocol):
    def complete_json(
        self, *, instructions: str, data: dict[str, str], schema: dict[str, Any]
    ) -> object:
        """Return decoded JSON constrained to schema, or raise on provider failure.

        Adapters must put instructions in the system/developer role and serialize
        data separately in the user role. They must not log data or provider errors.
        Model IDs and credentials belong in environment configuration.
        """
