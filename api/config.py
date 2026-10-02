"""Load policy metadata and enforce the engineering threshold ceiling."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class AlignmentLimits(BaseModel):
    model_config = ConfigDict(extra="ignore")
    near_miss_max_ceiling: float = Field(ge=0, le=1, allow_inf_nan=False)


class PolicyMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")
    policy_version: str = Field(min_length=1)
    approved_by: str = Field(min_length=1)
    alignment: AlignmentLimits


class TuningMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tuning_version: str = Field(min_length=1)
    near_miss_max: float = Field(ge=0, le=1, allow_inf_nan=False)
    unmarked_near_miss_max: float = Field(ge=0, le=1, allow_inf_nan=False)


def load_config(policy_path: Path, tuning_path: Path) -> tuple[PolicyMetadata, TuningMetadata]:
    try:
        policy = PolicyMetadata.model_validate(yaml.safe_load(policy_path.read_text("utf-8")))
        tuning = TuningMetadata.model_validate(yaml.safe_load(tuning_path.read_text("utf-8")))
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError):
        raise RuntimeError(
            "Policy or tuning file missing or invalid; install reviewed P-08 files"
        ) from None
    for name in ("near_miss_max", "unmarked_near_miss_max"):
        if getattr(tuning, name) > policy.alignment.near_miss_max_ceiling:
            raise RuntimeError(f"{name} exceeds near_miss_max_ceiling")
    return policy, tuning
