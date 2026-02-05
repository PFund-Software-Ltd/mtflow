from __future__ import annotations

from typing import Literal, overload
from enum import StrEnum


class Channel(StrEnum):
    data = 'data'  # pfeed's data engine
    engine = 'engine'  # pfund's engine
    fund = 'fund'  # alphafund's fund
    
    @property
    def topic_class(self) -> type[StrEnum]:
        return {
            Channel.engine: EngineChannelTopic,
            Channel.fund: FundChannelTopic,
            Channel.data: DataChannelTopic,
        }[self]
    
    def create_channel(self, topic: str) -> str:
        return '.'.join([self.value, topic])



class DataChannelTopic(StrEnum):
    orderbook = quote = 'orderbook'
    tradebook = tick = 'tradebook'
    candlestick = kline = 'candlestick'

    def create_topic(self, resolution: str, symbol: str) -> str:
        """Build topic with params.
        
        DataChannelTopic.candlestick.create_topic('1m', 'BTC_USDT') → 'candlestick:1m:BTC_USDT'
        """
        from pfund.datas.resolution import Resolution
        return ':'.join([self.value, repr(Resolution(resolution)), symbol])
    
    
class EngineChannelTopic(StrEnum):
    # listen to component's signals:
    strategy = 'strategy'
    model = 'model'
    feature = 'feature'
    indicator = 'indicator'
    # listen to account's data:
    trade = 'trade'
    order = 'order'
    position = 'position'
    balance = 'balance'

    @overload
    def create_topic(
        self: Literal[
            EngineChannelTopic.strategy,
            EngineChannelTopic.model,
            EngineChannelTopic.feature,
            EngineChannelTopic.indicator,
        ],
        component_name: str,
    ) -> str:
        ...

    @overload
    def create_topic(
        self: Literal[
            EngineChannelTopic.trade,
            EngineChannelTopic.order,
            EngineChannelTopic.position,
            EngineChannelTopic.balance,
        ],
        account: str,
    ) -> str:
        ...

    def create_topic(self, name: str) -> str:
        return ':'.join([self.value, name])


class FundChannelTopic(StrEnum):
    channel = 'channel'  # chat channel
    agent = 'agent'  # agent's llm input and output
    
    def create_topic(self, name: str) -> str:
        '''
        Args:
            name: channel or agent name
        '''
        return ':'.join([self.value, name])
