"""setting clause -> static check of the effective configuration (L4).

key: publishing.review_max_age_days
type: integer | number | boolean | string | list
min / max          numeric bounds
value              the exact value this request requires
contains           items a list must contain
forbid             items a list must not contain
"""

from ..model import ClauseResult

_TYPES = {"integer": int, "number": (int, float), "boolean": bool, "string": str, "list": list}


def check(clause, ctx) -> ClauseResult:
    key = clause["key"]
    value = ctx.config(key, default=None)
    problems = []
    if value is None:
        problems.append(f"{key} is not set")
    else:
        want = clause.get("type")
        if want and (not isinstance(value, _TYPES[want]) or (want != "boolean" and isinstance(value, bool))):
            problems.append(f"{key} = {value!r} is not a {want}")
        if "min" in clause.data and isinstance(value, (int, float)) and value < clause["min"]:
            problems.append(f"{key} = {value} is below the minimum {clause['min']}")
        if "max" in clause.data and isinstance(value, (int, float)) and value > clause["max"]:
            problems.append(f"{key} = {value} is above the maximum {clause['max']}")
        if "value" in clause.data and value != clause["value"]:
            problems.append(f"{key} = {value!r}, this request requires {clause['value']!r}")
        if "contains" in clause.data:
            missing = [x for x in clause["contains"] if x not in (value or [])]
            if missing:
                problems.append(f"{key} must contain {missing}")
        if "forbid" in clause.data:
            present = [x for x in clause["forbid"] if x in (value or [])]
            if present:
                problems.append(f"{key} must not contain {present}")
    return ClauseResult(
        clause.id,
        "setting",
        "L4",
        "fail" if problems else "pass",
        f"{key} = {value!r}" + ("" if not problems else "; " + "; ".join(problems)),
        problems,
    )
