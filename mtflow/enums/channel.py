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
    trade = 'trade'
    order = 'order'
    position = 'position'
    balance = 'balance'

    def create_topic(self, account: str) -> str:
        return ':'.join([self.value, account])


class FundChannelTopic(StrEnum):
    channel = 'channel'  # chat channel
    agent = 'agent'  # agent's llm input and output
    
    def create_topic(self, name: str) -> str:
        '''
        Args:
            name: channel or agent name
        '''
        return ':'.join([self.value, name])
