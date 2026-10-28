"""Bounded immutable inputs and provenance for descriptive experiment reports."""

from __future__ import annotations

import csv
import datetime as dt
import io
import math
import re
from dataclasses import dataclass

from scripts.text_snapshot import Snapshot as Snapshot

MAX_RESULTS_BYTES = 16 * 1024**2
MAX_NOTEBOOK_BYTES = 2 * 1024**2
MAX_ROWS = 10_000
MAX_EXCERPT_CHARS = 2_000
REQUIRED_COLUMNS = ("timestamp", "val_bpb", "throughput_Mvps", "num_params_M")
SCOPE = (
    "Descriptive recorded diagnostics. val_bpb is auxiliary validation 1-Dice, "
    "not the promotion objective. Promotion uses threshold-swept F1 gated by "
    "AP-prevalence-lift; those metrics are absent from the frozen results.tsv "
    "schema. Throughput is the recorded training-rate proxy. Rows may use "
    "different configurations and validation regimes, "
    "so these plots establish neither an optimization frontier nor a Pareto ranking."
)


@dataclass(frozen=True)
class Record:
    source_line: int
    timestamp: dt.datetime
    val_bpb: float
    throughput_Mvps: float
    num_params_M: float
    recorded_timestamp: str

    def as_dict(self):
        return {
            "source_line": self.source_line,
            "timestamp": self.timestamp.isoformat(sep=" "),
            "recorded_timestamp": self.recorded_timestamp,
            "val_bpb": self.val_bpb,
            "throughput_Mvps": self.throughput_Mvps,
            "num_params_M": self.num_params_M,
        }


@dataclass(frozen=True)
class Results:
    source: Snapshot
    columns: tuple[str, ...]
    records: tuple[Record, ...]
    time_basis: str
    source_row_count: int
    last_rows: int | None = None

    @property
    def selection_label(self):
        if self.last_rows is None:
            return f"All {self.source_row_count} source rows"
        return f"Last {len(self.records)} of {self.source_row_count} source rows"

    def manifest(self):
        return {
            "schema_version": 2,
            "scope": SCOPE,
            "results": self.source.provenance(),
            "columns": list(self.columns),
            "row_count": len(self.records),
            "source_row_count": self.source_row_count,
            "selection": {
                "kind": "all_rows" if self.last_rows is None else "last_source_rows",
                "requested_last_rows": self.last_rows,
                "source_line_numbers": sorted(row.source_line for row in self.records),
            },
            "time_basis": self.time_basis,
            "row_order": "timestamp ascending, stable source order for ties",
            "records": [row.as_dict() for row in self.records],
            "promotion_metrics": "not read; absent from the frozen results.tsv schema",
        }


def read_results(path, *, last_rows=None):
    if last_rows is not None and (type(last_rows) is not int or last_rows <= 0):
        raise ValueError("--last-rows must be a positive integer")
    source = Snapshot.read(path, MAX_RESULTS_BYTES)
    reader = csv.reader(io.StringIO(source.text()), delimiter="\t", strict=True)
    try:
        columns = next(reader)
    except StopIteration as exc:
        raise ValueError("results TSV is empty") from exc
    if len(set(columns)) != len(columns) or any(not name for name in columns):
        raise ValueError("results TSV has duplicate or empty column names")
    missing = set(REQUIRED_COLUMNS).difference(columns)
    if missing:
        raise ValueError(f"results TSV missing columns: {sorted(missing)}")
    records = []
    aware = set()
    for cells in reader:
        line = reader.line_num
        if len(records) >= MAX_ROWS:
            raise ValueError(f"results TSV exceeds {MAX_ROWS} rows")
        if len(cells) != len(columns):
            raise ValueError(f"results TSV line {line} has wrong column count")
        fields = dict(zip(columns, cells, strict=True))
        timestamp = fields["timestamp"]
        if not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?",
            timestamp,
        ):
            raise ValueError(f"invalid timestamp on line {line}: {timestamp!r}")
        try:
            parsed = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(dt.timezone.utc)
        except (ValueError, OverflowError) as exc:
            raise ValueError(f"invalid timestamp on line {line}") from exc
        aware.add(parsed.tzinfo is not None)
        values = []
        for name in REQUIRED_COLUMNS[1:]:
            try:
                value = float(fields[name])
            except ValueError as exc:
                raise ValueError(f"invalid {name} on line {line}") from exc
            if not math.isfinite(value) or value < 0:
                raise ValueError(
                    f"{name} must be finite and nonnegative on line {line}"
                )
            if name == "val_bpb" and value > 1:
                raise ValueError(f"val_bpb must be in [0, 1] on line {line}")
            if name == "num_params_M" and value == 0:
                raise ValueError(f"num_params_M must be positive on line {line}")
            values.append(value)
        loss, throughput, parameters = values
        records.append(Record(line, parsed, loss, throughput, parameters, timestamp))
    if not records:
        raise ValueError("results TSV has no data rows")
    if len(aware) > 1:
        raise ValueError("results TSV mixes timezone-aware and unqualified timestamps")
    source_row_count = len(records)
    if last_rows is not None:
        records = records[-last_rows:]
    records.sort(key=lambda row: row.timestamp)
    time_basis = (
        "UTC (normalized from recorded offsets)"
        if True in aware
        else "recorded local wall time (timezone not recorded)"
    )
    return Results(
        source, tuple(columns), tuple(records), time_basis, source_row_count, last_rows
    )


def read_notebook(path):
    source = Snapshot.read(path, MAX_NOTEBOOK_BYTES)
    lines = source.text().splitlines()
    entries = []
    for index, line in enumerate(lines):
        match = re.match(r"^## \[?(\d{4}-\d{2}-\d{2})(?:\]|\b)", line)
        if match:
            try:
                date = dt.date.fromisoformat(match[1])
            except ValueError as exc:
                raise ValueError(f"invalid notebook entry date: {line}") from exc
            entries.append((date, index))
    if not entries:
        raise ValueError("notebook has no dated level-two entries")
    date, start = max(entries)
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    section = "\n".join(lines[start:end]).strip()
    excerpt = section[:MAX_EXCERPT_CHARS]
    truncated = len(section) > len(excerpt)
    if truncated:
        excerpt += "\n[Excerpt truncated]"
    return source, {
        **source.provenance(),
        "entry_date": date.isoformat(),
        "entry_heading": lines[start],
        "excerpt": excerpt,
        "truncated": truncated,
        "scope": "Notebook intent and commentary, not measured experiment results",
    }
