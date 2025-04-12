from __future__ import annotations
from typing_extensions import TypedDict
from typing import TYPE_CHECKING, TypeAlias
if TYPE_CHECKING:
    import datetime
    from pfeed.typing import tDATA_SOURCE
    from pfund.products.product_base import BaseProduct
    from pfund.datas.resolution import Resolution


ComponentName: TypeAlias = str
StrategyName: TypeAlias = str
ModelName: TypeAlias = str
IndicatorName: TypeAlias = str
FeatureName: TypeAlias = str
DataOrigin: TypeAlias = str


class MarketDataMetadata(TypedDict):
    data_source: tDATA_SOURCE
    data_origin: str
    product: BaseProduct
    resolution: Resolution
    start_date: datetime.date
    end_date: datetime.date
    consumers: list[ComponentName]
MarketDataKey: TypeAlias = str
ProductName: TypeAlias = str
ResolutionRepr: TypeAlias = str