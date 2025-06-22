from config.const import (
    ASPECT_16_9,
    COLS,
    INV_TAB,
    OFFSET_X,
    OFFSET_Y,
    ROW_START_BOTTOM,
    ROW_START_TOP,
    ROWS,
    SORT_BUTTON,
)
from models.const import SORT_DATE, SORT_LV, SORT_RARITY


LIGHT_CONE_NAV_DATA = {
    ASPECT_16_9: {
        INV_TAB: (0.38, 0.06),
        SORT_BUTTON: (0.12, 0.91),
        SORT_RARITY: (0.12, 0.42),
        SORT_LV: (0.12, 0.49),
        SORT_DATE: (0.12, 0.84),
        ROW_START_TOP: (0.096, 0.162),
        ROW_START_BOTTOM: (0.1, 0.77),
        OFFSET_X: 0.065,
        OFFSET_Y: 0.13796,
        ROWS: 5,
        COLS: 9,
    }
}
