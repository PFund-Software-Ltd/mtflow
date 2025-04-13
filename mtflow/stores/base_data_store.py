from __future__ import annotations
from typing import TYPE_CHECKING, TypeAlias
if TYPE_CHECKING:
    from pfeed.enums import DataTool, DataStorage
    from pfeed.typing import GenericData
    from pfeed.feeds.pfund.pfund_feed import PFundFeed
    from pfeed.data_models.pfund_data_model import PFundDataModel
    from pfeed.storages.base_storage import BaseStorage
    
from abc import ABC, abstractmethod
from logging import Logger

from pfeed import create_storage


DataKey: TypeAlias = str


class BaseDataStore(ABC):
    def __init__(
        self, 
        data_tool: DataTool,
        storage: DataStorage,
        storage_options: dict,
        registry: dict,
        feed: PFundFeed,
    ):
        self._data_tool = data_tool
        self._storage = storage
        self._storage_options = storage_options
        self._registry = registry
        self._logger: Logger | None = None
        self._data: GenericData | None = None
        self._feed: PFundFeed = feed
        
    @staticmethod
    @abstractmethod
    def _generate_data_key(self, *args, **kwargs) -> DataKey:
        pass
    
    @abstractmethod
    def _register_data(self, *args, **kwargs):
        pass
    
    @abstractmethod
    def _materialize(self, *args, **kwargs):
        pass

    @abstractmethod
    def _get_historical_data(self, *args, **kwargs) -> GenericData:
        pass

    @property
    def data(self) -> GenericData | None:
        if self._data is None:
            # TODO: read from storage if data is not in memory
            pass
        else:
            return self._data
    
    def _set_logger(self, logger: Logger):
        self._logger = logger
        
    def _set_data(self, data: GenericData):
        self._data = data
    
    def _write_to_storage(self, data: GenericData):
        '''
        Load data (e.g. market data) from the online store (TradingStore) to the offline store (pfeed's data lakehouse).
        '''
        data_model: PFundDataModel = self._feed.create_data_model(...)
        data_layer = 'curated'
        data_domain = 'trading_data'
        metadata = {}  # TODO
        storage: BaseStorage = create_storage(
            storage=self._storage.value,
            data_model=data_model,
            data_layer=data_layer,
            data_domain=data_domain,
            storage_options=self._storage_options,
        )
        storage.write_data(data, metadata=metadata)
        self._logger.info(f'wrote {data_model} data to {storage.name} in {data_layer=} {data_domain=}')
