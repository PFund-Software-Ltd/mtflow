from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pfeed.typing import tDATA_SOURCE
    from pfund.models.model_base import BaseFeature
    from pfund.datas.resolution import Resolution
    from pfund.products.product_base import BaseProduct
    from mtflow.typing import (
        ComponentName, 
        # types for market data registry
        MarketDataMetadata, 
        MarketDataKey, 
        ProductName, 
        ResolutionRepr,
    )

import datetime

from pfeed.enums import DataSource


class Registry:
    _market_data_registry: dict[MarketDataKey, MarketDataMetadata]
    
    def __init__(self):
        self._market_data_registry = {}
        self._strategy_registry = {}     # track strategies
        self._feature_registry = {}      # track features
        self._model_registry = {}        # track models
        self._dependency_graph = {}      # track relationships between components
    
    # TODO: show the DAG of the trading store
    def show_DAG(self):
        pass
    
    @staticmethod
    def _generate_market_data_key(
        data_source: tDATA_SOURCE,
        data_origin: str,
        product: ProductName,
        resolution: ResolutionRepr,
    ) -> MarketDataKey:
        return f"{data_source}:{data_origin}:{product}:{resolution}"
    
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
        data_source = DataSource[data_source.upper()].value
        data_origin = data_origin or data_source
        key = self._generate_market_data_key(
            data_source=data_source,
            data_origin=data_origin,
            product=product.name,
            resolution=repr(resolution),
        )
        if key not in self._market_data_registry:
            self._market_data_registry[key] = {
                "data_source": data_source,
                "data_origin": data_origin,
                "product": product,
                "resolution": resolution,
                "start_date": start_date,
                "end_date": end_date,
                "consumers": [consumer]
            }
        else:
            if consumer not in self._market_data_registry[key]["consumers"]:
                self._market_data_registry[key]["consumers"].append(consumer)


    # TODO:
    '''
    Why it matters: 
    You need to know 
    - what this feature is, 
    - where it came from, 
    - what version of logic it uses, 
    - and how it’s been used.
    - add versioning, metadata etc.
    '''
    def register_feature(
        self,
        feature: BaseFeature,
    ):
        key = f"feature:{name}"
    
        # Add to feature registry
        self._feature_registry[key] = {
            "name": name,
            "metadata": metadata or {},
            # other properties
        }
        
        # Update dependency graph for this component
        if key not in self._dependency_graph:
            self._dependency_graph[key] = {"inputs": input_dependencies, "outputs": []}
        else:
            # Update inputs if this component already exists
            self._dependency_graph[key]["inputs"] = input_dependencies
        
        # Update outputs for all input dependencies
        for input_dep in input_dependencies:
            if input_dep in self._dependency_graph:
                if key not in self._dependency_graph[input_dep]["outputs"]:
                    self._dependency_graph[input_dep]["outputs"].append(key)
            else:
                # Create entry for dependency if it doesn't exist yet
                self._dependency_graph[input_dep] = {"inputs": [], "outputs": [key]}

    def list_features(self):
        pass