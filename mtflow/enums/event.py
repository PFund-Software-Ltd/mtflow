from typing import Protocol, TypeAlias, TypeVar, Literal, runtime_checkable

from enum import StrEnum

from msgspec import Struct

from mtflow.enums.channel import Channel


FullChannelName: TypeAlias = str
@runtime_checkable
class EventLike(Protocol):
    event: str
    data: Struct | None

EventStruct = TypeVar("EventStruct", bound=EventLike)


__all__ = [
    'Event',
    'ConnectedEvent',
    'DisconnectedEvent',
    'SubscribeEvent',
    'UnsubscribeEvent',
    'PingPongEvent',
    'DataEvent',
    'EngineEvent',
    'FundEvent',
]


class Event(StrEnum):
    # NOTE: channel name (not full channel) is used as event name
    data = Channel.data
    engine = Channel.engine
    fund = Channel.fund

    subscribe = 'subscribe'
    unsubscribe = 'unsubscribe'
    connected = 'connected'
    disconnected = 'disconnected'
    ping = 'ping'
    pong = 'pong'

    @property
    def event_class(self) -> type[Struct]:
        return {
            Event.connected: ConnectedEvent,
            Event.disconnected: DisconnectedEvent,
            Event.subscribe: SubscribeEvent,
            Event.unsubscribe: UnsubscribeEvent,
            Event.ping: PingPongEvent,
            Event.pong: PingPongEvent,
            Event.fund: FundEvent,
            Event.engine: EngineEvent,
            Event.data: DataEvent,
        }[self]


class ConnectedEvent(Struct):
    class Data(Struct, omit_defaults=True):
        ts: float | None = None  # used by server -> client only
        
    data: Data
    event: Literal['connected'] = Event.connected
    
    
class DisconnectedEvent(Struct):
    class Data(Struct, omit_defaults=True):
        ts: float | None = None  # used by server -> client only
        
    data: Data
    event: Literal['disconnected'] = Event.disconnected


class SubscribeEvent(Struct):
    class Data(Struct, omit_defaults=True):
        channels: list[FullChannelName]
        ts: float | None = None  # used by server -> client only
        # NOTE: conceptually, error is None = successful
        error: str | None = None  # used by server -> client only
        
    data: Data
    event: Literal['subscribe'] = Event.subscribe


class UnsubscribeEvent(Struct):
    class Data(Struct, omit_defaults=True):
        channels: list[FullChannelName]
        ts: float | None = None  # used by server -> client only
        error: str | None = None  # used by server -> client only
        
    data: Data
    event: Literal['unsubscribe'] = Event.unsubscribe


class PingPongEvent(Struct, omit_defaults=True):
    class Data(Struct, omit_defaults=True):
        ts: float | None = None
    
    event: Literal['ping', 'pong']
    data: Data | None = None
    
    
# TODO
class DataEvent(Struct):
    pass


# TODO
class EngineEvent(Struct):
    pass


# TODO
class FundEvent(Struct):
    class Data(Struct, omit_defaults=True):
        channel: FullChannelName
        message: str
        ts: float | None = None  # used by server -> client only
        error: str | None = None  # used by server -> client only
    
    data: Data
    event: Literal['fund'] = Event.fund
