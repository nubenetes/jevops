"""
Decision Model Primitives for JevOps.

System 1 Decision Models differ fundamentally from System 2 Generative LLMs:
- They do NOT produce free-form text or hallucinated code.
- They evaluate unstructured context (state) and return typed, schema-constrained judgments:
  1. Choice: Selects one option from a predefined list.
  2. Score: Numerical rating on a normalized scale [0.0, 1.0] or custom bounds.
  3. Noul: Boolean judgment (yes/no) with explicit probability.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class QuestionType(str, Enum):
    CHOICE = "choice"
    SCORE = "score"
    NOUL = "noul"


@dataclass
class ChoiceQuestion:
    id: str
    prompt: str
    options: List[str]
    default: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": QuestionType.CHOICE.value,
            "id": self.id,
            "prompt": self.prompt,
            "options": self.options,
            "default": self.default,
        }


@dataclass
class ScoreQuestion:
    id: str
    prompt: str
    min_value: float = 0.0
    max_value: float = 1.0
    default: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": QuestionType.SCORE.value,
            "id": self.id,
            "prompt": self.prompt,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "default": self.default,
        }


@dataclass
class NoulQuestion:
    id: str
    prompt: str
    default: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": QuestionType.NOUL.value,
            "id": self.id,
            "prompt": self.prompt,
            "default": self.default,
        }


DecisionQuestion = Union[ChoiceQuestion, ScoreQuestion, NoulQuestion]


@dataclass
class ChoiceResult:
    id: str
    selected: str
    confidence: float
    probabilities: Dict[str, float] = field(default_factory=dict)
    degraded: bool = False


@dataclass
class ScoreResult:
    id: str
    score: float
    confidence: float
    degraded: bool = False


@dataclass
class NoulResult:
    id: str
    value: bool
    probability: float
    confidence: float
    degraded: bool = False


DecisionResult = Union[ChoiceResult, ScoreResult, NoulResult]


@dataclass
class DecisionBatchRequest:
    context: Union[str, Dict[str, Any]]
    questions: List[DecisionQuestion]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context": self.context,
            "questions": [q.to_dict() for q in self.questions],
            "metadata": self.metadata,
        }


@dataclass
class DecisionBatchResponse:
    results: Dict[str, DecisionResult]
    latency_ms: float
    degraded: bool = False
    error: Optional[str] = None

    def get_choice(self, question_id: str) -> Optional[ChoiceResult]:
        res = self.results.get(question_id)
        return res if isinstance(res, ChoiceResult) else None

    def get_score(self, question_id: str) -> Optional[ScoreResult]:
        res = self.results.get(question_id)
        return res if isinstance(res, ScoreResult) else None

    def get_noul(self, question_id: str) -> Optional[NoulResult]:
        res = self.results.get(question_id)
        return res if isinstance(res, NoulResult) else None
