import logging
from typing import Optional, Callable
from .net.package import Package
from .net.protocol import Protocol


class ApiProtocol(Protocol):

    PROTO_REQ_DATA = 0x00
    PROTO_REQ_INFO = 0x01
    PROTO_REQ_ALERTS_COUNT = 0x02
    PROTO_REQ_ALERTS = 0x03
    PROTO_REQ_ALERTS_ASSIGN = 0x04
    PROTO_REQ_ALERTS_MESSAGE = 0x05
    PROTO_REQ_ALERTS_CLOSE = 0x06
    PROTO_REQ_PATH = 0x07
    PROTO_REQ_PATH_SET = 0x08
    PROTO_REQ_STATE = 0x09
    PROTO_REQ_EXPRESSION = 0x0a
    PROTO_REQ_ALERT = 0x0b
    PROTO_REQ_AGENTCORES_INFO = 0x0c
    PROTO_REQ_ALERTS_ICALL = 0x0d

    PROTO_RES_INFO = 0x80
    PROTO_RES_ALERTS_COUNT = 0x81
    PROTO_RES_ALERTS = 0x82
    PROTO_RES_PATH = 0x83
    PROTO_RES_PATH_SET = 0x84
    PROTO_RES_STATE = 0x85
    PROTO_RES_EXPRESSION = 0x86
    PROTO_RES_ALERT = 0x87
    PROTO_RES_AGENTCORES_INFO = 0x88

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
        PROTO_RES_INFO: _on_res_data,
        PROTO_RES_ALERTS_COUNT: _on_res_data,
        PROTO_RES_ALERTS: _on_res_data,
        PROTO_RES_PATH: _on_res_data,
        PROTO_RES_PATH_SET: _on_res_data,
        PROTO_RES_STATE: _on_res_data,
        PROTO_RES_EXPRESSION: _on_res_data,
        PROTO_RES_ALERT: _on_res_data,
        PROTO_RES_AGENTCORES_INFO: _on_res_data,
        PROTO_RES_ERR: _on_res_err,
        PROTO_RES_OK: _on_res_ok,
    }):
        handle = _map.get(pkg.tp)
        if handle is None:
            logging.error(f'unhandled package type: {pkg.tp}')
        else:
            handle(self, pkg)
