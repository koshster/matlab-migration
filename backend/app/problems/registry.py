from app.problems.base import ProblemGeneratorProtocol


class ProblemRegistry:
    """Registry pattern implementation for registering and retrieving problem type generators."""

    def __init__(self) -> None:
        self._generators: dict[str, ProblemGeneratorProtocol] = {}

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

    def all(self) -> list[ProblemGeneratorProtocol]:
        """Every registered generator, for building the assignment builder's
        problem-type picker without hardcoding any type."""
        return list(self._generators.values())


# Global registry singleton instance
problem_registry = ProblemRegistry()
