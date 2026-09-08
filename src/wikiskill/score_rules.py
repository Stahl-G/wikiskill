"""Shared numeric rules; callers retain ownership of records and protocols."""
import math


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Score must be a finite number')
    return float(value)


def improvement(candidate, incumbent, direction='maximize'):
    if direction not in ('maximize', 'minimize'):
        raise ValueError('Direction must be maximize or minimize')
    return finite((finite(candidate) - finite(incumbent)) * (1 if direction == 'maximize' else -1))


def accepted(candidate, incumbent, direction='maximize', minimum=0.):
    threshold = finite(minimum)
    if threshold < 0:
        raise ValueError('Minimum improvement must be nonnegative')
    return improvement(candidate, incumbent, direction) > threshold
