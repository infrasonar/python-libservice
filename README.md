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
`THINGSDB_TOKEN`     | _empty_                      | Token for authentication.
`THINGSDB_SCOPE`     | `//data`                     | Collection scope for data.
`HUB_HOST`           | `hub`                        | Hub host
`HUB_PORT`           | `8700`                       | Hub port
`SLEEP_TIME`         | `2`                          | Sleep time in seconds in each iteration.
`LOG_LEVEL`          | `warning`                    | Log level _(error, warning, info, debug)_.
`LOG_COLORIZED`      | `0`                          | Either 0 (=disabled) or 1 (=enabled).
`LOG_FMT`            | `%y%m...`                    | Default format is `%y%m%d %H:%M:%S`.


## Usage

```python
import logging
from libservice.asset import Asset
from libservice.probe import Probe
from libservice.severity import Severity
from libservice.exceptions import (
    CheckException,
    IgnoreResultException,
    IgnoreCheckException,
    IncompleteResultException,
)

__version__ = "0.1.0"


async def my_first_check(asset: Asset, asset_config: dict, check_config: dict):
    """My first check.
    Arguments:
      asset:        Asset contains an id, name and check which should be used
                    for logging;
      asset_config: local configuration for this asset, for example credentials;
      check_config: configuration for this check; contains for example the
                    interval at which the check is running and an address of
                    the asset to probe;
    """
    if "ignore_this_check_iteration":
        # nothing will be send to InfraSonar for this check iteration;
        raise IgnoreResultException()

    if "no_longer_try_this_check":
        # nothing will be send to InfraSonar for this check iteration and the
        # check will not start again until the probe restarts or configuration
        # has been changed;
        raise IgnoreCheckException()

    if "something_has_happened":
        # send a check error to InfraSonar because something has happened which
        # prevents us from building a check result; The default severity for a
        # CheckException is MEDIUM but this can be overwritten;
        raise CheckException("something went wrong", severity=Severity.LOW)

    if "something_unexpected_has_happened":
        # other exceptions will be converted to CheckException, MEDIUM severity
        raise Exception("something went wrong")

    # A check result may have multiple types, items, and/or metrics
    result = {"myType": [{"name": "my item"}]}

    if "result_is_incomplete":
        # optionally, IncompleteResultException can be given another severity;
        # the default severity is LOW.
        raise IncompleteResultException('missing type x', result)

    # Use the asset in logging; this will include asset info and the check key
    logging.info(f"log something; {asset}")

    # Return the check result
    return result


if __name__ == "__main__":
    checks = {
        "myFirstCheck": my_first_check,
    }

    # Initialize the probe with a name, version and checks
    probe = Probe("myProbe", __version__, checks)

    # Start the probe
    probe.start()
```

## ASCII item names

InfraSonar requires each item to have a unique _name_ property. The value for _name_ must be a _string_ with ASCII compatible character.
When your _name_ is not guaranteed to be ASCII compatible, the following code replaces the incompatible characters with question marks (`?`):

```python
name = name.encode('ascii', errors='replace').decode()
```

## Config

When using a `password` or `secret` within a _config_ section, the library
will encrypt the value so it will be unreadable by users. This must not be
regarded as true encryption as the encryption key is publicly available.

Example yaml configuration:

```yaml
exampleProbe:
  config:
    username: alice
    password: secret_password
  assets:
  - id: 123
    config:
      username: bob
      password: "my secret"
  - id: [456, 789]
    config:
      username: charlie
      password: "my other secret"
otherProbe:
  use: exampleProbe  # use the exampleProbe config for this probe
```

## Dry run

Create a yaml file, for example _(test.yaml)_:

```yaml
asset:
  name: "foo.local"
  check: "system"
  config:
    address: "192.168.1.2"
```

Run the probe with the `DRY_RUN` environment variable set the the yaml file above.

```
DRY_RUN=test.yaml python main.py
```

> Note: Optionally an asset _id_ might be given which can by used to find asset configuration in the local asset configuration file. Asset _config_ is also optional.

### Dump to JSON
A dry run writes all log to _stderr_ and only the JSON dump is written to _stdout_. Therefore, writing the output to JSON is easy:
```
DRY_RUN=test.yaml python main.py > dump.json
```
# python-libservice
