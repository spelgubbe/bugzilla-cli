import os
import re
import httpx
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

_BASE_URL = os.environ.get("BUGZILLA_BASE_URL", "").rstrip("/")
_API_KEY = os.environ.get("BUGZILLA_API_KEY", "")
_USER = os.environ.get("BUGZILLA_USER", "")


def _check_config():
    if not _BASE_URL or not _API_KEY:
        raise RuntimeError(
            "BUGZILLA_BASE_URL and BUGZILLA_API_KEY must be set in .env or environment"
        )


def _get(path: str, params: dict = None) -> dict:
    _check_config()
    p = {"api_key": _API_KEY}
    if params:
        p.update(params)
    url = f"{_BASE_URL}/rest{path}"
    r = httpx.get(url, params=p, timeout=30)
    if not r.is_success:
        _raise(r)
    return r.json()


def _post(path: str, body: dict) -> dict:
    _check_config()
    url = f"{_BASE_URL}/rest{path}"
    r = httpx.post(url, json={**body, "api_key": _API_KEY}, timeout=30)
    if not r.is_success:
        _raise(r)
    return r.json()


def get_thread(bug_id: int) -> dict:
    bug = _get(f"/bug/{bug_id}")["bugs"][0]
    comments_raw = _get(f"/bug/{bug_id}/comment")["bugs"][str(bug_id)]["comments"]
    comments = [
        {
            "count": i,
            "creator": c["creator"],
            "creation_time": c["creation_time"],
            "text": c["text"],
            "is_description": i == 0,
        }
        for i, c in enumerate(comments_raw)
    ]
    return {
        "id": bug["id"],
        "summary": bug["summary"],
        "product": bug["product"],
        "component": bug["component"],
        "status": bug["status"],
        "resolution": bug.get("resolution", ""),
        "assigned_to": bug["assigned_to"],
        "priority": bug.get("priority", ""),
        "severity": bug.get("severity", ""),
        "creation_time": bug["creation_time"],
        "last_change_time": bug["last_change_time"],
        "comments": comments,
    }


def post_comment(bug_id: int, text: str) -> int:
    result = _post(f"/bug/{bug_id}/comment", {"comment": text})
    return result["id"]


def resolve_me(value: str) -> str:
    if value != "me":
        return value
    if not _USER:
        raise RuntimeError(
            "'me' requires BUGZILLA_USER to be set in .env or environment"
        )
    return _USER


def _raise(r: httpx.Response):
    try:
        detail = r.json().get("message") or r.text
    except Exception:
        detail = r.text
    raise RuntimeError(f"HTTP {r.status_code}: {detail}")


def _put(path: str, body: dict) -> dict:
    _check_config()
    url = f"{_BASE_URL}/rest{path}"
    r = httpx.put(url, json={**body, "api_key": _API_KEY}, timeout=30)
    if not r.is_success:
        _raise(r)
    return r.json()


def update_bug(
    bug_id: int,
    status: str = None,
    resolution: str = None,
    priority: str = None,
    severity: str = None,
    assigned_to: str = None,
    product: str = None,
    component: str = None,
    target_milestone: str = None,
    cc_add: tuple = (),
    cc_remove: tuple = (),
    comment: str = None,
) -> dict:
    body = {}
    if status:
        body["status"] = status
    if resolution:
        body["resolution"] = resolution
    if priority:
        body["priority"] = priority
    if severity:
        body["severity"] = severity
    if assigned_to:
        body["assigned_to"] = resolve_me(assigned_to)
    if product:
        body["product"] = product
    if component:
        body["component"] = component
    if target_milestone:
        body["target_milestone"] = target_milestone
    if cc_add or cc_remove:
        body["cc"] = {
            "add": [resolve_me(u) for u in cc_add],
            "remove": [resolve_me(u) for u in cc_remove],
        }
    if comment:
        body["comment"] = {"body": comment}
    return _put(f"/bug/{bug_id}", body)


def parse_since(since: str) -> str:
    """Parse a relative or absolute --since value to an ISO datetime string."""
    m = re.match(r'^(\d+)([hdw])$', since.lower())
    if m:
        n, unit = int(m.group(1)), m.group(2)
        delta = {'h': timedelta(hours=n), 'd': timedelta(days=n), 'w': timedelta(weeks=n)}[unit]
        dt = datetime.now(timezone.utc) - delta
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        dt = datetime.strptime(since, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise ValueError(f"Invalid --since value: {since!r}. Use e.g. '24h', '2d', '1w', or 'YYYY-MM-DD'")


def get_activity(since_dt: str, product: str = None, component: str = None, limit: int = 0) -> list[dict]:
    params = [
        ("f1", "delta_ts"), ("o1", "greaterthan"), ("v1", since_dt),
        ("order", "changeddate DESC"),
        ("api_key", _API_KEY),
    ]
    if limit:
        params.append(("limit", limit))
    if product:
        params.append(("product", product))
    if component:
        params.append(("component", component))

    _check_config()
    url = f"{_BASE_URL}/rest/bug"
    r = httpx.get(url, params=params, timeout=30)
    r.raise_for_status()
    bugs = r.json()["bugs"]

    results = []
    for bug in bugs:
        comments_raw = _get(f"/bug/{bug['id']}/comment")["bugs"][str(bug['id'])]["comments"]
        recent = [c for c in comments_raw if c["creation_time"] >= since_dt]
        if recent:
            results.append({"bug": bug, "comments": recent})
    results.sort(key=lambda i: i["comments"][-1]["creation_time"], reverse=True)
    return results


def search_bugs(
    assigned_to: str = None,
    reporter: str = None,
    cc: str = None,
    product: str = None,
    component: str = None,
    status: tuple = (),
    priority: tuple = (),
    severity: tuple = (),
    target_milestone: str = None,
    text: str = None,
    mentions: str = None,
    changed_before: str = None,
    changed_after: str = None,
    limit: int = 0,
) -> list[dict]:
    params = {"limit": limit}
    if assigned_to:
        params["assigned_to"] = resolve_me(assigned_to)
    if reporter:
        params["reporter"] = resolve_me(reporter)
    if cc:
        params["cc"] = resolve_me(cc)
    if product:
        params["product"] = product
    if component:
        params["component"] = component
    if status:
        params["status"] = list(status)
    if priority:
        params["priority"] = list(priority)
    if severity:
        params["severity"] = list(severity)
    if target_milestone:
        params["target_milestone"] = target_milestone
    if text:
        params["quicksearch"] = text

    # httpx needs lists sent as repeated params, not JSON arrays
    flat: list[tuple] = []
    for k, v in params.items():
        if isinstance(v, list):
            for item in v:
                flat.append((k, item))
        else:
            flat.append((k, v))

    # Boolean chart syntax for comment text and date range filtering
    chart = 1
    if mentions:
        flat += [("f" + str(chart), "longdesc"), ("o" + str(chart), "substring"), ("v" + str(chart), mentions)]
        chart += 1
    if changed_before:
        flat += [("f" + str(chart), "delta_ts"), ("o" + str(chart), "lessthan"), ("v" + str(chart), changed_before)]
        chart += 1
    if changed_after:
        flat += [("f" + str(chart), "delta_ts"), ("o" + str(chart), "greaterthan"), ("v" + str(chart), changed_after)]
        chart += 1

    flat.append(("api_key", _API_KEY))

    _check_config()
    url = f"{_BASE_URL}/rest/bug"
    r = httpx.get(url, params=flat, timeout=30)
    r.raise_for_status()
    return r.json()["bugs"]
