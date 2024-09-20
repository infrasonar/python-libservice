import abc
from .asset import Asset
from typing import Tuple, List, Optional


class CheckBase(abc.ABC):
    key: str  # Check key (must not be changed)

    def __init_subclass__(cls, **kwargs):
        if not hasattr(cls, 'key'):
            raise NotImplementedError('key not implemented')
        if not isinstance(cls.key, str):
            raise NotImplementedError('key must be type str')
        return super().__init_subclass__(**kwargs)

    @classmethod
    @abc.abstractmethod
    async def run(cls, ts: float, asset: Asset) -> Tuple[
            Optional[dict], Optional[dict]]:
        ...


class CheckBaseMulti(abc.ABC):
    key: str  # Check key (must not be changed)

    def __init_subclass__(cls, **kwargs):
        if not hasattr(cls, 'key'):
            raise NotImplementedError('key not implemented')
        if not isinstance(cls.key, str):
            raise NotImplementedError('key must be type str')
        return super().__init_subclass__(**kwargs)

    @classmethod
    @abc.abstractmethod
    async def run(cls, ts: float, assets: List[Asset]) -> List[
            Tuple[Optional[dict], Optional[dict]]]:
        ...
