from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pfund.engines.base_engine import BaseEngine

from pfund.enums import RunMode


'''
TODO: potential implementation of distributing workloads across multiple trade engines
- multiple engines to pull (zmq.PULL) data from different sources (zmq.PUSH)?
- multiple engines (multiple publishers) -> components (strategy/model/feature)
    - use Proxy (XPUB,XSUB), see https://zguide.zeromq.org/docs/chapter2/#The-Dynamic-Discovery-Problem
- each engine should also be a Ray actor
    - see https://zguide.zeromq.org/docs/chapter2/#Node-Coordination
'''
# Meta Trade Engine
class MTEngine:
    # add more engines for sharding, engine should be a Ray actor
    def add_engine(self, engine: BaseEngine, **ray_kwargs):
        import ray
        # TODO: refer to add_strategy in pfund's base_engine.py
        Engine = engine.__class__
        EngineActor = ray.remote(**ray_kwargs)(Engine)
        engine = EngineActor.remote(...)
        engine._set_run_mode(RunMode.REMOTE)
        raise NotImplementedError('Not implemented')
