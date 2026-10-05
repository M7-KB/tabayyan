"""Real HTTPResponse parsing over a deterministic, slow synthetic TLS socket."""

import socket
import ssl

import pytest

from api.source_http import BoundedSourceHTTP, SourceUnavailable


def install_drip(
    monkeypatch, *, header_delay=0, body_delay=0, connection_close=False, stage_delays=None
):
    clock = [0.0]
    stage_delays = stage_delays or {}
    body = b'{"ok":true}'
    header = (
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 11\r\n"
        + (b"Connection: close\r\n" if connection_close else b"")
        + b"\r\n"
    )

    class DripSocket:
        def __init__(self):
            self.pos = 0
            self.timeout = None
            self.timeouts = []
            self.closed = False

        def settimeout(self, timeout):
            self.timeout = timeout
            self.timeouts.append(timeout)

        def sendall(self, data):
            advance("send", self.timeout)

        def recv_into(self, target):
            assert not self.closed
            wire = header + body
            if self.pos == len(wire):
                return 0
            delay = header_delay if self.pos < len(header) else body_delay
            if delay >= self.timeout:
                clock[0] += self.timeout
                raise socket.timeout
            clock[0] += delay
            target[0] = wire[self.pos]
            self.pos += 1
            return 1

        def close(self):
            self.closed = True

    sock = DripSocket()

    def advance(stage, timeout):
        delay = stage_delays.get(stage, 0)
        if delay >= timeout:
            clock[0] += timeout
            raise socket.timeout
        clock[0] += delay

    context = ssl.create_default_context()

    def wrap_socket(raw, server_hostname):
        assert server_hostname == "hadeethenc.com"
        advance("tls", raw.timeout)
        return raw

    monkeypatch.setattr(context, "wrap_socket", wrap_socket)

    monkeypatch.setattr("api.source_http.time.monotonic", lambda: clock[0])
    monkeypatch.setattr(
        "api.source_http.socket.getaddrinfo",
        lambda *a, **k: [(None, None, None, None, ("8.8.8.8", 443))],
    )

    def connect(address, timeout):
        assert address == ("8.8.8.8", 443)
        advance("connect", timeout)
        return sock

    monkeypatch.setattr("api.source_http.socket.create_connection", connect)
    monkeypatch.setattr("api.source_http.ssl.create_default_context", lambda: context)
    return clock, sock, len(header)


@pytest.mark.parametrize("phase", ["header", "body"])
def test_drip_cannot_extend_deadline_inside_httpresponse(monkeypatch, phase):
    clock, sock, header_size = install_drip(
        monkeypatch,
        header_delay=9 if phase == "header" else 0,
        body_delay=9 if phase == "body" else 0,
    )
    with pytest.raises(SourceUnavailable, match="^Source unavailable$"):
        BoundedSourceHTTP().get("hadeethenc.com", "/api/v1/hadeeths/one/", {})
    assert clock[0] == 10
    assert sock.pos == (1 if phase == "header" else header_size + 1)
    assert sock.timeouts[-1] == 1
    assert sock.closed


@pytest.mark.parametrize("connection_close", [False, True])
def test_near_deadline_body_succeeds_and_releases_socket(monkeypatch, connection_close):
    clock, sock, _ = install_drip(monkeypatch, body_delay=0.9, connection_close=connection_close)
    assert BoundedSourceHTTP().get("hadeethenc.com", "/api/v1/hadeeths/one/", {}) == {"ok": True}
    assert clock[0] == pytest.approx(9.9)
    assert sock.closed
    assert sock.timeouts[-1] == pytest.approx(1.0)


def test_dns_budget_exhaustion_prevents_connect(monkeypatch):
    clock, sock, _ = install_drip(monkeypatch)

    def resolve(*args, **kwargs):
        clock[0] = 11
        return [(None, None, None, None, ("8.8.8.8", 443))]

    monkeypatch.setattr("api.source_http.socket.getaddrinfo", resolve)
    with pytest.raises(SourceUnavailable):
        BoundedSourceHTTP().get("hadeethenc.com", "/api/v1/hadeeths/one/", {})
    assert sock.timeouts == []


@pytest.mark.parametrize("stage", ["connect", "tls", "send"])
def test_prior_socket_stages_consume_body_budget(monkeypatch, stage):
    clock, sock, header_size = install_drip(monkeypatch, body_delay=9, stage_delays={stage: 6})
    with pytest.raises(SourceUnavailable):
        BoundedSourceHTTP().get("hadeethenc.com", "/api/v1/hadeeths/one/", {})
    assert clock[0] == 10
    assert sock.pos == header_size
    assert sock.timeouts[-1] == 4
    assert sock.closed


@pytest.mark.parametrize("stage", ["connect", "tls", "send"])
def test_socket_stage_timeout_fails_closed(monkeypatch, stage):
    clock, sock, _ = install_drip(monkeypatch, stage_delays={stage: 11})
    with pytest.raises(SourceUnavailable, match="^Source unavailable$"):
        BoundedSourceHTTP().get("hadeethenc.com", "/api/v1/hadeeths/one/", {})
    assert clock[0] == 10
    assert sock.pos == 0
    assert sock.closed is (stage != "connect")
