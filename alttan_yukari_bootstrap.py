#!/usr/bin/env python3
"""Pinned validation-only project-cluster bootstrap for bottom-up lexical diagnostics."""

import argparse
import hashlib
import json
import math
import random
import re
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

KOK = Path(__file__).resolve().parent
VALIDATION_ROWS = 300
DEFAULT_REPLICATES = 2000
DEFAULT_SEED = 42
METRIC = "macro_token_recall"
COMPARISONS = (
    ("gold_minus_anonymised_macro_token_recall", "gold", "anonymised"),
    ("v5_predicted_minus_anonymised_macro_token_recall", "v5_predicted", "anonymised"),
)
MODES = ("anonymised", "gold", "v5_predicted")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_object(path: Path, label: str) -> Dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError(label + " manifest or summary is missing or invalid") from None
    if not isinstance(value, dict):
        raise ValueError(label + " must be a JSON object")
    return value


def _hash(value: object, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(label + " is not a SHA-256 digest")
    return value


def expected_validation_hashes(root: Optional[Path] = None) -> Dict[str, str]:
    root = root or KOK
    v6 = _json_object(root / "lora" / "v6_girdi_manifest.json", "v6")
    audit = _json_object(root / "rapor" / "arastirma" / "dogrulama_manifest.json", "validation")
    try:
        hashes = {
            "prompts": v6["beklenen_sha256"]["valid_v6"],
            "raw": audit["tam_dogrulama_sha256"],
            "predictions": audit["dondurulmus_tahminler"]["v5"],
        }
    except (KeyError, TypeError):
        raise ValueError("repository manifests do not pin all validation inputs") from None
    return {name: _hash(value, name) for name, value in hashes.items()}


def _validate_provenance(summary: Mapping[str, object], expected: Mapping[str, str]) -> Dict[str, str]:
    provenance = summary.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("summary has no input provenance")
    prompts_hash = provenance.get("prompts_sha256")
    predictions_hash = provenance.get("predictions_sha256")
    raw_hashes = provenance.get("raw_sha256")
    if prompts_hash != expected["prompts"]:
        raise ValueError("summary prompts are not the pinned v6 validation input")
    if predictions_hash != expected["predictions"]:
        raise ValueError("summary predictions are not the pinned v5 validation input")
    if not isinstance(raw_hashes, dict) or len(raw_hashes) != 1:
        raise ValueError("summary must identify exactly one complete raw validation file")
    if next(iter(raw_hashes.values())) != expected["raw"]:
        raise ValueError("summary raw data is not the pinned v4 validation input")
    return {
        "prompts_sha256": expected["prompts"],
        "raw_sha256": expected["raw"],
        "predictions_sha256": expected["predictions"],
    }


def _finite_ratio(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + " must be a finite number")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(label + " must be between 0 and 1")
    return result


def project_values(summary: Mapping[str, object]) -> Tuple[Dict[str, Dict[str, float]], int]:
    modes = summary.get("modes")
    projects = summary.get("projects")
    if not isinstance(modes, dict) or not isinstance(projects, dict):
        raise ValueError("summary must contain modes and per-project aggregates")

    project_sets = []
    for mode in MODES:
        mode_projects = projects.get(mode)
        mode_summary = modes.get(mode)
        if not isinstance(mode_projects, dict) or not isinstance(mode_summary, dict):
            raise ValueError("summary is missing a required mode: " + mode)
        if mode_summary.get("rows") != VALIDATION_ROWS:
            raise ValueError("mode row count is not the fixed 300-row validation cohort")
        project_sets.append(set(mode_projects))

    if not project_sets[0] or any(project_set != project_sets[0] for project_set in project_sets[1:]):
        raise ValueError("project sets differ between paired modes")
    if len(project_sets[0]) < 2:
        raise ValueError("at least two project clusters are required")

    values: Dict[str, Dict[str, float]] = {}
    total_rows = 0
    for project in sorted(project_sets[0]):
        if not isinstance(project, str) or not project:
            raise ValueError("invalid project key in aggregate summary")
        cluster: Dict[str, float] = {}
        row_count = None
        for mode in MODES:
            metrics = projects[mode][project]
            if not isinstance(metrics, dict):
                raise ValueError("invalid per-project aggregate")
            rows = metrics.get("rows")
            if isinstance(rows, bool) or not isinstance(rows, int) or rows <= 0:
                raise ValueError("per-project row count must be a positive integer")
            if row_count is None:
                row_count = rows
            elif row_count != rows:
                raise ValueError("per-project row counts differ between paired modes")
            cluster[mode] = _finite_ratio(metrics.get(METRIC), mode + "." + METRIC)
        cluster["rows"] = float(row_count)
        values[project] = cluster
        total_rows += row_count

    if total_rows != VALIDATION_ROWS:
        raise ValueError("per-project aggregates do not sum to the fixed validation cohort")
    if summary.get("prediction_rows") != VALIDATION_ROWS:
        raise ValueError("prediction row count is not the fixed 300-row validation cohort")
    return values, total_rows


def _quantile(sorted_values: List[float], probability: float) -> float:
    position = (len(sorted_values) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def paired_project_bootstrap(
    values: Mapping[str, Mapping[str, float]], replicates: int = DEFAULT_REPLICATES, seed: int = DEFAULT_SEED
) -> Dict[str, Dict[str, object]]:
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates < 100:
        raise ValueError("bootstrap replicates must be an integer >= 100")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("bootstrap seed must be an integer")
    projects = sorted(values)
    if len(projects) < 2:
        raise ValueError("at least two project clusters are required")

    total_rows = sum(int(values[project]["rows"]) for project in projects)
    estimates = {}
    samples = {name: [] for name, _, _ in COMPARISONS}
    for name, left, right in COMPARISONS:
        estimates[name] = sum(
            int(values[project]["rows"]) * (values[project][left] - values[project][right])
            for project in projects
        ) / total_rows

    rng = random.Random(seed)
    for _ in range(replicates):
        sampled = [rng.choice(projects) for _ in projects]
        denominator = sum(int(values[project]["rows"]) for project in sampled)
        for name, left, right in COMPARISONS:
            numerator = sum(
                int(values[project]["rows"]) * (values[project][left] - values[project][right])
                for project in sampled
            )
            samples[name].append(numerator / denominator)

    result = {}
    for name, _, _ in COMPARISONS:
        ordered = sorted(samples[name])
        result[name] = {
            "estimate": round(estimates[name], 9),
            "ci95": [round(_quantile(ordered, 0.025), 9), round(_quantile(ordered, 0.975), 9)],
            "n_projects": len(projects),
            "n_rows": total_rows,
        }
    return result


def build_report(
    summary_path: Path, summary: Mapping[str, object], replicates: int = DEFAULT_REPLICATES, seed: int = DEFAULT_SEED
) -> Dict[str, object]:
    expected = expected_validation_hashes()
    input_hashes = _validate_provenance(summary, expected)
    values, total_rows = project_values(summary)
    comparisons = paired_project_bootstrap(values, replicates=replicates, seed=seed)
    return {
        "schema": 1,
        "scope": "fixed validation-only valid300; no test/eval scoring",
        "interpretation": "Lexical information availability only; not model F1 or a causal naming gain.",
        "method": "paired project-cluster percentile bootstrap with linear-interpolated 95% intervals",
        "resampling_unit": "project",
        "weighting": "row-weighted macro token recall; all rows in each sampled project stay together",
        "replicates": replicates,
        "seed": seed,
        "confidence_level": 0.95,
        "n_projects": len(values),
        "n_rows": total_rows,
        "summary_sha256": sha256(summary_path),
        "validation_inputs": input_hashes,
        "comparisons": comparisons,
    }


def is_inside_repo(path: Path, root: Optional[Path] = None) -> bool:
    root = root or KOK
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, type=Path, help="aggregate output from alttan_yukari_sim.py")
    parser.add_argument("--output", required=True, type=Path, help="new aggregate JSON path outside the repository")
    parser.add_argument("--replicates", type=int, default=DEFAULT_REPLICATES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)

    try:
        if not args.summary.is_file():
            raise ValueError("summary must be one aggregate JSON file")
        if is_inside_repo(args.output):
            raise ValueError("aggregate output must be outside the repository")
        if args.output.exists():
            raise FileExistsError("output already exists; it will not be overwritten")
        summary = _json_object(args.summary, "summary")
        report = build_report(args.summary, summary, replicates=args.replicates, seed=args.seed)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
    except (OSError, ValueError) as error:
        parser.exit(2, "ERROR: " + str(error) + "\n")

    print(json.dumps(report, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
