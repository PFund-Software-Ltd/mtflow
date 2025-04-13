from __future__ import annotations
from typing import TYPE_CHECKING, TypeAlias
if TYPE_CHECKING:
    import datetime
    from pfeed.typing import tDATA_SOURCE, GenericFrame
    from pfeed.enums import DataStorage
    from pfeed.feeds.market_feed import MarketFeed
    from pfeed.data_models.market_data_model import MarketDataModel
    from pfund.typing import ComponentName
    from pfund.datas.resolution import Resolution
    from pfund.products.product_base import BaseProduct

from dataclasses import dataclass, field

import polars as pl

from pfeed.enums import DataSource
from mtflow.stores.base_data_store import BaseDataStore


MarketDataKey: TypeAlias = str
ProductName: TypeAlias = str
ResolutionRepr: TypeAlias = str


@dataclass
class MarketDataMetadata:
    data_source: tDATA_SOURCE
    data_origin: str
    product: BaseProduct
    resolution: Resolution
    start_date: datetime.date
    end_date: datetime.date
    consumers: list[ComponentName] = field(default_factory=list)


class MarketDataStore(BaseDataStore):
    _registry: dict[MarketDataKey, MarketDataMetadata]
    _datas: dict[MarketDataKey, GenericFrame]
    
    @staticmethod
    def generate_data_key(
        data_source: tDATA_SOURCE,
        data_origin: str,
        product: ProductName,
        resolution: ResolutionRepr,
    ) -> MarketDataKey:
        return f"{data_source}:{data_origin}:{product}:{resolution}"
    
    def register_data(
        self,
        consumer: ComponentName,
        data_source: tDATA_SOURCE,
        data_origin: str,
        product: BaseProduct,
        resolution: Resolution,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> MarketDataKey:
        data_source = DataSource[data_source.upper()].value
        data_origin = data_origin or data_source
        data_key = self.generate_data_key(
            data_source=data_source,
            data_origin=data_origin,
            product=product.name,
            resolution=repr(resolution),
        )
        if data_key not in self._registry:
            self._registry[data_key] = MarketDataMetadata(
                data_source=data_source,
                data_origin=data_origin,
                product=product,
                resolution=resolution,
                start_date=start_date,
                end_date=end_date,
                consumers=[consumer],
            )
        else:
            if consumer not in self._registry[data_key].consumers:
                self._registry[data_key].consumers.append(consumer)

    def materialize(self, storage: DataStorage, storage_options: dict):
        '''Loads data from pfeed's data lakehouse into the store'''
        for metadata in self._registry.values():
            data_source: tDATA_SOURCE = metadata['data_source']
            data_origin = metadata['data_origin']
            product: BaseProduct = metadata['product']
            resolution: Resolution = metadata['resolution']
            data_key = self.generate_data_key(
                data_source=data_source,
                data_origin=data_origin,
                product=product.name,
                resolution=repr(resolution),
            )
            df = self.get_historical_data(
                data_source=data_source,
                data_origin=data_origin,
                product=product,
                resolution=resolution,
                start_date=metadata['start_date'],
                end_date=metadata['end_date'],
                storage=storage,
                storage_options=storage_options,
            )
            assert df is not None, f'No data found for {data_key}'
            self._add_data(data_key, df)
            # TODO: add data_source as new column? need to differentiate historical data from live data
        # TODO: concat all dataframes
        df = pl.concat(self._datas.values())
    
    def get_feed(self, data_source: tDATA_SOURCE, use_ray: bool=False) -> MarketFeed:
        from pfeed import get_market_feed
        return get_market_feed(
            data_source=data_source,
            data_tool=self._data_tool.value,
            use_ray=use_ray,
            use_deltalake=True,
        )
    
    def get_historical_data(
        self,
        data_source: tDATA_SOURCE,
        data_origin: str,
        product: BaseProduct,
        resolution: Resolution,
        start_date: datetime.date,
        end_date: datetime.date,
        storage: DataStorage,
        storage_options: dict,
    ):
        feed = self.get_feed(data_source, use_ray=...)
        lf: pl.LazyFrame = feed.retrieve(
            auto_transform=False,
        )
        df = lf.head(1).collect()
        # TODO
        retrieved_resolution = ...
        is_resample_required = ...
        
        df = feed.get_historical_data(
            product=product.basis, 
            symbol=product.symbol,
            resolution=resolution,
            start_date=start_date, 
            end_date=end_date,
            data_origin=data_origin,
            from_storage=storage.value,
            storage_options=storage_options,
            retrieve_per_date=is_resample_required,
            **product.specs
        )
        data_model = feed.create_data_model(
            product=product,
            resolution=resolution,
            start_date=start_date,
            end_date=end_date,
            data_origin=data_origin,
            **product.specs,
        )
        # TEMP
        print('***got historical data:\n', df)