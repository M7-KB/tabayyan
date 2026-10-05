"""Bounded HTTPS reads pinned to a public address on a fixed source host."""

import http.client
import ipaddress
import socket
import ssl
import time
from typing import Protocol
from urllib.parse import urlencode

from corpus.validate import _decode


class SourceUnavailable(ValueError):
    """Safe fixed error without URLs, source text or response diagnostics."""

    def __init__(self, status: int | None = None):
        super().__init__("Source unavailable")
        self.status = status


class JsonSource(Protocol):
    def get(self, host: str, path: str, params: dict[str, str]) -> object: ...


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        raw = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


class BoundedSourceHTTP:
    HOSTS = frozenset({"hadeethenc.com", "dorar.net"})
    MAX_BYTES = 256 * 1024
    TIMEOUT = 10

    def get(self, host: str, path: str, params: dict[str, str]) -> object:
        if host not in self.HOSTS or path not in {"/api/v1/hadeeths/one/", "/dorar_api.json"}:
            raise SourceUnavailable()
        connection = None
        started = time.monotonic()
        try:
            addresses = {
                row[4][0] for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            }
            if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
                raise ValueError("Non-public source")
            connection = _PinnedHTTPS(host, sorted(addresses)[0], self.TIMEOUT)
            target = path + "?" + urlencode(params)
            connection.request("GET", target, headers={"Accept": "application/json"})
            response = connection.getresponse()
            if response.status != 200:
                raise SourceUnavailable(response.status)
            if response.getheader("Content-Encoding", "identity") != "identity":
                raise ValueError("Unexpected source response")
            if "json" not in response.getheader("Content-Type", "").lower():
                raise ValueError("Unexpected source response")
            data = bytearray()
            while True:
                if time.monotonic() - started >= self.TIMEOUT:
                    raise TimeoutError
                chunk = response.read(min(8192, self.MAX_BYTES + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > self.MAX_BYTES:
                    raise ValueError("Oversize source")
            return _decode(data.decode("utf-8"))
        except SourceUnavailable:
            raise
        except Exception:
            raise SourceUnavailable() from None
        finally:
            if connection is not None:
                connection.close()
