import logging
from typing import Optional, Callable
from .net.package import Package
from .net.protocol import Protocol


class ApiProtocol(Protocol):

    PROTO_REQ_DATA = 0x00
    PROTO_REQ_ALERTS_COUNT = 0x02
    PROTO_REQ_GET_DATA = 0x11

    PROTO_RES_ALERTS_COUNT = 0x81
    PROTO_RES_GET_DATA = 0x8b
    PROTO_RES_ERR = 0xe0
    PROTO_RES_OK = 0xe1

    def __init__(self, connection_lost: Callable):
        super().__init__()
        self.set_connection_lost(connection_lost)

    def connection_lost(self, exc: Optional[Exception]):
        super().connection_lost(exc)
        self._connection_lost()

    def set_connection_lost(self, connection_lost: Callable):
        self._connection_lost = connection_lost

    def _on_res_data(self, pkg):
        future = self._get_future(pkg)
        if future is None:
            return
        future.set_result(pkg.data)

    def _on_res_err(self, pkg: Package):
        future = self._get_future(pkg)
        if future is None:
            return
        future.set_exception(Exception(pkg.data))

    def _on_res_ok(self, pkg):
        future = self._get_future(pkg)
        if future is None:
            return
        future.set_result(None)

    def on_package_received(self, pkg, _map={
        PROTO_RES_ALERTS_COUNT: _on_res_data,
        PROTO_RES_GET_DATA: _on_res_data,
        PROTO_RES_ERR: _on_res_err,
        PROTO_RES_OK: _on_res_ok,
    }):
        handle = _map.get(pkg.tp)
        if handle is None:
            logging.error(f'Unhandled package type: {pkg.tp}')
        else:
            handle(self, pkg)
