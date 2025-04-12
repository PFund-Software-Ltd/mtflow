from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pfeed.typing import tDATA_TOOL, tDATA_SOURCE
    from pfund.typing import tENVIRONMENT
    from pfund.datas.resolution import Resolution
    from pfund.products.product_base import BaseProduct

import datetime
from logging import Logger

from pfeed.enums import DataTool, DataStorage
from pfund.enums import Environment
from mtflow.stores.trading_store import TradingStore
from mtflow.typing import StrategyName, ComponentName
from mtflow.registry import Registry


class MTStore:
    '''
    A metadata store for tracking across trading stores.
    '''
    def __init__(self, env: tENVIRONMENT, data_tool: tDATA_TOOL='polars'):
        from pfund import get_config
        pfund_config = get_config()
        self._env = Environment[env.upper()]
        self._data_tool = DataTool[data_tool.lower()]
        self._storage = DataStorage[pfund_config.storage.upper()]
        self._storage_options = pfund_config.storage_options
        self._trading_stores: dict[StrategyName, TradingStore] = {}
        self._logger: Logger | None = None
        self._registry = Registry()
        self._frozen = False
    
    @property
    def registry(self):
        return self._registry
    
    @property
    def trading_stores(self):
        return self._trading_stores
    
    def _freeze(self):
        self._frozen = True
    
    def is_frozen(self):
        return self._frozen
    
    def _set_logger(self, logger: Logger):
        self._logger = logger
        
    # TODO
    def show_DAG(self, name: StrategyName):
        trading_store = self.get_trading_store(name)
        trading_store.show_DAG()
        
    def _create_trading_store(self):
        trading_store = TradingStore(
            env=self._env, 
            data_tool=self._data_tool, 
            storage=self._storage, 
            storage_options=self._storage_options,
            registry=self._registry,
        )
        return trading_store
    
    def add_trading_store(self, name: StrategyName) -> TradingStore:
        if self.is_frozen():
            raise ValueError('MTStore is frozen, no more trading stores can be added')
        if name in self._trading_stores:
            raise ValueError(f'Trading store {name} already exists')
        trading_store = self._create_trading_store()
        self._trading_stores[name] = trading_store
        return trading_store
    
    def get_trading_store(self, name: StrategyName) -> TradingStore:
        if name not in self._trading_stores:
            raise ValueError(f'Trading store {name} does not exist')
        return self._trading_stores[name]
    
    def register_market_data(
        self, 
        consumer: ComponentName,
        data_source: tDATA_SOURCE, 
        data_origin: str, 
        product: BaseProduct, 
        resolution: Resolution,
        start_date: datetime.date,
        end_date: datetime.date, 
    ):
        if self.is_frozen():
            raise ValueError('MTStore is frozen, no more market data can be registered')
        self._registry.register_market_data(
            consumer=consumer,
            data_source=data_source,
            data_origin=data_origin,
            product=product,
            resolution=resolution,
            start_date=start_date,
            end_date=end_date,
        )
    
    def materialize(self):
        if not self.is_frozen():
            self._freeze()
        for trading_store in self._trading_stores.values():
            trading_store.materialize()