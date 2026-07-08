from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QuestionInput:
    question_id: str
    question: str
    db_id: str
    evidence: Optional[str] = None


@dataclass
class ColumnProfile:
    db_id: str
    table_name: str
    column_name: str
    data_type: str
    null_ratio: float
    distinct_count: int
    top_values: List[Any]
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    value_shape: Optional[str] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None


@dataclass
class ContextPackage:
    question_id: str
    db_id: str
    question: str
    intent: Dict[str, Any]
    literals: List[str]
    top_tables: List[Dict[str, Any]]
    top_columns: List[Dict[str, Any]]
    top_joins: List[Dict[str, Any]]
    matched_values: List[Dict[str, Any]]
    few_shot_examples: List[Dict[str, Any]]
    confidence: Dict[str, float]


@dataclass
class SQLCandidate:
    question_id: str
    db_id: str
    sql: str
    source: str
    prompt_id: Optional[str] = None
    generation_metadata: Dict[str, Any] = field(default_factory=dict)
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    repair_history: List[Dict[str, Any]] = field(default_factory=list)
