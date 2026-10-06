"""Read operations against the platform API."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


class PlatformError(Exception):
    pass


def get_json(base_url: str, token: str, path: str, env: str | None, timeout: float):
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.query or parsed.fragment:
        raise PlatformError("Base URL must be an HTTP(S) URL without a query or fragment.")
    if not token.strip():
        raise PlatformError("Set AG_UI_TOKEN with an Okta access token accepted by the platform UI.")
    url = base_url.rstrip("/") + path
    if env:
        url += "?" + urlencode({"env": env})
    request = Request(url, headers={"Authorization": f"Bearer {token.strip()}", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        messages = {
            401: "Authentication failed. Refresh your token.",
            403: "Access denied. Use an Okta token from an authorized platform UI client.",
            404: f"Not found: {path}. Check the workflow name and base URL.",
        }
        raise PlatformError(messages.get(exc.code, f"Platform returned HTTP {exc.code}.")) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise PlatformError("Could not reach the platform. Check the base URL and your network connection.") from exc
    except (ValueError, UnicodeError) as exc:
        raise PlatformError("Platform returned invalid JSON.") from exc
    return payload


def get_workflow(base_url: str, token: str, name: str, env: str | None, timeout: float) -> dict:
    payload = get_json(base_url, token, "/skills/" + quote(name, safe=""), env, timeout)
    if not isinstance(payload, dict) or not isinstance(payload.get("workflow"), dict):
        raise PlatformError("Unexpected response: expected a workflow definition.")
    workflow = payload["workflow"]
    nodes = workflow.get("nodes", [])
    if not isinstance(nodes, list) or any(not isinstance(node, dict) or not isinstance(node.get("id"), str) for node in nodes):
        raise PlatformError("Unexpected response: invalid workflow nodes.")
    if len({node["id"] for node in nodes}) != len(nodes):
        raise PlatformError("Unexpected response: duplicate workflow node IDs.")
    if any(node.get("args") is not None and not isinstance(node["args"], dict) for node in nodes):
        raise PlatformError("Unexpected response: invalid workflow node arguments.")
    return workflow


def list_workflows(base_url: str, token: str, env: str | None, timeout: float) -> list[dict]:
    payload = get_json(base_url, token, "/skills", env, timeout)
    if not isinstance(payload, dict) or not isinstance(payload.get("skills"), list):
        raise PlatformError("Unexpected response: expected a skills array.")
    skills = payload["skills"]
    if any(not isinstance(item, dict) or not isinstance(item.get("name"), str) for item in skills):
        raise PlatformError("Unexpected response: every workflow must have a name.")
    return sorted(skills, key=lambda item: item["name"].casefold())
