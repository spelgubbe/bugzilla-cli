#!/usr/bin/env python3
import sys
import click
from client import get_thread, post_comment, search_bugs, update_bug, get_activity, parse_since
from render import render_thread, render_search_results, render_activity

# Allow `bug <id>` as a shorthand for `bug show <id>`
if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit():
    sys.argv.insert(1, "show")


@click.group()
def cli():
    """Bugzilla command line interface.

    \b
    View a bug:
      bug <id>

    Post a comment:
      bug comment <id> -m "your text"
    """


@cli.command("show")
@click.argument("bug_id", type=int)
def show_bug(bug_id):
    """Display a bug thread."""
    try:
        thread = get_thread(bug_id)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    output = render_thread(thread)
    if sys.stdout.isatty():
        click.echo_via_pager(output)
    else:
        click.echo(output)


@cli.command("comment")
@click.argument("bug_id", type=int)
@click.option("-m", "--message", default=None, help="Comment text (opens editor if omitted)")
def add_comment(bug_id, message):
    """Post a comment on a bug."""
    if not message:
        message = click.edit()
        if not message or not message.strip():
            click.echo("Aborted: empty message.", err=True)
            sys.exit(1)
    try:
        comment_id = post_comment(bug_id, message)
        click.echo(f"Comment {comment_id} posted on bug {bug_id}.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("search")
@click.option("--assigned-to", default=None, help="Assignee email (or 'me')")
@click.option("--reporter", default=None, help="Reporter email (or 'me')")
@click.option("--cc", default=None, help="CC email (or 'me')")
@click.option("--product", default=None, help="Product name")
@click.option("--component", default=None, help="Component name")
@click.option("--status", multiple=True, help="Status (repeatable, e.g. --status NEW --status ASSIGNED)")
@click.option("--priority", multiple=True, help="Priority (repeatable, e.g. --priority P1 --priority P2)")
@click.option("--severity", multiple=True, help="Severity (repeatable)")
@click.option("--milestone", default=None, help="Target milestone")
@click.option("--text", default=None, help="Free-text search (quicksearch)")
@click.option("--mentions", default=None, help="Word or phrase appearing in any comment or description")
@click.option("--since", default=None, metavar="DATE", help="Bugs active after this date (YYYY-MM-DD)")
@click.option("--until", default=None, metavar="DATE", help="Bugs not touched after this date (YYYY-MM-DD)")
@click.option("--limit", default=0, show_default=True, help="Max results (0 = no limit)")
@click.option("--format", "fmt", default="table", show_default=True,
              type=click.Choice(["table", "ids", "json"], case_sensitive=False),
              help="Output format")
def search(assigned_to, reporter, cc, product, component, status, priority, severity, milestone, text, mentions, since, until, limit, fmt):
    """Search for bugs."""
    try:
        bugs = search_bugs(
            assigned_to=assigned_to,
            reporter=reporter,
            cc=cc,
            product=product,
            component=component,
            status=status,
            priority=priority,
            severity=severity,
            target_milestone=milestone,
            text=text,
            mentions=mentions,
            changed_after=since,
            changed_before=until,
            limit=limit,
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    click.echo(render_search_results(bugs, fmt=fmt))


@cli.command("activity")
@click.option("--since", default="24h", show_default=True, metavar="TIMESPEC",
              help="Show comments since this point (e.g. 24h, 2d, 1w, or YYYY-MM-DD)")
@click.option("--product", default=None, help="Filter by product")
@click.option("--component", default=None, help="Filter by component")
@click.option("--limit", default=0, show_default=True, help="Max bugs to scan (0 = no limit)")
@click.option("--format", "fmt", default="table", show_default=True,
              type=click.Choice(["table", "json"], case_sensitive=False),
              help="Output format")
@click.option("--output", "outfile", default=None, metavar="FILE",
              help="Write output to a file instead of stdout")
def activity(since, product, component, limit, fmt, outfile):
    """Show recent comments across the tracker."""
    try:
        since_dt = parse_since(since)
        items = get_activity(since_dt, product=product, component=component, limit=limit)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    output = render_activity(items, since_dt, fmt=fmt)
    if outfile:
        with open(outfile, "w") as f:
            f.write(output + "\n")
        click.echo(f"Written to {outfile}", err=True)
    elif sys.stdout.isatty():
        click.echo_via_pager(output)
    else:
        click.echo(output)


@cli.command("edit")
@click.argument("bug_id", type=int)
@click.option("--status", default=None, help="New status (e.g. ASSIGNED, RESOLVED)")
@click.option("--resolution", default=None, help="Resolution (e.g. FIXED, WONTFIX) — required when setting status to RESOLVED")
@click.option("--priority", default=None, help="Priority (e.g. P1, P2)")
@click.option("--severity", default=None, help="Severity (e.g. critical, major, normal)")
@click.option("--assigned-to", default=None, help="Assignee email (or 'me')")
@click.option("--product", default=None, help="Product name")
@click.option("--component", default=None, help="Component name")
@click.option("--milestone", default=None, help="Target milestone")
@click.option("--cc", multiple=True, help="Add to CC (repeatable, supports 'me')")
@click.option("--cc-remove", multiple=True, help="Remove from CC (repeatable, supports 'me')")
@click.option("-m", "--comment", default=None, help="Comment to attach alongside the edit")
def edit_bug(bug_id, status, resolution, priority, severity, assigned_to, product, component, milestone, cc, cc_remove, comment):
    """Edit bug fields."""
    if not any([status, resolution, priority, severity, assigned_to, product, component, milestone, cc, cc_remove, comment]):
        click.echo("No fields specified. Use --help to see available options.", err=True)
        sys.exit(1)
    try:
        update_bug(
            bug_id,
            status=status,
            resolution=resolution,
            priority=priority,
            severity=severity,
            assigned_to=assigned_to,
            product=product,
            component=component,
            target_milestone=milestone,
            cc_add=cc,
            cc_remove=cc_remove,
            comment=comment,
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    click.echo(f"Bug {bug_id} updated.")


@cli.command("watch")
@click.option("--since", default=None, metavar="TIMESPEC",
              help="Look back on startup (e.g. 15m, 1h). Default: now")
@click.option("--interval", default=120, show_default=True, metavar="SECONDS",
              help="Poll interval in seconds")
@click.option("--product", default=None, help="Filter by product")
@click.option("--component", default=None, help="Filter by component")
def watch_activity(since, interval, product, component):
    """Watch for new comments, polling every INTERVAL seconds."""
    import time
    from datetime import datetime, timezone

    if not sys.stdout.isatty():
        click.echo("Error: 'watch' requires a TTY.", err=True)
        sys.exit(1)

    try:
        last_poll = parse_since(since) if since else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"Watching for activity since {last_poll}. Ctrl+C to stop.\n")

    try:
        while True:
            fetch_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            click.echo("\rpolling...", nl=False)
            try:
                items = get_activity(last_poll, product=product, component=component)
            except Exception as e:
                click.echo(f"\rError: {e}", err=True)
                time.sleep(interval)
                continue

            since_label = last_poll
            last_poll = fetch_start

            if items:
                click.echo("\r            ")  # clear "polling..." line
                click.echo(render_activity(items, since_label))

            time.sleep(interval)
    except KeyboardInterrupt:
        click.echo("\rStopped.")


if __name__ == "__main__":
    cli()
