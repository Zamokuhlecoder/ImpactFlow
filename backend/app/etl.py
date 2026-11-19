import json
import math
import re
from collections.abc import Mapping
from typing import TypedDict, cast

import pandas as pd
from pydantic import ValidationError

from app.phase3_ingestion import ParticipationInput, SchemaType
from app.schemas.domain import ProgrammeInput, Province

PROVINCES: tuple[str, ...] = Province.__args__
_PROVINCE_BY_KEY = {province.casefold(): province for province in PROVINCES}
_INTEGER_FIELDS = {"age", "target_beneficiaries", "reached_beneficiaries"}


class QualityReport(TypedDict):
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    missing_values: int
    quality_percentage: float


class TransformationResult(TypedDict):
    silver: list[dict[str, object]]
    quarantine: list[dict[str, object]]
    gold: dict[str, list[dict[str, object]]]
    quality_report: QualityReport
    records_rejected: int
    quality_score: float


def _column_name(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("The dataset must have named columns.")
    return re.sub(r"[\s-]+", "_", value.strip().casefold())


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    missing = pd.isna(value)
    if getattr(missing, "ndim", 0) > 0:
        return False
    return bool(missing)


def _clean_record(record: Mapping[str, object]) -> tuple[dict[str, object], list[str]]:
    clean: dict[str, object] = {}
    errors: list[str] = []
    for key, value in record.items():
        if _is_missing(value):
            clean[key] = None
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                clean[key] = None
                continue
        if key == "province":
            province = _PROVINCE_BY_KEY.get(str(value).casefold())
            if province is None:
                errors.append("province")
            else:
                value = province
        elif key in {"name", "programme", "category"} and isinstance(value, str):
            value = value.title()
        elif key == "beneficiary_id":
            value = str(value).upper()
        elif key == "status":
            value = str(value).casefold()
        elif key in _INTEGER_FIELDS:
            number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
            if (
                pd.isna(number)
                or not math.isfinite(float(number))
                or not float(number).is_integer()
            ):
                errors.append(key)
            elif key == "age" and not 0 <= int(number) <= 120:
                errors.append(key)
            elif key != "age" and int(number) < 0:
                errors.append(key)
            else:
                value = int(number)
        elif key == "date" or key.endswith("_date"):
            parsed = pd.to_datetime(value, errors="coerce", format="mixed")
            if pd.isna(parsed):
                errors.append(key)
            else:
                value = parsed.date().isoformat()
        clean[key] = value
    return clean, errors


def _validate_record(
    record: dict[str, object],
    schema_type: SchemaType,
    conversion_errors: list[str],
    known_programmes: set[str] | None,
) -> tuple[dict[str, object] | None, list[str]]:
    errors = list(conversion_errors)
    if schema_type == "aggregate":
        try:
            validated = ProgrammeInput.model_validate(record).model_dump()
        except ValidationError as error:
            errors.extend(
                str(item["loc"][0]) for item in error.errors() if item["loc"]
            )
        else:
            return validated, []
    elif schema_type == "participation":
        if (
            known_programmes is not None
            and record.get("programme") is not None
            and str(record["programme"]).casefold() not in known_programmes
        ):
            errors.append("programme")
        try:
            validated = ParticipationInput.model_validate(record).model_dump(mode="json")
        except ValidationError as error:
            errors.extend(
                str(item["loc"][0]) for item in error.errors() if item["loc"]
            )
        else:
            return (None, sorted(set(errors))) if errors else (validated, [])
    else:
        if not any(value is not None for value in record.values()):
            errors.append("empty_record")
        for field in ("name", "programme", "category"):
            if field in record and record[field] is None:
                errors.append(field)
        if "province" in record and record["province"] is None:
            errors.append("province")
        if "age" in record and record["age"] is None:
            errors.append("age")
        if errors:
            return None, sorted(set(errors))
        return record, []
    return None, sorted(set(errors))


def _gold_datasets(records: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    frame = pd.DataFrame(records)
    participant_count = (
        frame["beneficiary_id"].nunique()
        if "beneficiary_id" in frame
        else len(frame)
    )
    distinct_programmes = (
        int(frame["programme"].nunique())
        if "programme" in frame
        else int(frame["name"].nunique())
        if "name" in frame
        else 0
    )
    beneficiary_summary = [{
        "participation_records": len(frame),
        "unique_beneficiaries": int(participant_count),
        "distinct_programmes": distinct_programmes,
    }]

    programme_column = "programme" if "programme" in frame else "name" if "name" in frame else None
    programme_performance: list[dict[str, object]] = []
    if programme_column:
        for name, group in frame.groupby(programme_column, dropna=False, sort=True):
            item: dict[str, object] = {
                "programme": str(name),
                "records": int(len(group)),
                "participants": int(
                    group["beneficiary_id"].nunique()
                    if "beneficiary_id" in group
                    else len(group)
                ),
            }
            if "target_beneficiaries" in group:
                item["target_beneficiaries"] = int(group["target_beneficiaries"].sum())
            if "reached_beneficiaries" in group:
                item["reached_beneficiaries"] = int(group["reached_beneficiaries"].sum())
            if item.get("target_beneficiaries", 0):
                item["target_achievement_pct"] = round(
                    int(item.get("reached_beneficiaries", 0))
                    / int(item["target_beneficiaries"])
                    * 100,
                    2,
                )
            programme_performance.append(item)

    provincial_performance: list[dict[str, object]] = []
    if "province" in frame:
        for province, group in frame.groupby("province", dropna=False, sort=True):
            provincial_performance.append({
                "province": str(province),
                "records": int(len(group)),
                "participants": int(
                    group["beneficiary_id"].nunique()
                    if "beneficiary_id" in group
                    else len(group)
                ),
            })
    return {
        "beneficiary_summary": beneficiary_summary,
        "programme_performance": programme_performance,
        "provincial_performance": provincial_performance,
    }


def transform_records(
    rows: list[dict[str, object]],
    schema_type: SchemaType,
    known_programmes: set[str] | None = None,
) -> TransformationResult:
    if not rows:
        raise ValueError("The dataset has no data rows.")
    frame = pd.DataFrame(rows)
    normalized_columns = [_column_name(column) for column in frame.columns]
    if len(normalized_columns) != len(set(normalized_columns)):
        raise ValueError("The dataset contains duplicate columns after standardization.")
    frame.columns = normalized_columns
    frame = frame.replace(to_replace=r"(?i)^\s*(?:null|none|n/?a|nan)\s*$", value=None, regex=True)
    frame = frame.apply(lambda column: column.map(
        lambda value: value.strip() if isinstance(value, str) and value.strip() else (
            None if isinstance(value, str) else value
        )
    ))
    missing_values = int(frame.isna().sum().sum())
    silver: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    seen: set[str] = set()
    invalid_count = 0
    duplicate_count = 0

    for record_number, raw_record in enumerate(frame.to_dict(orient="records"), start=1):
        record, conversion_errors = _clean_record(cast(Mapping[str, object], raw_record))
        clean, errors = _validate_record(
            record, schema_type, conversion_errors, known_programmes
        )
        if errors:
            invalid_count += 1
            rejected.append({
                "record_number": record_number,
                "record": record,
                "errors": errors,
            })
            continue
        canonical = json.dumps(clean, sort_keys=True, ensure_ascii=False, allow_nan=False)
        if canonical in seen:
            duplicate_count += 1
            rejected.append({
                "record_number": record_number,
                "record": clean,
                "errors": ["duplicate_record"],
            })
            continue
        seen.add(canonical)
        silver.append(cast(dict[str, object], clean))

    total_records = len(rows)
    quality_score = round(len(silver) / total_records * 100, 2)
    report: QualityReport = {
        "total_records": total_records,
        "valid_records": len(silver),
        "invalid_records": invalid_count,
        "duplicate_records": duplicate_count,
        "missing_values": missing_values,
        "quality_percentage": quality_score,
    }
    return {
        "silver": silver,
        "quarantine": rejected,
        "gold": _gold_datasets(silver) if silver else {
            "beneficiary_summary": [],
            "programme_performance": [],
            "provincial_performance": [],
        },
        "quality_report": report,
        "records_rejected": invalid_count + duplicate_count,
        "quality_score": quality_score,
    }
