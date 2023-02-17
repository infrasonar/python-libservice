import asyncio
import logging
import random
from typing import Optional, Dict, List, Awaitable
from .net.package import Package
from .protocol import ApiProtocol


class HubClient:

    def __init__(self, auto_reconnect: bool = True):
        self._loop = asyncio.get_event_loop()
        self._protocol = None
        self._reconnect = auto_reconnect
        self._reconnecting = False
        self._pool = None
        self._pool_idx = 0
        self._request = self._ensure_write if auto_reconnect else self._write

    def close(self):
        if self._protocol and self._protocol.transport:
            self._protocol.transport.close()
        self._protocol = None

    def is_connected(self) -> bool:
        return self._protocol is not None and self._protocol.is_connected()

    def connect_pool(self, pool: list) -> asyncio.Future:
        assert self.is_connected() is False
        assert self._reconnecting is False
        assert len(pool), 'pool must contain at least one node'

        self._pool = tuple((
            (address, 8700) if isinstance(address, str) else address
            for address in pool))
        self._pool_idx = random.randint(0, len(pool) - 1)
        return self.reconnect()

    def connect(self, host: str, port: int = 8700,
                timeout: Optional[int] = 5) -> asyncio.Future:
        assert self.is_connected() is False
        self._pool = ((host, port),)
        self._pool_idx = 0
        return self._connect(timeout=timeout)

    def reconnect(self) -> Optional[asyncio.Future]:
        if self._reconnecting:
            return
        self._reconnecting = True
        return asyncio.ensure_future(self._reconnect_loop())

    async def _connect(self, timeout=5):
        host, port = self._pool[self._pool_idx]
        try:
            conn = self._loop.create_connection(
                lambda: ApiProtocol(self._on_connection_lost),
                host=host,
                port=port
            )
            _, self._protocol = await asyncio.wait_for(
                conn,
                timeout=timeout)
        finally:
            self._pool_idx += 1
            self._pool_idx %= len(self._pool)

    def _on_connection_lost(self):
        self._protocol = None
        if self._reconnect:
            self.reconnect()

    async def _reconnect_loop(self):
        try:
            wait_time = 1
            timeout = 2
            protocol = self._protocol
            while True:
                host, port = self._pool[self._pool_idx]
                try:
                    await self._connect(timeout=timeout)
                except Exception as e:
                    logging.error(
                        f'Connecting to {host}:{port} failed: '
                        f'{e}({e.__class__.__name__}), '
                        f'Try next connect in {wait_time} seconds'
                    )
                else:
                    if protocol and protocol.transport:
                        self._loop.call_later(10.0, protocol.transport.close)
                    break

                await asyncio.sleep(wait_time)
                wait_time *= 2
                wait_time = min(wait_time, 60)
                timeout = min(timeout + 1, 10)
        finally:
            self._reconnecting = False

    async def _ensure_write(self, pkg):
        if not self._pool:
            raise ConnectionError('no connection')
        while True:
            if not self.is_connected():
                logging.info('Wait for a connection')
                self.reconnect()  # ensure the re-connect loop
                await asyncio.sleep(1.0)
                continue

            try:
                res = await self._protocol.request(pkg, timeout=10)
            except Exception as e:
                logging.error(
                    f'Failed to transmit package: '
                    f'{e}({e.__class__.__name__}) (will try again)')
                await asyncio.sleep(1.0)
                continue

            return res

    async def _write(self, pkg):
        if not self.is_connected():
            raise ConnectionError('no connection')
        return await self._protocol.request(pkg, timeout=10)

    def test_expression(self, path: list, expression: str) -> Awaitable:
        pkg = Package.make(
            ApiProtocol.PROTO_REQ_EXPRESSION,
            data=[path, expression]
        )
        return self._request(pkg)

    def get_state(self, asset_id: int) -> Awaitable[dict]:
        pkg = Package.make(
            ApiProtocol.PROTO_REQ_STATE,
            data=asset_id,
        )
        return self._request(pkg)

    def get_path(self, container_ids: list, asset_ids: list, path: list,
                 metrics: Optional[list] = None,
                 expr: Optional[dict] = None) -> Awaitable[list]:
        pkg = Package.make(
            ApiProtocol.PROTO_REQ_PATH,
            data=[container_ids, asset_ids, path, metrics, expr]
        )
        return self._request(pkg)

    def get_path_set(self, container_ids: list, asset_ids: list,
                     path: list, metric: str) -> Awaitable[list]:
        pkg = Package.make(
            ApiProtocol.PROTO_REQ_PATH_SET,
            data=[container_ids, asset_ids, path, metric]
        )
        return self._request(pkg)

    def get_alert(self, alert: list) -> Awaitable[dict]:
        pkg = Package.make(
            ApiProtocol.PROTO_REQ_ALERT,
            data=alert,
        )
        return self._request(pkg)

    def get_agentcores_info(self,
                            agentcore_ids: List[int]
                            ) -> Awaitable[Dict[int, bool]]:
        pkg = Package.make(
            ApiProtocol.PROTO_REQ_AGENTCORES_INFO,
            data=agentcore_ids
        )
        return self._request(pkg)

    def get_alerts_count(self, container_ids: list,
                         asset_ids: Optional[list] = [],
                         user_id: Optional[int] = None) -> Awaitable[list]:
        pkg = Package.make(
            ApiProtocol.PROTO_REQ_ALERTS_COUNT,
            data=[container_ids, asset_ids, user_id]
        )
        return self._request(pkg)

    def get_alerts(self, container_ids: list,
                   asset_ids: Optional[list] = [],
                   user_id: Optional[int] = None,
                   with_actions: Optional[bool] = False,
                   with_names: Optional[bool] = False) -> Awaitable[list]:
        pkg = Package.make(
            ApiProtocol.PROTO_REQ_ALERTS,
            data=[container_ids, asset_ids, user_id, with_actions, with_names]
        )
        return self._request(pkg)

    def alerts_assign(self, alerts: list, message: str, user_id: int,
                      assign_user_id: int, ts: int) -> Awaitable:
        pkg = Package.make(
            ApiProtocol.PROTO_REQ_ALERTS_ASSIGN,
            data=[alerts, message, user_id, assign_user_id, ts]
        )
        return self._request(pkg)

    def alerts_message(self, alerts: list, message: str, user_id: int,
                       ts: int) -> Awaitable:
        pkg = Package.make(
            ApiProtocol.PROTO_REQ_ALERTS_MESSAGE,
            data=[alerts, message, user_id, ts]
        )
        return self._request(pkg)

    def alerts_close(self, alerts: list, message: str, user_id: int,
                     ts: int) -> Awaitable:
        pkg = Package.make(
            ApiProtocol.PROTO_REQ_ALERTS_CLOSE,
            data=[alerts, message, user_id, ts]
        )
        return self._request(pkg)

    def alerts_integration_call(self, alerts: list, user_id: int,
                                integration_key: int, data: int,
                                ts: int) -> Awaitable:
        pkg = Package.make(
            ApiProtocol.PROTO_REQ_ALERTS_ICALL,
            data=[alerts, user_id, integration_key, data, ts]
        )
        return self._request(pkg)

    def send_check_data(self, path: list, check_data: dict) -> Awaitable:
        pkg = Package.make(
            ApiProtocol.PROTO_REQ_DATA,
            data=[path, check_data],
            partid=path[0],  # asset_id
        )
        return self._request(pkg)
