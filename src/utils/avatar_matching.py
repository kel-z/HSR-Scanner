"""Equipped-footer detection and portrait matching."""
import cv2
import numpy as np
from utils.scan_integrity import ScanIntegrityError

# Suffix marking a bundled outfit template; its real game outfit ID is unknown.
REFERENCE_OUTFIT = "reference:"


def split_icon_key(key):
    """Split an icon key such as "1310#SPRING_MISSIVE" into (character, outfit)."""
    character, _, outfit = key.partition("#")
    return character, None if not outfit or outfit.startswith(REFERENCE_OUTFIT) else outfit


def equipped_frame_present(image):
    """Detect the equipped footer by its border edges; the label OCR is unreliable.

    Coordinates are in a 480x68 footer crop. Borderline contrast raises.
    """
    a = np.asarray(image.convert('RGB')).astype(np.int16)
    dy = np.abs(a[1:] - a[:-1]).mean(axis=2)
    sx, sy = image.width / 480, image.height / 68
    score = min(float(np.max(np.median(dy[int(y0*sy):int(y1*sy), int(x0*sx):int(x1*sx)], axis=1)))
                for y0,y1 in ((5,12),(40,48)) for x0,x1 in ((30,130),(340,430)))
    if 26 < score < 32:
        raise ScanIntegrityError(f'Uncertain equipped footer border ({score:.2f}); incomplete scan, no export.')
    return score >= 32


def rank_avatar(image, templates):
    query = cv2.resize(np.asarray(image.convert('RGB')), (100, 100))
    query = np.ascontiguousarray(query[8:93, 8:93])
    scores = []
    for key, template in templates.items():
        core = np.ascontiguousarray(template[20:80, 20:80, :3])
        if float(core.std()) < 1:
            continue
        score = float(cv2.matchTemplate(query, core, cv2.TM_CCOEFF_NORMED).max())
        if np.isfinite(score):
            scores.append((score, key))
    scores.sort(reverse=True)
    if not scores:
        return ('', 0.0, 0.0)
    score, key = scores[0]
    runner = next((s for s,k in scores[1:] if k.split('#')[0] != key.split('#')[0]), -1.0)
    return key, score, score-runner


def require_avatar_match(image, templates):
    key, score, margin = rank_avatar(image, templates)
    # An unknown portrait still has a best match, so require a clear winner.
    if score < .80 or margin < .05:
        raise ScanIntegrityError(
            f'Uncertain equipped portrait: candidate={key!r}, correlation={score:.3f}, '
            f'margin={margin:.3f}; incomplete scan, no export.'
        )
    return split_icon_key(key)
