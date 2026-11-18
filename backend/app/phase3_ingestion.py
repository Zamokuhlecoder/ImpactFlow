import csv
import json
import re
import struct
from datetime import date
from io import BytesIO, StringIO
from typing import Literal
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile, ZipFile

import xlrd
from openpyxl import load_workbook
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.ingestion import MAX_CSV_BYTES, MAX_CSV_ROWS, OPTIONAL_COLUMNS, REQUIRED_COLUMNS
from app.schemas.domain import ProgrammeInput, Province

SchemaType = Literal["aggregate", "participation"]
PARTICIPATION_COLUMNS = {"beneficiary_id", "programme", "province", "participation_date"}
MAX_EXPANDED_BYTES = 20 * 1024 * 1024


class ParticipationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    beneficiary_id: str = Field(pattern=r"^B[0-9]{3,8}$")
    programme: str = Field(min_length=1, max_length=120)
    province: Province
    participation_date: date


def _normalize_headers(headers: list[object]) -> list[str]:
    if not headers or any(not isinstance(header, str) or not header.strip() for header in headers):
        raise ValueError("The dataset must have named columns.")
    normalized = [
        re.sub(r"[\s-]+", "_", header.strip().lower())
        for header in headers
        if isinstance(header, str)
    ]
    if len(normalized) != len(set(normalized)):
        raise ValueError("The dataset contains duplicate columns.")
    return normalized


def _validate_rows(
    rows: list[dict[str, object]], schema_type: SchemaType
) -> list[dict[str, object]]:
    if not rows:
        raise ValueError("The dataset has no data rows.")
    if len(rows) > MAX_CSV_ROWS:
        raise ValueError(f"The dataset may contain at most {MAX_CSV_ROWS} rows.")
    required = REQUIRED_COLUMNS if schema_type == "aggregate" else PARTICIPATION_COLUMNS
    optional = OPTIONAL_COLUMNS if schema_type == "aggregate" else set()
    seen_names: set[str] = set()
    validated: list[dict[str, object]] = []
    for number, row in enumerate(rows, start=1):
        missing = required - row.keys()
        unknown = row.keys() - required - optional
        if missing or unknown:
            raise ValueError(f"Row {number} has missing or unsupported columns.")
        clean = {
            key: value.strip() if isinstance(value, str) else value for key, value in row.items()
        }
        if clean.get("status") in ("", None):
            clean.pop("status", None)
        try:
            if schema_type == "aggregate":
                programme = ProgrammeInput.model_validate(clean)
                name = programme.name.casefold()
                if name in seen_names:
                    raise ValueError(f"Row {number} duplicates a programme name.")
                seen_names.add(name)
                validated.append(programme.model_dump())
            else:
                validated.append(ParticipationInput.model_validate(clean).model_dump())
        except ValidationError as error:
            fields = sorted({str(item["loc"][0]) for item in error.errors() if item["loc"]})
            raise ValueError(f"Row {number} has invalid values for: {', '.join(fields)}.") from None
    return validated


def parse_dataset(
    content: bytes, file_type: Literal["csv", "xlsx", "xls", "json"], schema_type: SchemaType
) -> list[dict[str, object]]:
    if not content:
        raise ValueError("The file is empty.")
    if len(content) > MAX_CSV_BYTES:
        raise ValueError("The file exceeds the 2 MB limit.")
    rows: list[dict[str, object]] = []
    if file_type == "csv":
        try:
            reader = csv.DictReader(StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
            if not reader.fieldnames:
                raise ValueError("The CSV must include a header row.")
            headers = _normalize_headers(list(reader.fieldnames))
            reader.fieldnames = headers
            for row in reader:
                if None in row:
                    raise ValueError("A CSV row has more fields than its header.")
                rows.append(dict(row))
                if len(rows) > MAX_CSV_ROWS:
                    raise ValueError(f"The dataset may contain at most {MAX_CSV_ROWS} rows.")
        except UnicodeDecodeError:
            raise ValueError("The CSV must use UTF-8 encoding.") from None
        except csv.Error:
            raise ValueError("The CSV file is malformed.") from None
    elif file_type == "json":
        try:
            data = json.loads(content.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("The JSON file is malformed or not UTF-8.") from None
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise ValueError("JSON must contain an array of row objects.")
        for item in data:
            headers = _normalize_headers(list(item))
            rows.append(dict(zip(headers, item.values(), strict=True)))
    elif file_type == "xls":
        try:
            workbook = xlrd.open_workbook(file_contents=content, on_demand=True)
            try:
                if workbook.nsheets == 0:
                    raise ValueError("The spreadsheet has no worksheet.")
                sheet = workbook.sheet_by_index(0)
                if sheet.ncols > 32 or sheet.nrows > MAX_CSV_ROWS + 1:
                    raise ValueError("The spreadsheet exceeds the row or column limit.")
                headers = _normalize_headers(sheet.row_values(0) if sheet.nrows else [])
                for row_index in range(1, sheet.nrows):
                    values: list[object] = []
                    for cell in sheet.row(row_index):
                        if cell.ctype == xlrd.XL_CELL_ERROR:
                            raise ValueError("The spreadsheet contains an error cell.")
                        if cell.ctype == xlrd.XL_CELL_DATE:
                            values.append(xlrd.xldate_as_datetime(cell.value, workbook.datemode))
                        else:
                            values.append(cell.value)
                    if all(value == "" for value in values):
                        continue
                    rows.append(dict(zip(headers, values, strict=True)))
            finally:
                workbook.release_resources()
        except (xlrd.XLRDError, OSError, EOFError, IndexError, struct.error, OverflowError):
            raise ValueError("The Excel file is invalid.") from None
    else:
        try:
            with ZipFile(BytesIO(content)) as archive:
                if sum(item.file_size for item in archive.infolist()) > MAX_EXPANDED_BYTES:
                    raise ValueError("The expanded spreadsheet exceeds the size limit.")
            workbook = load_workbook(BytesIO(content), read_only=True, data_only=False)
            try:
                sheet = workbook.active
                if sheet is None:
                    raise ValueError("The spreadsheet has no worksheet.")
                if (sheet.max_column or 0) > 32 or (sheet.max_row or 0) > MAX_CSV_ROWS + 1:
                    raise ValueError("The spreadsheet exceeds the row or column limit.")
                iterator = sheet.iter_rows()
                header_row = next(iterator, ())
                headers = _normalize_headers([cell.value for cell in header_row])
                for cells in iterator:
                    if any(cell.data_type == "f" for cell in cells):
                        raise ValueError("Spreadsheet formulas are not supported.")
                    if all(cell.value is None for cell in cells):
                        continue
                    rows.append(dict(zip(headers, (cell.value for cell in cells), strict=True)))
                    if len(rows) > MAX_CSV_ROWS:
                        raise ValueError(f"The dataset may contain at most {MAX_CSV_ROWS} rows.")
            finally:
                workbook.close()
        except (BadZipFile, KeyError, OSError, ParseError, EOFError, IndexError, TypeError):
            raise ValueError("The Excel file is invalid.") from None
    return _validate_rows(rows, schema_type)
