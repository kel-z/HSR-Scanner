from config.const import (
    ASPECT_16_9,
    COLS,
    INV_TAB,
    OFFSET_X,
    OFFSET_Y,
    ROW_START_BOTTOM,
    ROW_START_TOP,
    ROWS,
    SORT,
    SORT_BUTTON,
)
from models.const import SORT_DATE, SORT_LV, SORT_RARITY

RELIC_NAV_DATA = {
    ASPECT_16_9: {
        INV_TAB: (0.43, 0.06),
        SORT_BUTTON: (0.12, 0.91),
        SORT_RARITY: (0.12, 0.7),
        SORT_LV: (0.12, 0.77),
        SORT_DATE: (0.12, 0.84),
        ROW_START_TOP: (0.096875, 0.23),
        ROW_START_BOTTOM: (0.096875, 0.776),
        OFFSET_X: 0.065,
        OFFSET_Y: 0.13796,
        ROWS: 5,
        COLS: 9,
    }
}
