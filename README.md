[![CI](https://github.com/infrasonar/python-libservice/workflows/CI/badge.svg)](https://github.com/infrasonar/python-libservice/actions)
[![Release Version](https://img.shields.io/github/release/infrasonar/python-libservice)](https://github.com/infrasonar/python-libservice/releases)

# Python library for building InfraSonar Services

This library is created for building [InfraSonar](https://infrasonar.com) services.

## Environment variable

You might want to implement configuration which applies for all assets in all containers, but still don't want to hard-code this setting in your check.
Think for example about a API URL which is always the same, except maybe for a development environment.

The following environment variable are required for a service to work and are always set by InfraSonar:

Environment variable | Default                      | Description
-------------------- | ---------------------------- | ----------------
`THINGSDB_HOSTLIST`  | `thingsdb:9200`              | ThingsDB host list.
`THINGSDB_TOKEN`     | _empty_                      | Token for authentication **(required)**.
`THINGSDB_SCOPE`     | `//data`                     | Collection scope for data.
`HUB_HOST`           | `hub`                        | Hub host
`HUB_PORT`           | `8700`                       | Hub port
`SLEEP_TIME`         | `2`                          | Sleep time in seconds in each iteration.
`LOG_LEVEL`          | `warning`                    | Log level _(error, warning, info, debug)_.
`LOG_COLORIZED`      | `0`                          | Either 0 (=disabled) or 1 (=enabled).
`LOG_FMT`            | `%y%m...`                    | Default format is `%y%m%d %H:%M:%S`.
`DRY_RUN`            | _empty_                      | If enabled, result data will be printed to stdout instead of send to the hub.

## Usage

```python
from asyncio import AbstractEventLoop
from typing import Tuple, Optional
from libservice import start, Asset, CheckBase


class MyCheck(CheckBase):
    # Use CheckBaseMulti if you want to perform checks for multiple assets
    # combined. Sometimes this can be useful as you might be able to combine
    # multiple assets in a single request.
    key = 'my_check'

    @classmethod
    async def run(cls, ts: float, asset: Asset) -> Tuple[
            Optional[dict], Optional[dict]]:
        # Return with the state and optionally an error dict which can be
        # created using CheckException(my_error_message).to_dict().
        # Alternatively, you can rase a CheckException. The return error is
        # especially useful with CheckBaseMulti where only a single asset might
        # fail or to return an error together with the result.
        # For example:
        #
        #   return state, CheckException('Incomplete result').to_dict()
        #
        return {
          'my_type': [
            {'name': 'my_item'}
          ]
        }, None


def start_func(loop: AbstractEventLoop):
    pass  # optional init function

def close_func(loop: AbstractEventLoop):
    pass  # optional close function


if __name__ == '__main__':
    start(
      collector_key='my_server',
      version='0.1.0',
      checks=(MyCheck, ),
      start_func=start_func,
      close_func=close_func,
      no_count=False)  # When True, the check(s) do not count (counter + lastseen)

```

## ASCII item names

InfraSonar requires each item to have a unique _name_ property. The value for _name_ must be a _string_ with ASCII compatible character.
When your _name_ is not guaranteed to be ASCII compatible, the following code replaces the incompatible characters with question marks (`?`):

```python
name = name.encode('ascii', errors='replace').decode()
```

## Check is an asset Id is scheduled

In some cases, the dmarc service as an example, you might want to check if an asset Id is scheduled and ask for the container Id.
As the Asset() instance is only available during the check process, you need to verify this in a different way.

```python
from libservice.serviceroom import service_room

container_id = service_room.get_container_id(asset_id)
if container_id is None:
    # missing asset ID
    ...
```
