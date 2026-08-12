from typing import Dict
from app.problems.base import ProblemGeneratorProtocol


class ProblemRegistry:
    """Registry pattern implementation for registering and retrieving problem type generators."""

    def __init__(self) -> None:
        self._generators: Dict[str, ProblemGeneratorProtocol] = {}

    def register(self, generator: ProblemGeneratorProtocol) -> None:
        """Register a problem domain generator instance.

        Raises:
            ValueError: If a generator with the same problem_type is already registered.
        """
        p_type = generator.problem_type
        if p_type in self._generators:
            raise ValueError(f"Problem generator for type '{p_type}' is already registered.")
        self._generators[p_type] = generator

    def get(self, problem_type: str) -> ProblemGeneratorProtocol:
        """Retrieve the registered generator for a problem type.

        Raises:
            KeyError: If no generator is registered for the specified problem_type.
        """
        if problem_type not in self._generators:
            raise KeyError(
                f"No generator registered for problem type '{problem_type}'. "
                f"Available types: {list(self._generators.keys())}"
            )
        return self._generators[problem_type]

    def list_types(self) -> list[str]:
        """List all registered problem type identifiers."""
        return list(self._generators.keys())


# Global registry singleton instance
problem_registry = ProblemRegistry()
