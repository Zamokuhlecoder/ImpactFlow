import csv
from io import StringIO

from pydantic import ValidationError

from app.schemas.domain import ProgrammeInput

MAX_CSV_BYTES = 2 * 1024 * 1024
MAX_CSV_ROWS = 2_000
REQUIRED_COLUMNS = {
    "name",
    "category",
    "province",
    "target_beneficiaries",
    "reached_beneficiaries",
}
OPTIONAL_COLUMNS = {"status"}


def parse_programme_csv(content: bytes) -> list[dict[str, object]]:
    if not content:
        raise ValueError("The CSV file is empty.")
    if len(content) > MAX_CSV_BYTES:
        raise ValueError("The CSV file exceeds the 2 MB upload limit.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("The CSV file must use UTF-8 encoding.") from None

    try:
        reader = csv.DictReader(StringIO(text, newline=""), strict=True)
        if not reader.fieldnames:
            raise ValueError("The CSV file must include a header row.")
        headers = [header.strip() for header in reader.fieldnames]
        if len(headers) != len(set(headers)):
            raise ValueError("The CSV header contains duplicate columns.")
        missing = REQUIRED_COLUMNS - set(headers)
        unknown = set(headers) - REQUIRED_COLUMNS - OPTIONAL_COLUMNS
        if missing:
            raise ValueError(f"Required CSV columns are missing: {', '.join(sorted(missing))}.")
        if unknown:
            raise ValueError(f"Unsupported CSV columns: {', '.join(sorted(unknown))}.")
        reader.fieldnames = headers

        rows: list[dict[str, object]] = []
        seen_names: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            if row_number > MAX_CSV_ROWS + 1:
                raise ValueError(f"The CSV file may contain at most {MAX_CSV_ROWS} data rows.")
            if None in row:
                raise ValueError(f"CSV row {row_number} has more fields than the header.")
            cleaned = {key: (value or "").strip() for key, value in row.items()}
            if any(not value for key, value in cleaned.items() if key in REQUIRED_COLUMNS):
                raise ValueError(f"CSV row {row_number} is missing a required value.")
            if not cleaned.get("status"):
                cleaned.pop("status", None)
            try:
                programme = ProgrammeInput.model_validate(cleaned)
            except ValidationError as error:
                invalid_fields = sorted(
                    {str(detail["loc"][0]) for detail in error.errors() if detail["loc"]}
                )
                raise ValueError(
                    f"CSV row {row_number} has invalid values for: {', '.join(invalid_fields)}."
                ) from None
            canonical_name = programme.name.casefold()
            if canonical_name in seen_names:
                raise ValueError(f"CSV row {row_number} duplicates a programme name.")
            seen_names.add(canonical_name)
            rows.append(programme.model_dump())
    except csv.Error:
        raise ValueError("The CSV file is malformed.") from None

    if not rows:
        raise ValueError("The CSV file has no programme data rows.")
    return rows
