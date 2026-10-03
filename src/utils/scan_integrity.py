import json

from models.const import RELIC_LOCATION


class ScanIntegrityError(RuntimeError):
    """Raised when parsed inventory records violate an in-game invariant."""


def validate_relic_records(relics: list[dict]) -> list[dict]:
    """Reject identical equipped records: one character can't wear two copies.

    Unequipped duplicates are legitimate and pass.
    """
    seen: dict[str, tuple[int, str]] = {}
    for index, relic in enumerate(relics):
        if not relic:
            raise ScanIntegrityError(f'Empty parsed relic at index {index}; incomplete scan, no export.')
        location = str(relic.get(RELIC_LOCATION, ""))
        if not location:
            continue

        payload = {key: value for key, value in relic.items() if key != "_uid"}
        key = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        uid = str(relic.get("_uid", f"index {index}"))
        if key in seen:
            previous_index, previous_uid = seen[key]
            raise ScanIntegrityError(
                "Relic scan integrity check failed: "
                f"{previous_uid} (index {previous_index}) and {uid} (index {index}) "
                f"are identical records equipped by character {location!r}. "
                "The scan is incomplete and will not be exported."
            )
        seen[key] = (index, uid)
    return relics
