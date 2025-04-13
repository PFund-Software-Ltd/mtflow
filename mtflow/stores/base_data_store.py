from __future__ import annotations
from typing import TYPE_CHECKING, TypeAlias
if TYPE_CHECKING:
    from pfeed.enums import DataTool
    from pfeed.typing import GenericData
    
from abc import ABC, abstractmethod


DataKey: TypeAlias = str


class BaseDataStore(ABC):
    def __init__(
        self, 
        data_tool: DataTool,
        registry: dict,
    ):
        self._data_tool = data_tool
        self._registry = registry
        self._datas: dict[DataKey, GenericData] = {}
    
    @staticmethod
    @abstractmethod
    def _generate_data_key(*args, **kwargs) -> DataKey:
        pass

    @abstractmethod
    def register_data(self, *args, **kwargs):
        pass
    
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
    