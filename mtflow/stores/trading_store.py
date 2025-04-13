from __future__ import annotations
from typing import TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from pfeed.typing import GenericData, GenericFrame, GenericSeries
    from pfeed.data_models.base_data_model import BaseDataModel
    from pfeed.storages.base_storage import BaseStorage
    from pfund.datas.data_base import BaseData
    from mtflow.registry import Registry

from logging import Logger

from apscheduler.schedulers.background import BackgroundScheduler

import pfeed as pe
from pfeed.enums import DataTool, DataStorage, DataCategory
from pfund.enums import Environment
from mtflow.stores.market_data_store import MarketDataStore


class TradingStore:
    '''
    A TradingStore is a store that contains all data used in trading, from market data, computed features, to model predictions etc.
    '''
    def __init__(
        self,
        env: Environment,
        data_tool: DataTool,
        storage: DataStorage,
        storage_options: dict,
        registry: Registry,
    ):
        self._env = env
        self._data_tool = data_tool
        self._storage = storage
        self._storage_options = storage_options
        self._logger: Logger | None = None
        self._registry = registry
        self._scheduler = BackgroundScheduler()
        self._data_stores = {
            DataCategory.market_data: MarketDataStore(
                data_tool=data_tool,
                registry=registry._data_registries[DataCategory.market_data],
            ),
        }
        # FIXME:
        # self._pfund = pe.PFund(env=env, data_tool=data_tool)

    @property
    def market(self):
        return self._data_stores[DataCategory.market_data]
    
    def _set_logger(self, logger: Logger):
        self._logger = logger
    
    def _schedule_task(self, func: Callable, **kwargs):
        self._scheduler.add_job(func, trigger='interval', **kwargs)
    
    def show_dependencies(self):
        self._registry.show_dependencies()

    def get_market_data_df(self, data: BaseData | None=None, unstack: bool=False) -> GenericFrame | None:
        pass
    get_data_df = get_market_data_df
    
    def get_complete_df(self) -> GenericFrame | None:
        pass
    
    def get_strategy_df(
        self, 
        name: str='', 
        include_data: bool=False,
        as_series: bool=False,
    ) -> GenericFrame | GenericSeries | None:
        '''
        Get the dataframe of the strategy's outputs.
        Args:
            name: the name of the strategy
            include_data: whether to include the data dataframe in the output dataframe
                if not, only returns the strategy's outputs as a dataframe
            as_series: whether to return the dataframe as a series
        '''
        pass
    
    def get_model_df(
        self, 
        name: str='', 
        include_data: bool=False,
        as_series: bool=False,
    ) -> GenericFrame | GenericSeries | None:
        pass
    
    def get_indicator_df(
        self, 
        name: str='', 
        include_data: bool=False,
        as_series: bool=False,
    ) -> GenericFrame | GenericSeries | None:
        pass
     
    def get_feature_df(
        self, 
        name: str='', 
        include_data: bool=False,
        as_series: bool=False,
    ) -> GenericFrame | GenericSeries | None:
        pass
    
    def _get_df(self) -> GenericFrame | None:
        pass

    def materialize(self):
        for data_store in self._data_stores.values():
            data_store.materialize(
                storage=self._storage,
                storage_options=self._storage_options,
            )
    
    def persist_to_storage(
        self, 
        data: GenericData, 
        data_model: BaseDataModel, 
        data_domain: str,
        metadata: dict | None=None,  # TODO: add run_id, ingestion_time (if delta table has it) etc.?
    ):
        '''
        Load data from the online store (TradingStore) to the offline store (pfeed's data lakehouse).
        '''
        storage: BaseStorage = pe.create_storage(
            storage=self._storage.value,
            data_model=data_model,
            data_layer='curated',
            data_domain=data_domain,
            storage_options=self._storage_options,
        )
        storage.write_data(data, metadata=metadata)
        # FIXME: add logger
        # self.logger.info(f'wrote {data_model} data to {storage.name} in {data_layer=}')

    # TODO: when pfeed's data recording is ready
    def _rehydrate_from_lakehouse(self):
        '''
        Load data from pfeed's data lakehouse if theres missing data after backfilling.
        '''
        pass
    