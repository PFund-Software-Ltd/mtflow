from typing import Literal, TypeAlias

from enum import StrEnum

from msgspec import Struct

from mtflow.enums.channel import Channel


FullChannelName: TypeAlias = str


class Event(StrEnum):
    # NOTE: channel name (not full channel) is used as event name
    data = Channel.data
    engine = Channel.engine
    fund = Channel.fund

    subscribe = 'subscribe'
    unsubscribe = 'unsubscribe'
    ping = 'ping'
    pong = 'pong'

    @property
    def event_class(self) -> type[Struct]:
        return {
            Event.subscribe: SubscribeEvent,
            Event.unsubscribe: UnsubscribeEvent,
            Event.ping: PingPongEvent,
            Event.pong: PingPongEvent,
            Event.fund: FundEvent,
            Event.engine: EngineEvent,
            Event.data: DataEvent,
        }[self]
    

class SubscribeEvent(Struct):
    class Data(Struct):
        ts: float | None = None  # used by server -> client only
        # NOTE: conceptually, error is None = successful
        error: str | None = None  # used by server -> client only
        channels: list[FullChannelName]
        
    event: Literal[Event.subscribe] = Event.subscribe
    data: Data


class UnsubscribeEvent(Struct):
    class Data(Struct):
        ts: float | None = None  # used by server -> client only
        error: str | None = None  # used by server -> client only
        channels: list[FullChannelName]
        
    event: Literal[Event.unsubscribe] = Event.unsubscribe
    data: Data


class PingPongEvent(Struct):
    class Data(Struct):
        ts: float | None = None
    
    event: Literal[Event.ping | Event.pong]
    data: Data | None = None
    
    
# TODO
class DataEvent(Struct):
    pass


# TODO
class EngineEvent(Struct):
    pass


# TODO
class FundEvent(Struct):
    class Data(Struct):
        ts: float | None = None  # used by server -> client only
        error: str | None = None  # used by server -> client only
        channel: FullChannelName
        message: str
    
    event: Literal[Event.fund] = Event.fund
    data: Data