"""Direct, bounded MCP reads; only publisher-owned text becomes request evidence."""

import ipaddress
import json
import queue
import re
import socket
import threading
import time
from typing import Protocol

from api.gatekeeper import SourceRequest, allowed_url
from api.source_http import SourceUnavailable, _PinnedHTTPS, _remaining
from corpus.validate import _decode

HOST = "mcp.islamiccontent.org"
ENDPOINT = "https://mcp.islamiccontent.org/mcp"


def _resolve(deadline):
    # DNS can block independently of socket timeouts. Only the fixed public host
    # enters the worker; no query or source response survives the request there.
    result = queue.Queue(maxsize=1)

    def resolve():
        try:
            result.put(socket.getaddrinfo(HOST, 443, type=socket.SOCK_STREAM))
        except Exception:
            result.put(None)

    threading.Thread(target=resolve, daemon=True).start()
    rows = result.get(timeout=_remaining(deadline))
    if rows is None:
        raise SourceUnavailable()
    return {r[4][0] for r in rows}


class MCPTransport(Protocol):
    def call(self, name: str, arguments: dict, *, deadline: float) -> dict: ...


def rpc_result(data: bytes, content_type: str, request_id: int) -> dict:
    """Accept one matching RPC response, never instructions or free text."""
    text = data.decode("utf-8")
    if content_type.split(";", 1)[0] == "text/event-stream":
        messages = []
        for event in text.replace("\r\n", "\n").split("\n\n"):
            lines = [
                line[5:].lstrip(" ") for line in event.splitlines() if line.startswith("data:")
            ]
            if lines:
                messages.append(_decode("\n".join(lines)))
        if len(messages) != 1:
            raise SourceUnavailable()
        body = messages[0]
    elif content_type.split(";", 1)[0] == "application/json":
        body = _decode(text)
    else:
        raise SourceUnavailable()
    if (
        not isinstance(body, dict)
        or body.get("jsonrpc") != "2.0"
        or type(body.get("id")) is not int
        or body["id"] != request_id
        or "error" in body
        or not isinstance(body.get("result"), dict)
        or body["result"].get("isError", False) is not False
    ):
        raise SourceUnavailable()
    return body["result"]


class DirectMCP:
    MAX_BYTES = 256 * 1024
    TOOLS = frozenset({"search", "get_library_item", "get_quran_verses"})

    def call(self, name: str, arguments: dict, *, deadline: float) -> dict:
        if name not in self.TOOLS:
            raise SourceUnavailable()
        connection = response = None
        try:
            _remaining(deadline)
            addresses = _resolve(deadline)
            if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
                raise SourceUnavailable()
            connection = _PinnedHTTPS(
                HOST, sorted(addresses)[0], _remaining(deadline), deadline=deadline
            )
            body = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                }
            ).encode()
            connection.request(
                "POST",
                "/mcp",
                body=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "MCP-Protocol-Version": "2025-03-26",
                },
            )
            response = connection.getresponse()
            if response.status != 200:
                raise SourceUnavailable(response.status)
            if response.getheader("Content-Encoding", "identity") != "identity":
                raise SourceUnavailable()
            data = bytearray()
            while True:
                _remaining(deadline)
                chunk = response.read(min(8192, self.MAX_BYTES + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > self.MAX_BYTES:
                    raise SourceUnavailable()
            _remaining(deadline)
            return rpc_result(bytes(data), response.getheader("Content-Type", ""), 1)
        except Exception:
            raise SourceUnavailable() from None
        finally:
            if response is not None:
                response.close()
            if connection is not None:
                connection.close()


def _blocks(result: dict) -> list[str]:
    content = result.get("content")
    if result.get("isError", False) is not False or not isinstance(content, list):
        raise SourceUnavailable()
    if not 1 <= len(content) <= 5 or any(
        not isinstance(b, dict) or b.get("type") != "text" or not isinstance(b.get("text"), str)
        for b in content
    ):
        raise SourceUnavailable()
    return [b["text"] for b in content]


def _publisher_block(result: dict, tag: str, url: str) -> str:
    texts = _blocks(result)
    matches = []
    for text in texts:
        if text.splitlines().count("Source: " + url) != 1:
            continue
        pattern = rf"\[{tag}\][^\n]*\n(.*?)\n\[/{tag}\]"
        sections = re.findall(pattern, text, flags=re.DOTALL)
        if len(sections) == 1 and text.count(f"[{tag}]") == 1:
            matches.extend(sections)
    if len(matches) != 1 or not matches[0].strip() or len(matches[0]) > 12000:
        raise SourceUnavailable()
    return matches[0]


class IslamicContentConnector:
    """Hosted MCP coverage: library and Quran only; absent platforms abstain."""

    def __init__(self, transport: MCPTransport | None = None):
        self.transport = transport or DirectMCP()

    def discover(self, query: str, request: SourceRequest) -> list:
        if not isinstance(query, str) or not query.strip() or len(query) > 12000:
            return []
        deadline = time.monotonic() + 10
        records = []
        try:
            result = self.transport.call(
                "search",
                {
                    "query": query,
                    "sources": ["library"],
                    "language": "ar",
                    "limit": 2,
                },
                deadline=deadline,
            )
            blocks = _blocks(result)
            # Search metadata locates items; it never authorizes a quote.
            search = _decode(blocks[0])
            rows = search.get("results") if isinstance(search, dict) else None
            if not isinstance(rows, list) or len(rows) > 2:
                return []
            seen = set()
            for row in rows:
                if not isinstance(row, dict):
                    continue
                match = re.fullmatch(r"library:([1-9][0-9]{0,8}):ar", row.get("id", ""))
                if match is None or match[1] in seen:
                    continue
                item_id = match[1]
                seen.add(item_id)
                url = f"https://islamcontent.com/ar/content/{item_id}"
                if row.get("url") != url or not allowed_url(url, "islamcontent.com"):
                    continue
                detail = self.transport.call(
                    "get_library_item",
                    {
                        "id": item_id,
                        "language": "ar",
                    },
                    deadline=deadline,
                )
                text = _publisher_block(detail, "COMMENTARY", url)
                if not re.search(r"[\u0621-\u064a]", text):
                    continue
                records.append(
                    {
                        "source_id": "islamhouse",
                        "domain": "faq",
                        "record_ref": item_id,
                        "source_url": url,
                        "text_ar": text,
                        "ref": {"item_id": item_id},
                    }
                )
            _remaining(deadline)
        except Exception:
            # An incomplete/outage batch cannot masquerade as complete evidence.
            return []
        return [request.receive(r) for r in records]

    def verse(self, surah: int, ayah: int, request: SourceRequest):
        if (
            type(surah) is not int
            or type(ayah) is not int
            or not 1 <= surah <= 114
            or not 1 <= ayah <= 286
        ):
            return None
        url = f"https://islamenc.com/en/quran/{surah}/{ayah}"
        try:
            result = self.transport.call(
                "get_quran_verses",
                {
                    "surah": surah,
                    "ayah": ayah,
                    "through": ayah,
                    "language": "en",
                },
                deadline=time.monotonic() + 10,
            )
            text = _publisher_block(result, "EXACT", url)
            lines = text.splitlines()
            if len(lines) != 3 or lines[0] != f"[{surah}:{ayah}]":
                return None
            if not re.search(r"[\u0621-\u064a]", lines[1]) or not lines[2].strip():
                return None
            # Both lines are same-response source bytes, kept outside generated prose.
            return request.receive(
                {
                    "source_id": "quranenc",
                    "domain": "quran_translation",
                    "record_ref": f"{surah}:{ayah}:en",
                    "source_url": url,
                    "text_ar": "\n".join(lines[1:]),
                    "ref": {"surah": surah, "ayah": ayah},
                }
            )
        except Exception:
            return None
