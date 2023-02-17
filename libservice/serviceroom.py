import asyncio
import functools
import logging
import time
import os
from collections import defaultdict
from thingsdb.room import Room
from thingsdb.room import event
from typing import List, Dict, Tuple, Callable, Union, Optional
from .hub import hub
from .exceptions import CheckException
from .asset import Asset
from .check import CheckBase, CheckBaseMulti


HUB_REQ_SLEEP = .001
SLEEP_TIME = int(os.getenv('SLEEP_TIME', 2))
assert 60 >= SLEEP_TIME > 0


class ServiceRoom(Room):

    def init(self, collector_key: str,
             checks: Tuple[Union[CheckBase, CheckBaseMulti]],
             on_log_level: Callable[[int], None], no_count: bool = False):
        self.collector_key = collector_key
        self._checks = {check.key: check for check in checks}
        self._last = int(time.time())-1
        self._scheduled: Dict[int, Dict[int, dict]] = defaultdict(dict)
        self._on_log_level = on_log_level
        self._no_count = no_count

    async def load_all(self):
        self._query = functools.partial(self.client.query, scope=self.scope)
        assert self.collector_key, 'run init before load_all()'
        root_id, root = await self._query("""//ti
            [.root.id(), .root.wrap("_ContainerSvc")];
        """)
        await self._on_container(root_id, root)

    def _get_work(self):
        now = int(time.time())
        if now <= self._last:
            logging.warning('now before or equal to last; '
                            'maybe the clock time has changed?')
            return {}
        work = defaultdict(list)
        for (container_id, asset_id), checks in self._scheduled.items():
            for check_id, (check_key, config) in checks.items():
                interval = config['_interval']
                diff = now - self._last
                part = (asset_id % interval + now) % interval
                if part < diff:
                    work[check_key].append(Asset(
                        container_id,
                        asset_id,
                        check_id,
                        config))
        self._last = now
        return work

    async def _load(self, container_id: int):
        container = await self._query("""//ti
            Container(id).wrap("_ContainerSvc");
        """, id=container_id)
        await self._on_container(container_id, container)

    async def _on_container(self, container_id: int, container: dict):
        assets = container['assets']
        children = container['children']
        for (asset_id, services) in assets:
            if not services:
                continue
            key = (container_id, asset_id)
            for (collector_key, svc_config, checks) in services:
                if collector_key != self.collector_key:
                    continue
                for check_id, check_key, interval, chk_config in checks:
                    config = {
                        '_interval': interval,
                        **(svc_config or {}),  # can be empty
                        **(chk_config or {}),  # can be empty
                    }
                    self._scheduled[key][check_id] = (check_key, config)

        for cid in children:
            await self._load(cid)

    async def _send_to_hub(self, asset: Asset, result: Optional[dict],
                           error: Optional[dict], ts: float):
        if error:
            logging.error(error)
        path = asset.asset_id, asset.check_id
        check_data = {
            'result': result,
            'error': error,
            'framework': {
                'duration': time.time() - ts,
                'timestamp': int(ts),
                'no_count': self._no_count,
            }
        }
        try:
            await hub.send_check_data(path, check_data)
        except Exception as e:
            msg = str(e) or type(e).__name__
            logging.error(f'Failed to send data to hub: {msg}; {asset}')
        else:
            logging.debug(f'successfully send data to hub; {asset}')

    async def _run_multi(self, check: CheckBaseMulti, assets: List[Asset]):
        ts = time.time()
        try:
            results = await check.run(ts, assets)
        except CheckException as e:
            error = e.to_dict()
            results = [(None, error)] * len(assets)
        except Exception as e:
            msg = str(e) or type(e).__name__
            error = CheckException(msg).to_dict()
            results = [(None, error)] * len(assets)

        for asset, (result, error) in zip(assets, results):
            await self._send_to_hub(asset, result, error, ts)
            await asyncio.sleep(HUB_REQ_SLEEP)

    async def _run(self, check: CheckBase, asset: Asset):
        ts = time.time()
        try:
            result, error = await check.run(ts, asset)
        except CheckException as e:
            result, error = None, e.to_dict()
        except Exception as e:
            msg = str(e) or type(e).__name__
            result, error = None, CheckException(msg).to_dict()

        await self._send_to_hub(asset, result, error, ts)

    async def run_loop(self):
        while True:
            work = self._get_work()
            total = len(self._scheduled)
            log_msg = f'Work: {len(work)} item(s), total: {total}'
            if work:
                logging.info(log_msg)
            else:
                logging.debug(log_msg)
            for check_key, assets in work.items():
                check = self._checks.get(check_key)
                if check is None:
                    logging.warning(f'Check {check_key} not implemented')
                    continue

                if issubclass(check, CheckBaseMulti):
                    asyncio.ensure_future(self._run_multi(check, assets))
                else:
                    for asset in assets:
                        asyncio.ensure_future(self._run(check, asset))
            for _ in range(SLEEP_TIME):
                await asyncio.sleep(1)

    @event('set-log-level')
    def on_set_log_level(self, log_level: str):
        self._on_log_level(log_level)

    @event('upsert-asset')
    def on_upsert_asset(self, container_id: int,
                        service_data: Tuple[int, tuple]):
        logging.debug('on upsert asset')
        asset_id, services = service_data
        self._scheduled.pop(asset_id, None)
        key = (container_id, asset_id)
        self._scheduled.pop(key, None)

        for (collector_key, svc_config, checks) in services:
            if collector_key != self.collector_key:
                continue

            for check_id, check_key, interval, chk_config in checks:
                config = {
                    '_interval': interval,
                    **(svc_config or {}),  # can be empty
                    **(chk_config or {}),  # can be empty
                }
                self._scheduled[key][check_id] = (check_key, config)

    @event('unset-assets')
    def on_unset_assets(self, container_id: int, asset_ids: Tuple[int]):
        logging.debug('on unset assets')
        for asset_id in asset_ids:
            key = (container_id, asset_id)
            self._scheduled.pop(key, None)
