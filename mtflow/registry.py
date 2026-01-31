from __future__ import annotations
from typing import TYPE_CHECKING, TypeAlias
if TYPE_CHECKING:
    from pfund._typing import EngineName, ComponentName

from pfeed.enums.data_category import DataCategory
from pfund.enums.component_type import ComponentType


# TEMP: remove these when they are defined in pfund.typing
EngineMetadata: TypeAlias = dict
ComponentMetadata: TypeAlias = dict
MarketDataMetadata: TypeAlias = dict


class Registry:
    def __init__(self):
        self._engine_registries: dict[EngineName, EngineMetadata] = {}
        self._component_registries: dict[ComponentType, dict[ComponentName, ComponentMetadata]] = {
            ComponentType.strategy: {},
            ComponentType.model: {},
            ComponentType.feature: {},
            ComponentType.indicator: {},
        }
        self._data_registries: dict[DataCategory, list[MarketDataMetadata]] = {
            DataCategory.MARKET_DATA: [],
        }
    
    # TODO: show the DAG of the trading store
    def show_dependencies(self):
        raise NotImplementedError
    
    def get_engine_registry(self, engine_name: EngineName):
        return self._engine_registries[engine_name]
    
    def get_component_registry(self, component_type: ComponentType):
        return self._component_registries[component_type]
    
    def get_data_registry(self, data_category: DataCategory):
        return self._data_registries[data_category]
    
    def register_engine(self, metadata: EngineMetadata):
        self._engine_registries[metadata['name']] = metadata
    
    def register_component(self, metadata: ComponentMetadata):
        consumers: list[ComponentName] = metadata['consumers']
        component_name: ComponentName = metadata['name']
        component_type: ComponentType = ComponentType[metadata['component_type']]
        if component_type != ComponentType.strategy:
            assert consumers, 'Consumers must not be empty for non-strategy components'
        component_registry = self.get_component_registry(component_type)
        if component_name not in component_registry:
            component_registry[component_name] = metadata
        for data_metadata in metadata['datas']:
            self.register_market_data(data_metadata)

    def register_market_data(self, metadata: MarketDataMetadata):
        data_registry = self.get_data_registry(metadata['data_category'])
        data_registry.append(metadata)