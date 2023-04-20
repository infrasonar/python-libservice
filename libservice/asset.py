import base64
from typing import NamedTuple
from cryptography.fernet import Fernet
from .ticonn import ticonn


class Asset(NamedTuple):
    container_id: int
    asset_id: int
    check_id: int
    config: dict

    def __repr__(self) -> str:
        return f"asset: {self.asset_id} check: {self.check_id}"

    async def decrypt(self, secret: str):
        key = await ticonn.run('get_encryption_key', self.asset_id)
        return Fernet(key).decrypt(base64.b64decode(secret)).decode()
