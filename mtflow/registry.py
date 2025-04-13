from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pfund.typing import ComponentName

from pfeed.enums.data_category import DataCategory
from pfund.enums.component_type import ComponentType


class Registry:
    def __init__(self):
        self._data_registries = {
            DataCategory.market_data: {},
        }
        self._component_registries = {
            ComponentType.strategy: {},
            ComponentType.model: {},
            ComponentType.feature: {},
            ComponentType.indicator: {},
        }
    
    # TODO: show the DAG of the trading store
    def show_dependencies(self):
        raise NotImplementedError
    
    def register_component(
        self, 
        consumer: ComponentName, 
        component: ComponentName,
        metadata: dict,
        component_type: ComponentType,
    ):
        key = f"{component_type}:{component}"
        registry = self._component_registries[component_type]
            
        if key not in registry:
            # TODO: create BaseModelMetadata
            registry[key] = {
                "consumers": [consumer],
                "metadata": metadata,
            }
        else:
            if consumer not in registry[key]["consumers"]:
                registry[key]["consumers"].append(consumer)
