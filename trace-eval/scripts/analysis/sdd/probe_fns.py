"""Small pure functions used to probe the fidelity of the Z3 translation in traceeval/spec/checks/contracts.py."""


def f_ifexp(a: int, b: int) -> int:
    return 1 if a == b + 1000003 else 0


def f_ifexp_bool(a: int, b: int) -> bool:
    return True if a == b + 1000003 else a < b


def f_truediv(n: int) -> bool:
    return n != 1000003 or n / 2 == 500001


def f_in(x: int) -> bool:
    return x in (1, 2)


def f_mod_neg(a: int) -> bool:
    return a % -3 <= 0


def f_floordiv(a: int) -> bool:
    return a // 2 * 2 <= a


def f_ne_ifexp(a: int, b: int) -> int:
    return 0 if a != b else 1


def f_gate_ignores_version(check_version: int, page_version: int, broken: int) -> bool:
    return broken == 0


def f_review_age_ok(age_days: int, max_age_days: int) -> bool:
    return 0 <= age_days <= max_age_days
