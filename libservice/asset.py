import base64
from typing import Optional
from cryptography.fernet import Fernet
from .ticonn import ticonn


class Asset:
    __slots__ = ('container_id', 'asset_id', 'check_id', 'config', 'key')

    container_id: int
    asset_id: int
    check_id: int
    config: dict
    key: Optional[str]

    def __init__(self, container_id: int, asset_id: int, check_id: int,
                 config: dict):
        self.container_id = container_id
        self.asset_id = asset_id
        self.check_id = check_id
        self.config = config
        self.key = None

    def __repr__(self) -> str:
        return f"asset: {self.asset_id} check: {self.check_id}"

    async def decrypt(self, secret: str):
        if self.key is None:
            self.key = await ticonn.run(
                'get_encryption_key',
                self.container_id)

        return Fernet(self.key).decrypt(base64.b64decode(secret)).decode()
