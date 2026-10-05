"""One metadata-only Dorar JSON reachability probe, run in a Render shell."""

import json
import os

from api.source_http import BoundedSourceHTTP, SourceUnavailable


def probe(http=None):
    if os.environ.get("RENDER") != "true":
        return {"environment": "not_render", "attempted": False, "json_response": False}
    try:
        result = (http or BoundedSourceHTTP()).get("dorar.net", "/dorar_api.json", {"skey": "test"})
        return {
            "environment": "render",
            "attempted": True,
            "json_response": isinstance(result, dict),
            "http_status": 200,
        }
    except SourceUnavailable as exc:
        return {
            "environment": "render",
            "attempted": True,
            "json_response": False,
            "http_status": exc.status,
        }


if __name__ == "__main__":
    print(json.dumps(probe()))
