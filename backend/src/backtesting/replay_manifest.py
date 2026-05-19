import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

def parse_tz_aware(dt_str: Optional[str]) -> datetime:
    """
    Parses an ISO 8601 timestamp and strictly enforces timezone awareness.
    Raises ValueError if the string is empty, malformed, or naive.
    """
    if not dt_str:
        raise ValueError("Timestamp string is empty or None")
    
    # Normalize 'Z' suffix to '+00:00' for complete ISO parsing compatibility
    s = dt_str.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
        
    try:
        dt = datetime.fromisoformat(s)
    except Exception as e:
        raise ValueError(f"Failed to parse timestamp '{dt_str}': {e}")
        
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"Timestamp '{dt_str}' is naive / lacks timezone offset")
        
    return dt


def build_replay_manifest(
    decision_time_utc: str,
    artifacts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Constructs a deterministic point-in-time replay manifest from a simulated
    decision time and a list of candidate artifacts. Evaluates eligibility 
    of each artifact and logs any lookahead errors or warnings.
    
    Required artifact dict keys:
        artifact_type: str
        path: str
        embedded_timestamp_utc: Optional[str]
        as_of_time_utc: Optional[str]
        source: str
        required_for_decision: bool
    """
    lookahead_errors: List[str] = []
    warnings: List[str] = []
    eligible_artifacts: List[Dict[str, Any]] = []
    excluded_artifacts: List[Dict[str, Any]] = []

    # 1. Parse simulated decision time (must be timezone-aware)
    try:
        decision_time = parse_tz_aware(decision_time_utc)
    except Exception as e:
        decision_time = None
        lookahead_errors.append(f"Invalid simulated decision_time_utc '{decision_time_utc}': {e}")

    # 2. Evaluate eligibility of each candidate artifact
    for art in artifacts:
        # Copy to avoid external mutation
        art_copy = dict(art)
        art_type = art_copy.get("artifact_type")
        path = art_copy.get("path")
        required = bool(art_copy.get("required_for_decision", False))

        embedded_ts_str = art_copy.get("embedded_timestamp_utc")
        as_of_ts_str = art_copy.get("as_of_time_utc")
        
        effective_ts_str = embedded_ts_str or as_of_ts_str

        # Rule 6: Missing timestamps on required artifacts must create a lookahead error
        if not effective_ts_str:
            if required:
                lookahead_errors.append(
                    f"Required artifact '{path}' of type '{art_type}' is missing both "
                    "embedded_timestamp_utc and as_of_time_utc."
                )
            else:
                warnings.append(
                    f"Artifact '{path}' of type '{art_type}' lacks eligibility timestamps and is excluded."
                )
            art_copy["exclusion_reason"] = "missing_timestamp"
            excluded_artifacts.append(art_copy)
            continue

        # Rule 2 / 6: Verify artifact timestamp parsing & timezone-awareness
        try:
            art_ts = parse_tz_aware(effective_ts_str)
        except Exception as e:
            if required:
                lookahead_errors.append(
                    f"Required artifact '{path}' has naive or unparseable timestamp '{effective_ts_str}': {e}"
                )
            else:
                warnings.append(
                    f"Artifact '{path}' has naive or unparseable timestamp '{effective_ts_str}': {e}"
                )
            art_copy["exclusion_reason"] = f"invalid_timestamp: {e}"
            excluded_artifacts.append(art_copy)
            continue

        # If decision time is not parsed, we cannot verify eligibility; exclude to fail-closed
        if decision_time is None:
            art_copy["exclusion_reason"] = "decision_time_parse_failed"
            excluded_artifacts.append(art_copy)
            continue

        is_eligible = True
        exclusion_reason = None

        # Rule 4: Artifact timestamps after decision_time_utc must be excluded
        if art_ts > decision_time:
            is_eligible = False
            exclusion_reason = "future_artifact_excluded"
            # Rule 5: Required artifacts after decision time must raise lookahead error
            if required:
                lookahead_errors.append(
                    f"Required artifact '{path}' has timestamp '{effective_ts_str}' which is in the future "
                    f"relative to decision time '{decision_time_utc}'."
                )
            else:
                warnings.append(
                    f"Artifact '{path}' has timestamp '{effective_ts_str}' which is in the future "
                    f"relative to decision time '{decision_time_utc}'."
                )

        # Rule 7: Settlement, CLI-final, or corrected reports must not be eligible before settlement_as_of_time
        is_settlement = art_type and art_type.lower() in (
            "settlement", "cli_final", "corrected_report", "settlement_snapshot", "settlement_data"
        )
        if is_eligible and is_settlement:
            # Check availability time (settlement_as_of_time)
            settlement_as_of_str = art_copy.get("settlement_as_of_time_utc") or as_of_ts_str or embedded_ts_str
            if settlement_as_of_str:
                try:
                    settlement_as_of = parse_tz_aware(settlement_as_of_str)
                    # Rule 8: Settlement artifact before settlement_as_of_time is excluded/flagged
                    if decision_time < settlement_as_of:
                        is_eligible = False
                        exclusion_reason = "settlement_before_availability_time"
                        if required:
                            lookahead_errors.append(
                                f"Required settlement artifact '{path}' is not available at decision time "
                                f"'{decision_time_utc}' (available at '{settlement_as_of_str}')."
                            )
                        else:
                            warnings.append(
                                f"Settlement artifact '{path}' is not available at decision time "
                                f"'{decision_time_utc}' (available at '{settlement_as_of_str}')."
                            )
                except Exception as e:
                    is_eligible = False
                    exclusion_reason = f"invalid_settlement_as_of_timestamp: {e}"
                    if required:
                        lookahead_errors.append(
                            f"Required settlement artifact '{path}' has invalid availability timestamp '{settlement_as_of_str}': {e}"
                        )
            else:
                if required:
                    is_eligible = False
                    exclusion_reason = "missing_settlement_availability_timestamp"
                    lookahead_errors.append(
                        f"Required settlement artifact '{path}' is missing settlement availability timestamp."
                    )

        # Categorize
        if is_eligible:
            eligible_artifacts.append(art_copy)
        else:
            art_copy["exclusion_reason"] = exclusion_reason
            excluded_artifacts.append(art_copy)

    # 9. Ensure output is JSON-serializable
    manifest = {
        "decision_time_utc": decision_time_utc,
        "artifacts": artifacts,
        "eligible_artifacts": eligible_artifacts,
        "excluded_artifacts": excluded_artifacts,
        "lookahead_errors": lookahead_errors,
        "warnings": warnings,
        "schema_version": "1.0.0",
    }

    try:
        json.dumps(manifest)
    except Exception as e:
        manifest["lookahead_errors"].append(f"Manifest serialization failed: {e}")

    return manifest


def validate_replay_manifest(manifest: Dict[str, Any]) -> List[str]:
    """
    Validates a built replay manifest and checks for any schema violations,
    unparseable timestamps, lookahead errors, or filesystem metadata leaks.
    
    Fail-closed: if unsure or format is unexpected, returns error messages.
    """
    errors: List[str] = []

    # Schema check
    required_keys = [
        "decision_time_utc",
        "artifacts",
        "eligible_artifacts",
        "excluded_artifacts",
        "lookahead_errors",
        "warnings",
        "schema_version"
    ]
    for key in required_keys:
        if key not in manifest:
            errors.append(f"Schema violation: missing required top-level key '{key}'")

    if errors:
        return errors

    decision_time_utc = manifest["decision_time_utc"]

    # Verify decision_time_utc timezone awareness
    try:
        decision_time = parse_tz_aware(decision_time_utc)
    except Exception as e:
        errors.append(f"decision_time_utc: {e}")
        decision_time = None

    # Include pre-compiled lookahead errors
    errors.extend(manifest.get("lookahead_errors", []))

    # Defense-in-depth double check: verify eligible_artifacts contain no future leaks
    eligible_list = manifest.get("eligible_artifacts", [])
    for art in eligible_list:
        path = art.get("path")
        art_type = art.get("artifact_type")
        required = bool(art.get("required_for_decision", False))

        embedded_ts_str = art.get("embedded_timestamp_utc")
        as_of_ts_str = art.get("as_of_time_utc")
        effective_ts_str = embedded_ts_str or as_of_ts_str

        if not effective_ts_str:
            errors.append(f"Lookahead leak: Eligible artifact '{path}' lacks a timestamp.")
            continue

        try:
            art_ts = parse_tz_aware(effective_ts_str)
        except Exception as e:
            errors.append(f"Eligible artifact '{path}' has naive or invalid timestamp '{effective_ts_str}': {e}")
            continue

        if decision_time is not None and art_ts > decision_time:
            errors.append(
                f"Lookahead leak: Eligible artifact '{path}' has timestamp '{effective_ts_str}' "
                f"which is after simulated decision time '{decision_time_utc}'."
            )

        # Settlement check
        is_settlement = art_type and art_type.lower() in (
            "settlement", "cli_final", "corrected_report", "settlement_snapshot", "settlement_data"
        )
        if is_settlement:
            settlement_as_of_str = art.get("settlement_as_of_time_utc") or as_of_ts_str or embedded_ts_str
            if settlement_as_of_str:
                try:
                    settlement_as_of = parse_tz_aware(settlement_as_of_str)
                    if decision_time is not None and decision_time < settlement_as_of:
                        errors.append(
                            f"Lookahead leak: Eligible settlement artifact '{path}' is not available yet "
                            f"(available at '{settlement_as_of_str}', decision time is '{decision_time_utc}')."
                        )
                except Exception as e:
                    errors.append(f"Eligible settlement artifact '{path}' has invalid availability timestamp: {e}")
            else:
                errors.append(f"Eligible settlement artifact '{path}' is missing availability timestamp.")

    # Rule 3: Ensure filesystem metadata is not required or consulted (mtime keywords forbidden in artifacts)
    for art in manifest.get("artifacts", []):
        for key in art.keys():
            if "mtime" in key.lower() or "stat" in key.lower():
                errors.append(
                    f"Safety violation: Forbidden filesystem metadata key '{key}' "
                    f"detected in artifact '{art.get('path')}'. mtime reliance is prohibited."
                )

    return errors


def load_and_validate_manifest(manifest_path: str) -> Dict[str, Any]:
    """
    Utility helper to load a manifest JSON from disk and validate it.
    Returns a audit report dictionary.
    """
    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        errors = validate_replay_manifest(manifest)
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "summary": {
                "decision_time_utc": manifest.get("decision_time_utc"),
                "schema_version": manifest.get("schema_version"),
                "total_artifacts": len(manifest.get("artifacts", [])),
                "eligible_count": len(manifest.get("eligible_artifacts", [])),
                "excluded_count": len(manifest.get("excluded_artifacts", [])),
                "lookahead_errors_count": len(manifest.get("lookahead_errors", [])),
                "warnings_count": len(manifest.get("warnings", [])),
            }
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Failed to read/parse replay manifest file: {e}"],
            "summary": None
        }
