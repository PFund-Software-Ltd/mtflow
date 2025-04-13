from __future__ import annotations
from typing import TYPE_CHECKING, Callable, TypeAlias
if TYPE_CHECKING:
    from pfeed.typing import tDATA_TOOL, tDATA_SOURCE
    from pfund.typing import tENVIRONMENT
    from pfund.datas.resolution import Resolution
    from pfund.products.product_base import BaseProduct
    from pfund.typing import ComponentName

import datetime
from logging import Logger

from apscheduler.schedulers.background import BackgroundScheduler

from pfeed.enums import DataTool, DataStorage, DataCategory
from pfund.enums import Environment, ComponentType
from mtflow.stores.trading_store import TradingStore
from mtflow.registry import Registry


StrategyName: TypeAlias = str


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
        self._scheduler = BackgroundScheduler()
        self._frozen = False
    
    def freeze(self):
        self._frozen = True
    
    def is_frozen(self):
        return self._frozen
    
    def _set_logger(self, logger: Logger):
        self._logger = logger
    
    def _schedule_task(self, func: Callable, **kwargs):
        self._scheduler.add_job(func, trigger='interval', **kwargs)
        
    # TODO: show ALL dependencies when name=None
    def show_dependencies(self, name: StrategyName | None=None):
        trading_store = self.get_trading_store(name)
        trading_store.show_dependencies()
        
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
    
    def _register_data(self, data_category: DataCategory, **kwargs):
        if self.is_frozen():
            raise ValueError(f'MTStore is frozen, no more {data_category} can be registered')
        consumer = kwargs['consumer']
        assert consumer in self._trading_stores, f'No trading store found for {consumer}, cannot register {data_category}'
        if data_category == DataCategory.market_data:
            data_store = self._trading_stores[consumer].market
        else:
            raise ValueError(f'{data_category} registry is not supported')
        data_store.register_data(**kwargs)
    
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
        params = {k: v for k, v in locals().items() if k != 'self'}
        self._register_data(DataCategory.market_data, **params)

    def _register_component(
        self, 
        consumer: ComponentName,
        component: ComponentName,
        metadata: dict,
        component_type: ComponentType,
    ):
        if self.is_frozen():
            raise ValueError(f'MTStore is frozen, no more {component_type} can be registered')
        self._registry.register_component(consumer, component, metadata, component_type)
    
    def register_strategy(self, consumer: ComponentName, component: ComponentName, metadata: dict):
        self._register_component(consumer, component, metadata, ComponentType.strategy)

    def register_model(self, consumer: ComponentName, component: ComponentName, metadata: dict):
        self._register_component(consumer, component, metadata, ComponentType.model)
        
    def register_feature(self, consumer: ComponentName, component: ComponentName, metadata: dict):
        self._register_component(consumer, component, metadata, ComponentType.feature)
        
    def register_indicator(self, consumer: ComponentName, component: ComponentName, metadata: dict):
        self._register_component(consumer, component, metadata, ComponentType.indicator)
