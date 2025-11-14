import abc
from .asset import Asset


class CheckBase(abc.ABC):
    key: str  # Check key (must not be changed)
    use_unchanged: bool = False

    def __init_subclass__(cls, **kwargs):
        if not hasattr(cls, 'key'):
            raise NotImplementedError('key not implemented')
        if not isinstance(cls.key, str):
            raise NotImplementedError('key must be type str')
        return super().__init_subclass__(**kwargs)

    @classmethod
    @abc.abstractmethod
    async def run(cls, ts: float, asset: Asset) -> tuple[
            dict | None, dict | None]:
        ...


class CheckBaseMulti(abc.ABC):
    key: str  # Check key (must not be changed)
    use_unchanged: bool = False

    def __init_subclass__(cls, **kwargs):
        if not hasattr(cls, 'key'):
            raise NotImplementedError('key not implemented')
        if not isinstance(cls.key, str):
            raise NotImplementedError('key must be type str')
        return super().__init_subclass__(**kwargs)

    @classmethod
    @abc.abstractmethod
    async def run(cls, ts: float, assets: list[Asset]) -> list[
            tuple[dict | None, dict | None]]:
        ...
