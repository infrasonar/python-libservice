import base64
from asyncio import Lock
from typing import Optional
from cryptography.fernet import Fernet
from .ticonn import ticonn


class Asset:
    __slots__ = (
        'container_id', 'asset_id', 'check_id', 'config', 'key', '_lock')

    container_id: int
    asset_id: int
    check_id: int
    config: dict
    key: Optional[bytes]
    lock: Optional[Lock]

    def __init__(self, container_id: int, asset_id: int, check_id: int,
                 config: dict):
        self.container_id = container_id
        self.asset_id = asset_id
        self.check_id = check_id
        self.config = config
        self.key = None
        self._lock = None

    def __repr__(self) -> str:
        return f"asset: {self.asset_id} check: {self.check_id}"

    def get_interval(self) -> int:
        """Returns the check interval in seconds."""
        return self.config['_interval']

    async def decrypt(self, secret: str):
        """Returns the decrypted value."""
        if self.key is None:
            self.key = await ticonn.run(
                'get_encryption_key',
                self.container_id)
            assert isinstance(self.key, bytes)

        assert self.key is not None, 'no encryption key'
        return Fernet(self.key).decrypt(base64.b64decode(secret)).decode()

    async def get_other_asset_configs(self, asset_id: int):
        return await ticonn.run(
            "get_asset_configs",
            self.container_id,
            asset_id)

    def get_lock(self) -> Lock:
        if self._lock is None:
            self._lock = Lock()
        return self._lock
