from abc import ABC, abstractmethod
from asyncio import Event

from PIL import Image as PILImage
from PIL.Image import Image
from PyQt6.QtCore import pyqtBoundSignal

from enums.increment_type import IncrementType
from models.game_data import GameData
from utils.data import resource_path


class BaseParseStrategy(ABC):
    """BaseStrategy class for parsing data from screenshots."""

    SCAN_TYPE: IncrementType
    NAV_DATA: dict

    def __init__(
        self,
        game_data: GameData,
        log_signal: pyqtBoundSignal,
        update_signal: pyqtBoundSignal,
        interrupt_event: Event,
        debug: bool = False,
    ) -> None:
        """Constructor

        :param game_data: The GameData class instance
        :param log_signal: The log signal
        :param update_signal: The update signal
        :param interrupt_event: The interrupt event
        :param debug: Debug flag
        """
        self._game_data = game_data
        self._log_signal = log_signal
        self._update_signal = update_signal
        self._interrupt_event = interrupt_event
        self._debug = debug
        self._lock_icon = PILImage.open(resource_path("assets/images/lock.png"))

    @abstractmethod
    def get_optimal_sort_method(self, filters: dict) -> str:
        """Gets the optimal sort method based on the filters

        :param filters: The filters
        :return: The optimal sort method
        """
        pass

    @abstractmethod
    def check_filters(
        self, stats_dict: dict, filters: dict, uid: int
    ) -> tuple[dict, dict]:
        """Check if the stats dictionary passes the filters

        :param stats_dict: The stats dictionary
        :param filters: The filters
        :param uid: The UID of the item
        :raises ValueError: Thrown if the filter key does not have an int value
        :raises KeyError: Thrown if the filter key is not valid
        :return: The filter results and the stats dictionary
        """
        pass

    @abstractmethod
    def extract_stats_data(self, key: str, data: str | Image) -> str | Image:
        """Extract the stats data from the string

        :param key: The key
        :param data: The data
        :return: The stats data
        """
        pass

    @abstractmethod
    def parse(self, stats_dict: dict, uid: int) -> dict:
        """Parses the stats dictionary

        :param stats_dict: The stats dictionary
        :param uid: The UID of the light cone
        :return: The parsed stats dictionary
        """
        pass
