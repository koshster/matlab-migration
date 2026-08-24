"""Problems domain package containing base protocols, registry, and problem implementations."""

# Import domain modules to register plugins with problem_registry
import app.problems.beam.generator  # noqa: F401
import app.problems.rigid_body.generator  # noqa: F401
import app.problems.truss.generator  # noqa: F401
