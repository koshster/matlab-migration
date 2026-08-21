from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class VisualElementSchema(BaseModel):
    """Declarative graphical element emitted to the frontend renderer."""

    element_type: str = Field(
        ...,
        description=("Type of graphic primitive (e.g. node, member, pin, roller, load, moment)"),
    )
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Properties describing coordinates, magnitudes, vectors, labels, or styles",
    )


class AnswerFieldSpec(BaseModel):
    """Specification for a single input field in the student answer form."""

    field_id: str = Field(
        ..., description="Unique key for answer field (e.g. member_1_2, reaction_Ax)"
    )
    label: str = Field(..., description="Human readable label displayed to the student")
    unit: str = Field(default="", description="Units of value (e.g. kN, N-m, m)")
    value_type: str = Field(
        default="numeric",
        description="Data type of input (e.g., 'numeric', 'enum', 'text')",
    )
    options: list[str] | None = Field(
        default=None,
        description="Selectable enum options (e.g. ['Tension', 'Compression', 'Zero'])",
    )


class ProblemDisplayData(BaseModel):
    """Public problem specification sent to the client (NO solution data)."""

    problem_type: str = Field(
        ..., description="Domain identifier (e.g. truss, frame_2d, rigid_body)"
    )
    seed: int = Field(..., description="RNG seed used to synthesize geometry")
    title: str = Field(..., description="Problem title")
    instructions: str = Field(..., description="Problem prompt and student instructions")
    visual_schema: list[VisualElementSchema] = Field(
        default_factory=list, description="Graphical primitives for SVG component rendering"
    )
    answer_schema: list[AnswerFieldSpec] = Field(
        default_factory=list, description="List of expected student input fields"
    )


class AnswerSubmission(BaseModel):
    """Student submission payload."""

    answers: dict[str, Any] = Field(
        ..., description="Dictionary mapping field_id to submitted value"
    )


class FieldResult(BaseModel):
    """Evaluation result for a single student answer field."""

    is_correct: bool = Field(
        ..., description="Whether the field value is within acceptable tolerance"
    )
    submitted: Any = Field(default=None, description="Value submitted by student")
    delta: float | None = Field(default=None, description="Absolute error delta if numeric")
    message: str | None = Field(default=None, description="Optional feedback or hint message")


class GradingResult(BaseModel):
    """Overall grading outcome of a problem submission."""

    is_passed: bool = Field(..., description="True if all required fields are correct")
    score: float = Field(..., description="Fraction of correct fields (0.0 to 1.0)")
    field_results: dict[str, FieldResult] = Field(
        default_factory=dict, description="Detailed per-field evaluation breakdown"
    )


@runtime_checkable
class ProblemGeneratorProtocol(Protocol):
    """Unified interface required for any statics problem backend plugin."""

    @property
    def problem_type(self) -> str:
        """Unique problem domain identifier string."""
        ...

    def generate(self, seed: int, params: dict[str, Any] | None = None) -> ProblemDisplayData:
        """Synthesize problem geometry and display schema from seed. NEVER return solution data."""
        ...

    def solve(self, seed: int, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Server-side solver for ground-truth reactions or forces. Internal use only."""
        ...

    def check(
        self, seed: int, submission: AnswerSubmission, tolerance: float = 0.01
    ) -> GradingResult:
        """Statelessly regenerate ground truth and evaluate student submission."""
        ...
