"""Compares findings between two scans of the same target using each
finding's stable `key` (not its title, which may embed dynamic values
like days-until-expiry) to tell genuinely new/resolved issues apart
from ones that just got reworded.
"""

from app.models.finding import Finding


def compute_diff(current: list[Finding], previous: list[Finding]) -> dict[str, list[Finding]]:
    previous_by_key = {f.key: f for f in previous}
    current_by_key = {f.key: f for f in current}

    new = [f for key, f in current_by_key.items() if key not in previous_by_key]
    resolved = [f for key, f in previous_by_key.items() if key not in current_by_key]
    persisting = [f for key, f in current_by_key.items() if key in previous_by_key]

    return {"new": new, "resolved": resolved, "persisting": persisting}
