"""Pure data quality rule evaluation and scoring (no I/O)."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import get_args

import pandas as pd

from app.schemas.domain import Province

RULE_TYPES = (
    "not_null", "unique", "range", "allowed_values", "regex", "date_not_future", "date_format",
    "referential_integrity",
)
DEFAULT_THRESHOLDS = {"excellent": 95.0, "good": 85.0, "needs_attention": 70.0}
PROVINCES = list(get_args(Province))
SAMPLE_LIMIT = 20


@dataclass
class RuleResult:
    evaluated: int
    failed: int
    status: str
    detail: str | None = None
    sample: list[int] = field(default_factory=list)

    @property
    def pass_rate(self) -> float | None:
        if self.evaluated <= 0:
            return None
        return round((self.evaluated - self.failed) / self.evaluated * 100, 2)


def status_for(pass_rate: float | None, warn: float, fail: float) -> str:
    if pass_rate is None:
        return "not_applicable"
    if pass_rate >= warn:
        return "pass"
    return "warning" if pass_rate >= fail else "fail"


def validate_params(rule_type: str, column: str | None, params: dict[str, object]) -> None:
    if rule_type not in RULE_TYPES:
        raise ValueError(f"Unsupported rule type: {rule_type}.")
    if not column:
        raise ValueError("A column is required.")
    if rule_type == "allowed_values" and not (
        params.get("values") or params.get("preset") == "provinces"
    ):
        raise ValueError("allowed_values needs 'values' or preset 'provinces'.")
    if rule_type == "regex":
        try:
            re.compile(str(params.get("pattern", "")))
        except re.error:
            raise ValueError("Invalid regular expression.") from None
        if not params.get("pattern"):
            raise ValueError("regex needs a 'pattern'.")
    if rule_type == "range" and params.get("min") is None and params.get("max") is None:
        raise ValueError("range needs 'min' and/or 'max'.")
    if rule_type == "referential_integrity" and not (
        params.get("reference_dataset") and params.get("reference_column")
    ):
        raise ValueError("referential_integrity needs 'reference_dataset' and 'reference_column'.")


def _result(frame: pd.DataFrame, failed_mask: pd.Series, applicable: pd.Series) -> RuleResult:
    failed = failed_mask & applicable
    rows = [int(index) + 1 for index in frame.index[failed][:SAMPLE_LIMIT]]
    return RuleResult(int(applicable.sum()), int(failed.sum()), "pending", sample=rows)


def evaluate_rule(
    frame: pd.DataFrame,
    rule_type: str,
    column: str,
    params: dict[str, object],
    reference: pd.Series | None = None,
    today: datetime | None = None,
) -> RuleResult:
    """Return failure counts. Record values are never included in results."""
    if column not in frame.columns:
        return RuleResult(0, 0, "not_applicable", f"Column '{column}' is not present.")
    series = frame[column]
    blank = series.isna() | (series.astype(str).str.strip() == "")
    everything = pd.Series(True, index=frame.index)
    present = ~blank
    if rule_type == "not_null":
        return _result(frame, blank, everything)
    if rule_type == "unique":
        duplicated = series.astype(str).duplicated(keep="first")
        return _result(frame, duplicated, present)
    if rule_type == "range":
        numbers = pd.to_numeric(series, errors="coerce")
        bad = numbers.isna()
        low, high = params.get("min"), params.get("max")
        if low is not None:
            bad |= numbers < float(low)
        if high is not None:
            bad |= numbers > float(high)
        return _result(frame, bad, present)
    if rule_type == "allowed_values":
        values = PROVINCES if params.get("preset") == "provinces" else list(params["values"])
        allowed = {str(value).casefold() for value in values}
        return _result(frame, ~series.astype(str).str.strip().str.casefold().isin(allowed), present)
    if rule_type == "regex":
        pattern = re.compile(str(params["pattern"]))
        bad = ~series.astype(str).map(lambda value: bool(pattern.fullmatch(value)))
        return _result(frame, bad, present)
    if rule_type in {"date_not_future", "date_format"}:
        dates = pd.to_datetime(series, errors="coerce", utc=True)
        bad = dates.isna()
        if rule_type == "date_not_future":
            limit = pd.Timestamp(today or datetime.now(UTC))
            bad |= dates > limit
        return _result(frame, bad, present)
    if rule_type == "referential_integrity":
        if reference is None:
            return RuleResult(0, 0, "not_applicable", "Reference dataset is unavailable.")
        known = set(reference.dropna().astype(str))
        return _result(frame, ~series.astype(str).isin(known), present)
    raise ValueError(f"Unsupported rule type: {rule_type}.")


def classify(score: float | None, thresholds: dict[str, float] | None = None) -> str:
    limits = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    if score is None:
        return "Insufficient data"
    if score >= limits["excellent"]:
        return "Excellent"
    if score >= limits["good"]:
        return "Good"
    if score >= limits["needs_attention"]:
        return "Needs Attention"
    return "Poor"


def aggregate(rows: list[tuple[int, int, str]]) -> dict[str, object]:
    """Aggregate (evaluated, failed, status) tuples into score metrics.

    score = passed record-checks / evaluated record-checks * 100 (None if none evaluated).
    rule_pass_rate = rules with status pass / rules that were applicable.
    """
    evaluated = sum(item[0] for item in rows)
    failed = sum(item[1] for item in rows)
    applicable = [item for item in rows if item[2] not in {"not_applicable", "error"}]
    score = round((evaluated - failed) / evaluated * 100, 2) if evaluated else None
    rule_pass = (
        round(sum(1 for item in applicable if item[2] == "pass") / len(applicable) * 100, 2)
        if applicable
        else None
    )
    return {
        "score": score,
        "records_evaluated": evaluated,
        "records_failed": failed,
        "rules_total": len(rows),
        "rules_applicable": len(applicable),
        "rules_failing": sum(1 for item in applicable if item[2] == "fail"),
        "rules_warning": sum(1 for item in applicable if item[2] == "warning"),
        "rule_pass_rate": rule_pass,
    }
