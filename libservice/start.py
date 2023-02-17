import asyncio
import logging
import signal
import os
from asyncio import AbstractEventLoop
from typing import Tuple, Union, Optional, Callable
from .check import CheckBase, CheckBaseMulti
from .serviceroom import ServiceRoom
from .hub import hub
from .logger import setup_logger, set_log_level
from .ticonn import ticonn


HUB_HOST = os.getenv('HUB_HOST', 'hub')
HUB_PORT = int(os.getenv('HUB_PORT', '8700'))
THINGSDB_HOSTLIST = os.getenv('THINGSDB_HOSTLIST', 'thingsdb:9200')
THINGSDB_TOKEN = os.getenv('THINGSDB_TOKEN')
THINGSDB_SCOPE = os.getenv('THINGSDB_SCOPE', '//data')


async def _setup_ticonn():
    nodes = [
        tuple(node.split(':'))
        for node in THINGSDB_HOSTLIST.replace(';', ',').split(',')]
    token = THINGSDB_TOKEN
    ticonn.set_default_scope(THINGSDB_SCOPE)
    await ticonn.connect_pool(nodes, token)
    logging.info(f'Connected to ThingsDB (ticonn)')


async def _setup_hub_connection():
    logging.info('Connecting to Hub')
    await hub.connect(HUB_HOST, HUB_PORT)


async def _setup_service_room(collector_key, checks):
    service_room = ServiceRoom('.ev_service.id()', THINGSDB_SCOPE)
    service_room.init('platform', checks, set_log_level, False)
    await service_room.join(ticonn)
    await service_room.load_all()
    asyncio.ensure_future(service_room.run_loop())
    logging.info(f'Collection `{THINGSDB_SCOPE}` ready')


def _stop(signame, *args):
    logging.warning(f'Signal \'{signame}\' received, stop service')
    for task in asyncio.all_tasks():
        task.cancel()
    raise Exception


def start(collector_key: str, version: str,
          checks: Tuple[Union[CheckBase, CheckBaseMulti]],
          start_func: Optional[Callable[[AbstractEventLoop], None]] = None,
          close_func: Optional[Callable[[AbstractEventLoop], None]] = None):
    if THINGSDB_TOKEN is None:
        raise Exception('Missing `THINGSDB_TOKEN` environment variable')

    setup_logger()
    logging.warning(f"Starting {collector_key} service v{version}")

    loop = asyncio.get_event_loop()

    if start_func is not None:
        start_func(loop)

    loop.run_until_complete(_setup_ticonn())
    loop.run_until_complete(_setup_hub_connection())
    loop.run_until_complete(_setup_service_room(collector_key, checks))

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        loop.run_forever()
    except Exception:
        loop.run_until_complete(loop.shutdown_asyncgens())

    ticonn.close()
    loop.run_until_complete(ticonn.wait_closed())

    if close_func is not None:
        close_func(loop)

    logging.info('Bye.')
