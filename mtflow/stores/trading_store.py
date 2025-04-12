from __future__ import annotations
from typing import TYPE_CHECKING, TypeAlias
if TYPE_CHECKING:
    from pfeed.typing import tSTORAGE, tDATA_TOOL, tDATA_SOURCE, GenericData, GenericFrame, GenericSeries
    from pfeed.data_models.base_data_model import BaseDataModel
    from pfeed.storages.base_storage import BaseStorage
    from pfund.typing import tENVIRONMENT
    from pfund.datas.data_base import BaseData
    from pfund.datas.data_time_based import TimeBasedData
    from mtflow.registry import Registry

import datetime
from logging import Logger

import pfeed as pe
from pfeed.enums import DataTool, DataLayer, DataStorage
from pfund.enums import Environment
from mtflow.stores.market_data_store import MarketDataStore
from mtflow.typing import ComponentName, StrategyName, ModelName, IndicatorName, FeatureName


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
        self._market_data_store = MarketDataStore(
            data_tool=data_tool,
            registry=registry._market_data_registry,
            data_key=registry._generate_market_data_key,
        )
        # FIXME:
        # self._feed = pe.PFund(env=env, data_tool=data_tool)

    @property
    def registry(self):
        return self._registry
    
    # EXTEND
    @property
    def data_stores(self):
        return {
            'market_data': self._market_data_store,
        }
    
    @property
    def market(self):
        return self._market_data_store
    
    @property
    def storage(self) -> DataStorage:
        return self._storage
    
    def _set_logger(self, logger: Logger):
        self._logger = logger
    
    # TODO: show the DAG of the trading store
    def show_DAG(self):
        self._registry.show_DAG()

    # TODO: make mtstore frozen, no changes allowed
    def _freeze(self):
        pass
    
    def get_market_data_df(self, data: BaseData | None=None, unstack: bool=False) -> GenericFrame | None:
        pass
    get_data_df = get_market_data_df
    
    def get_complete_df(self) -> GenericFrame | None:
        pass
    
    def get_strategy_df(
        self, 
        name: StrategyName='', 
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
        name: ModelName='', 
        include_data: bool=False,
        as_series: bool=False,
    ) -> GenericFrame | GenericSeries | None:
        pass
    
    def get_indicator_df(
        self, 
        name: IndicatorName='', 
        include_data: bool=False,
        as_series: bool=False,
    ) -> GenericFrame | GenericSeries | None:
        pass
     
    def get_feature_df(
        self, 
        name: FeatureName='', 
        include_data: bool=False,
        as_series: bool=False,
    ) -> GenericFrame | GenericSeries | None:
        pass
    
    def _get_df(self) -> GenericFrame | None:
        pass

    def materialize(self):
        for data_store in self.data_stores.values():
            data_store.materialize(
                storage=self._storage,
                storage_options=self._storage_options,
            )
    
    def _write_to_storage(
        self, 
        data: GenericData, 
        data_model: BaseDataModel, 
        data_domain: str,
        metadata: dict | None=None,
    ):
        '''
        Load data from the online store (TradingStore) to the offline store (pfeed's data lakehouse).
        '''
        data_layer = self.data_layer.value
        storage: BaseStorage = pe.create_storage(
            storage=self._storage.value,
            data_model=data_model,
            data_layer=data_layer,
            data_domain=data_domain,
            storage_options=self._storage_options,
        )
        storage.write_data(data, metadata=metadata)
        # FIXME: add logger
        # self.logger.info(f'wrote {data_model} data to {storage.name} in {data_layer=}')
