"""Roll feasibility checks against the substat value tables."""
import math
from functools import lru_cache

from models.substat_vals import SUBSTAT_ROLL_VALS
from utils.scan_integrity import ScanIntegrityError


@lru_cache(maxsize=4096)
def _roll_counts(rarity, key, value):
    # Table scores are total roll quality; each roll is 0.8, 0.9 or 1.0. Rounded
    # SPD can map to several scores, so keep every possible count.
    table = SUBSTAT_ROLL_VALS[str(rarity)].get(key, {})
    text = str(float(value)) if key.endswith('_') else str(int(value))
    scores = table.get(text)
    if scores is None:
        return ()
    scores = scores if isinstance(scores, list) else [scores]
    counts = set()
    for score in scores:
        tenths = round(score * 10)
        counts.update(range(max(1, (tenths + 9) // 10), tenths // 8 + 1))
    return tuple(sorted(counts))


def validate_substat_rolls(active, preview, rarity, level, uid):
    """Reject substat values and roll counts that no roll allocation can produce.

    A misread that happens to be a feasible value still passes.
    """
    def fail(reason):
        raise ScanIntegrityError(
            f'Relic {uid}: invalid substat OCR: {reason}. '
            'The scan is incomplete and will not be exported.'
        )

    if type(rarity) is not int or str(rarity) not in SUBSTAT_ROLL_VALS:
        fail(f'unsupported rarity {rarity!r}')
    if type(level) is not int or not 0 <= level <= rarity * 3:
        fail(f'invalid level {level!r} for rarity {rarity}')
    upgrades = level // 3
    initial_min, initial_max = rarity - 2, rarity - 1
    if not min(4, initial_min + upgrades) <= len(active) <= min(4, initial_max + upgrades):
        fail(f'{len(active)} active stats incompatible with rarity {rarity}, level {level}')
    if len(preview) > 1 or (preview and len(active) >= 4):
        fail('preview stat cannot coexist with four active stats or another preview')
    seen = set()
    possible_totals = {0}
    for is_preview, stats in ((False, active), (True, preview)):
        for stat in stats:
            key, value = stat.get('key'), stat.get('value')
            if not isinstance(key, str) or key in seen:
                fail(f'duplicate or invalid stat key {key!r}')
            seen.add(key)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                fail(f'{key} has invalid value {value!r}')
            if not key.endswith('_') and value != int(value):
                fail(f'{key} has fractional displayed value {value!r}')
            counts = _roll_counts(rarity, key, value)
            if not counts:
                fail(f'{key}={value} is not a possible displayed roll value for rarity {rarity}')
            if is_preview:
                if 1 not in counts:
                    fail(f'preview {key}={value} must be one initial roll')
            else:
                possible_totals = {a + b for a in possible_totals for b in counts}
    feasible = {
        initial + upgrades for initial in range(initial_min, initial_max + 1)
        if min(4, initial + upgrades) == len(active)
    }
    if not possible_totals.intersection(feasible):
        fail(f'roll totals {sorted(possible_totals)} incompatible with level {level}; expected {sorted(feasible)}')
