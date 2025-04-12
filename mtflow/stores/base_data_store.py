from __future__ import annotations
from typing import TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from pfeed.enums import DataTool
    from pfeed.typing import GenericData
    
from abc import ABC, abstractmethod


class BaseDataStore(ABC):
    def __init__(
        self, 
        data_tool: DataTool,
        registry: dict,
        key_generator: Callable,
    ):
        self._data_tool = data_tool
        self._registry = registry
        self._key_generator = key_generator
        self._datas: dict[str, GenericData] = {}
    
    @abstractmethod
    def materialize(self, *args, **kwargs):
        pass

    @abstractmethod
    def get_feed(self, *args, **kwargs):
        pass
    
    @abstractmethod
    def get_historical_data(self, *args, **kwargs):
        pass
    
    def _add_data(self, data_key: str, data: GenericData):
        self._datas[data_key] = data
    