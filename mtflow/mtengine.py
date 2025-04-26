from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pfund.engines.base_engine import BaseEngine


'''
TODO: potential implementation of distributing workloads across multiple trade engines
- multiple engines to pull (zmq.PULL) data from different sources (zmq.PUSH)?
- multiple engines (multiple publishers) -> components (strategy/model/feature)
    - use Proxy (XPUB,XSUB), see https://zguide.zeromq.org/docs/chapter2/#The-Dynamic-Discovery-Problem
- each engine should also be a Ray actor
    - see https://zguide.zeromq.org/docs/chapter2/#Node-Coordination
'''
class MTEngine:
    # add more engines for sharding, engine should be a Ray actor
    def add_engine(self, engine: BaseEngine):
        raise NotImplementedError('Not implemented')
