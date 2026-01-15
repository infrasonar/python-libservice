import socket
import asyncio
import urllib.parse
import ipaddress
import socket


class AddrErr(Exception):
    pass


class PrivateAddrErr(AddrErr):
    pass


class NoIpAddrErr(AddrErr):
    pass


class ResolveAddrErr(AddrErr):
    pass


class InvalidAddrErr(AddrErr):
    pass


def check_ip_address(
        addr: ipaddress.IPv4Address | ipaddress.IPv6Address):
    if addr.is_private:
        raise PrivateAddrErr(f"Error: Private IP address: {addr}")


async def get_dns_info(hostname) -> list[str]:
    loop = asyncio.get_running_loop()
    try:
        results = await loop.getaddrinfo(hostname, None,
                                         family=socket.AF_UNSPEC)
        ip_addresses = []
        for result in results:
            family, _, _, _, sockaddr = result
            address = sockaddr[0]
            if family in (socket.AF_INET, socket.AF_INET6):
                ip_addresses.append(address)

        if not ip_addresses:
            raise NoIpAddrErr(f"Error: No IP address found for '{hostname}'")

        return ip_addresses
    except Exception as e:
        msg = str(e) or type(e).__name__
        raise ResolveAddrErr(f"Error: Unable to resolve '{hostname}': {msg}")


async def addr_check(addr: str):
    if addr.lower().startswith('http://integrations/'):
        return  # The only internal call which is allowed

    try:
        _addr = ipaddress.ip_address(addr)
        check_ip_address(_addr)
        return  # OK
    except ValueError:
        pass

    parsed = urllib.parse.urlparse(addr)
    if parsed.hostname:
        addr = parsed.hostname

    if "/" not in addr:
        ip_addresses = await get_dns_info(addr)

        for ip_address in ip_addresses:
            _addr = ipaddress.ip_address(ip_address)
            check_ip_address(_addr)

        return  # OK

    raise InvalidAddrErr(f"Unknown/Invalid address: '{addr}'")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete
    r(addr_check('https://google.com'))
    r(addr_check('HTTPS://google.com:443/a?b=c'))
    r(addr_check('www.infrasonar.com'))
    r(addr_check('8.8.4.4'))
    r(addr_check('2345:0425:2CA1:0000:0000:0567:5673:23b5'))
    r(addr_check('http://integrations/HaloPSA/scope'))
    r(addr_check('https://api.infrasonar.com/alert/ks/close'))
    r(addr_check('https://hooks.slack.com/services/T53FYV161/B083ZHX84D9/s'))
    r(addr_check('https://nomoa.staging.beech.it/api/alert'))

    for addr in (
        '10.10.10.1',
        '192.168.1.1',
        '::1',
        'localhost',
        'bla bla',
        'FC00::/7',
        'FD00::45:AA:1/7',
        'not.resolvable',
    ):
        try:
            r(addr_check(addr))
        except AddrErr:
            pass
        else:
            raise Exception(f'Exception not raised for addr: {addr}')
