import sys
import textwrap

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_GREEN = "\033[32m"
_RED = "\033[31m"

_USE_COLOR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if not _USE_COLOR:
        return text
    return f"{code}{text}{_RESET}"


def _status_color(status: str) -> str:
    if status in ("RESOLVED", "CLOSED", "VERIFIED"):
        return _c(_GREEN, status)
    if status in ("NEW", "UNCONFIRMED"):
        return _c(_RED, status)
    return _c(_YELLOW, status)


def _fmt_time(iso: str) -> str:
    return iso.replace("T", " ").replace("Z", " UTC") if iso else ""


def render_thread(bug: dict) -> str:
    lines = []

    resolution = f" / {bug['resolution']}" if bug.get("resolution") else ""
    status_str = f"{_status_color(bug['status'])}{_c(_DIM, resolution)}"

    lines.append(_c(_BOLD, f"Bug {bug['id']}: {bug['summary']}"))
    lines.append(_c(_DIM, "─" * 72))
    lines.append(f"  Product   : {bug['product']} / {bug['component']}")
    lines.append(f"  Status    : {status_str}")
    lines.append(f"  Assigned  : {bug['assigned_to']}")
    lines.append(f"  Priority  : {bug['priority']}  Severity: {bug['severity']}")
    lines.append(f"  Created   : {_fmt_time(bug['creation_time'])}")
    lines.append(f"  Modified  : {_fmt_time(bug['last_change_time'])}")
    lines.append("")

    for c in bug["comments"]:
        label = "Description" if c["is_description"] else f"Comment {c['count']}"
        lines.append(
            _c(_BOLD, _c(_CYAN, f"[{label}]"))
            + _c(_DIM, f"  {c['creator']}  {_fmt_time(c['creation_time'])}")
        )
        lines.append(_c(_DIM, "─" * 72))
        for para in c["text"].splitlines():
            wrapped = textwrap.fill(para, width=80) if para.strip() else ""
            lines.append(wrapped)
        lines.append("")

    return "\n".join(lines)


def render_activity(items: list, since_dt: str, fmt: str = "table") -> str:
    if fmt == "json":
        import json
        rows = [
            {
                "bug_id": i["bug"]["id"],
                "summary": i["bug"]["summary"],
                "status": i["bug"]["status"],
                "resolution": i["bug"].get("resolution", ""),
                "product": i["bug"]["product"],
                "component": i["bug"]["component"],
                "comments": [
                    {"creation_time": c["creation_time"], "creator": c["creator"], "text": c["text"]}
                    for c in i["comments"]
                ],
            }
            for i in items
        ]
        return json.dumps(rows, indent=2)

    if not items:
        return _c(_DIM, f"No comments since {since_dt}.")
    lines = []
    total = sum(len(i["comments"]) for i in items)
    lines.append(_c(_DIM, f"{total} comment(s) across {len(items)} bug(s) since {since_dt}\n"))
    for item in items:
        bug = item["bug"]
        resolution = f"/{bug['resolution']}" if bug.get("resolution") else ""
        lines.append(
            _c(_BOLD, _c(_CYAN, f"Bug {bug['id']}"))
            + "  "
            + _status_color(bug["status"]) + _c(_DIM, resolution)
            + "  "
            + _c(_BOLD, bug["summary"])
        )
        lines.append(_c(_DIM, f"  {bug['product']} / {bug['component']}"))
        for c in item["comments"]:
            lines.append(
                "  "
                + _c(_CYAN, _fmt_time(c["creation_time"]))
                + "  "
                + _c(_BOLD, c["creator"])
            )
            for para in c["text"].splitlines():
                wrapped = textwrap.fill(para, width=76, initial_indent="    ", subsequent_indent="    ") if para.strip() else ""
                lines.append(wrapped)
        lines.append("")
    return "\n".join(lines)


def render_search_results(bugs: list, fmt: str = "table") -> str:
    if fmt == "ids":
        return "\n".join(str(b["id"]) for b in bugs)

    if fmt == "json":
        import json
        fields = ["id", "summary", "status", "resolution", "product", "component",
                  "assigned_to", "priority", "severity", "last_change_time"]
        rows = [{f: b.get(f) for f in fields} for b in bugs]
        return json.dumps(rows, indent=2)

    if not bugs:
        return "No bugs found."
    lines = []
    for b in bugs:
        resolution = f"/{b['resolution']}" if b.get("resolution") else ""
        status_plain = f"{b['status']}{resolution}"
        lines.append(
            _c(_CYAN, _c(_BOLD, f"#{b['id']:<7}"))
            + "  "
            + _status_color(b["status"]) + _c(_DIM, resolution)
            + " " * max(2, 16 - len(status_plain))
            + _c(_DIM, f"{b.get('priority', ''):3}")
            + "  "
            + b["summary"]
        )
    lines.append(_c(_DIM, f"\n{len(bugs)} result(s)"))
    return "\n".join(lines)
