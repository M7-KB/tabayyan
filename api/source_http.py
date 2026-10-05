"""Bounded HTTPS reads pinned to a public address on a fixed source host."""

import http.client
import io
import ipaddress
import socket
import ssl
import time
from typing import Protocol
from urllib.parse import urlencode

from api.deadline import request_deadline
from corpus.validate import _decode


class SourceUnavailable(ValueError):
    """Safe fixed error without URLs, source text or response diagnostics."""

    def __init__(self, status: int | None = None):
        super().__init__("Source unavailable")
        self.status = status


class JsonSource(Protocol):
    def get(self, host: str, path: str, params: dict[str, str]) -> object: ...


def _remaining(deadline):
    deadline = min(deadline, request_deadline.get() or float("inf"))
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError
    return remaining


class _DeadlineReader(io.RawIOBase):
    """Apply the remaining budget to every receive, including inside readline/read."""

    def __init__(self, sock, deadline, release):
        super().__init__()
        self.sock = sock
        self.deadline = deadline
        self.release = release

    def readable(self):
        return True

    def readinto(self, buffer):
        self.sock.settimeout(_remaining(self.deadline))
        count = self.sock.recv_into(buffer)
        _remaining(self.deadline)
        return count

    def close(self):
        if not self.closed:
            super().close()
            self.release()


class _DeadlineSocket:
    def __init__(self, sock, deadline):
        self.sock = sock
        self.deadline = deadline
        self.readers = 0
        self.closed = False

    def makefile(self, mode):
        if mode != "rb":
            raise ValueError("Unsupported source stream")
        self.readers += 1
        return io.BufferedReader(_DeadlineReader(self.sock, self.deadline, self._release))

    def _release(self):
        self.readers -= 1
        if self.closed and not self.readers:
            self.sock.close()

    def sendall(self, data):
        self.sock.settimeout(_remaining(self.deadline))
        self.sock.sendall(data)
        _remaining(self.deadline)

    def close(self):
        if not self.closed:
            self.closed = True
            if not self.readers:
                self.sock.close()


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout, *, deadline):
        self.deadline = deadline
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        raw = socket.create_connection((self.address, 443), _remaining(self.deadline))
        try:
            raw.settimeout(_remaining(self.deadline))
            secured = self._context.wrap_socket(raw, server_hostname=self.host)
            self.sock = _DeadlineSocket(secured, self.deadline)
            _remaining(self.deadline)
        except BaseException:
            raw.close()
            raise


class BoundedSourceHTTP:
    HOSTS = frozenset({"hadeethenc.com", "dorar.net"})
    MAX_BYTES = 256 * 1024
    TIMEOUT = 10

    def get(self, host: str, path: str, params: dict[str, str]) -> object:
        paths = {
            "hadeethenc.com": {
                "/api/v1/hadeeths/one/",
                "/api/v1/categories/list/",
                "/api/v1/hadeeths/list/",
            },
            "dorar.net": {"/dorar_api.json"},
        }
        if host not in self.HOSTS or path not in paths[host]:
            raise SourceUnavailable()
        connection = None
        response = None
        started = time.monotonic()
        try:
            addresses = {
                row[4][0] for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            }
            if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
                raise ValueError("Non-public source")
            connection = _PinnedHTTPS(
                host,
                sorted(addresses)[0],
                _remaining(started + self.TIMEOUT),
                deadline=started + self.TIMEOUT,
            )
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
            if response is not None:
                response.close()
            if connection is not None:
                connection.close()
