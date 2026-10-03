"""Match OCR text to known names, rejecting ambiguous or distant matches."""
import re
from functools import lru_cache
from rapidfuzz.distance import Levenshtein
from utils.scan_integrity import ScanIntegrityError


def normalize_text(text):
    return re.sub(r'\s+', ' ', str(text).replace('’', "'")).strip().casefold()


@lru_cache(maxsize=16)
def _vocabulary(choices):
    pairs = tuple((normalize_text(choice), str(choice)) for choice in choices)
    exact = {}
    for normalized, original in pairs:
        exact.setdefault(normalized, []).append(original)
    return pairs, exact


def validated_match(text, choices, field):
    raw = normalize_text(text)
    if field == 'main stat':
        raw = raw.strip(" '\"")
    if not raw:
        raise ScanIntegrityError(f'Unreadable {field}; incomplete scan, no export.')
    pairs, exact = _vocabulary(tuple(choices))
    if raw in exact and len(exact[raw]) == 1:
        return exact[raw][0]
    ranked = sorted((Levenshtein.distance(raw, normalized), original) for normalized, original in pairs)
    if not ranked:
        raise ScanIntegrityError(f'No recognition vocabulary for {field}; incomplete scan, no export.')
    best, result = ranked[0]
    allowance = min(2, len(raw) // 12) if field == 'relic name' else (1 if len(raw) >= 7 else 0)
    margin = ranked[1][0] - best if len(ranked) > 1 else 99
    if best > allowance or (best and margin < 2) or (len(ranked)>1 and margin == 0):
        raise ScanIntegrityError(f'Uncertain {field} {text!r}: nearest={result!r}, edits={best}, margin={margin}; incomplete scan, no export.')
    return result


_BASE = {'HP', 'ATK', 'DEF'}
MAIN_STATS_BY_SLOT = {
    'Head': {'HP'}, 'Hands': {'ATK'},
    'Body': _BASE | {'CRIT Rate', 'CRIT DMG', 'Effect Hit Rate', 'Outgoing Healing Boost'},
    'Feet': _BASE | {'SPD'},
    'Link Rope': _BASE | {'Break Effect', 'Energy Regeneration Rate'},
    'Planar Sphere': _BASE | {f'{element} DMG Boost' for element in ('Physical', 'Fire', 'Ice', 'Lightning', 'Wind', 'Quantum', 'Imaginary')},
}


def validate_main_stat_slot(main_stat, slot):
    if main_stat not in MAIN_STATS_BY_SLOT.get(slot, set()):
        raise ScanIntegrityError(f'Impossible main stat {main_stat!r} for slot {slot!r}; incomplete scan, no export.')
