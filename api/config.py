"""Validate engineering tuning against the reviewed policy budget ceiling."""

from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

PositiveBudget = Annotated[int, Field(strict=True, gt=0)]
Confidence = Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]


class AlignmentLimits(BaseModel):
    model_config = ConfigDict(extra="ignore")
    word_budget_ceiling: PositiveBudget


class PolicyMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")
    policy_version: str = Field(min_length=1)
    approved_by: str = Field(min_length=1)
    alignment: AlignmentLimits


class TuningMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tuning_version: str = Field(min_length=1)
    card_confidence_min: Confidence
    level_confidence_min: Confidence
    alignment_confidence_min: Confidence
    retrieval_score_floor: float = Field(ge=0, allow_inf_nan=False)
    retrieval_overlap_floor: Confidence
    retrieval_overlap_min_terms: PositiveBudget
    word_budget_table: dict[str, PositiveBudget]
    trigger_b_min_window_tokens: PositiveBudget

    @model_validator(mode="after")
    def ordered_budgets(self):
        table = self.word_budget_table
        bounds = [key for key in table if key != "else"]
        if "else" not in table or not bounds:
            raise ValueError("word_budget_table requires finite bands and an else band")
        if any(not key.isascii() or not key.isdigit() or int(key) < 1 for key in bounds):
            raise ValueError("word_budget_table bounds must be positive integer strings")
        if len({int(key) for key in bounds}) != len(bounds):
            raise ValueError("word_budget_table has duplicate numeric bounds")
        budgets = [table[key] for key in sorted(bounds, key=int)] + [table["else"]]
        if budgets != sorted(budgets):
            raise ValueError("word_budget_table budgets must not decrease with token length")
        return self


def _load(path: Path, model):
    try:
        return model.model_validate(yaml.safe_load(path.read_text("utf-8")))
    except ValidationError as exc:
        fields = ", ".join(".".join(map(str, error["loc"])) or "root" for error in exc.errors())
        raise RuntimeError(f"Config missing or invalid at {path}: fields {fields}") from exc
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise RuntimeError(f"Config missing or invalid at {path}: {type(exc).__name__}") from exc


def load_config(policy_path: Path, tuning_path: Path) -> tuple[PolicyMetadata, TuningMetadata]:
    policy = _load(policy_path, PolicyMetadata)
    tuning = _load(tuning_path, TuningMetadata)
    bands = sorted((key for key in tuning.word_budget_table if key != "else"), key=int)
    for band in [*bands, "else"]:
        budget = tuning.word_budget_table[band]
        if budget > policy.alignment.word_budget_ceiling:
            raise RuntimeError(
                f"{tuning_path}: word_budget_table.{band} exceeds word_budget_ceiling"
            )
    return policy, tuning
