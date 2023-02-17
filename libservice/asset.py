from typing import NamedTuple


class Asset(NamedTuple):
    container_id: int
    asset_id: int
    check_id: int
    config: dict

    def __repr__(self) -> str:
        return f"asset: {self.asset_id} check: {self.check_id}"
