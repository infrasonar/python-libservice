from .addr import addr_check as _addr_check


def _item_name(item: dict) -> str:
    return item['name']


def order(result: dict):
    """Order result items by item name."""
    for items in result.values():
        items.sort(key=_item_name)


def addr_check(addr: str):
    return _addr_check(addr)
