# bugzilla-cli

A minimal command line interface for Bugzilla. View bugs, post comments,
search, edit fields, and browse recent activity — all from the terminal.

This project is an unofficial command-line client for Bugzilla. It is not
affiliated with, endorsed by, or sponsored by the Bugzilla project or Mozilla.

It is vibe coded so it may have some bugs.

## Setup

**Linux / macOS**
```bash
./setup.sh
cp .env.example .env
```

**Windows (PowerShell)**
```powershell
.\setup.ps1
copy .env.example .env
```

`.env` contents:

```
BUGZILLA_BASE_URL=https://your-bugzilla-host
BUGZILLA_API_KEY=YOUR_API_KEY_HERE
BUGZILLA_USER=you@example.com
```

`BUGZILLA_USER` is only needed if you use `--assigned-to me` or similar `me` shorthands.

## Usage

### View a bug thread

```bash
python bug.py 12345
```

Prints the bug summary, metadata, and all comments. Output is paged automatically when running in a terminal, and plain text when piped.

### Post a comment

```bash
python bug.py comment 12345 -m "Fixed in commit abc123."
```

Omit `-m` to open your default editor instead.

### Search for bugs

```bash
python bug.py search --assigned-to me --status NEW
python bug.py search --product Firefox --component Networking --status ASSIGNED
python bug.py search --mentions login --since 2026-05-01
python bug.py search --mentions authorization --since 2026-05-01 --until 2026-05-15
python bug.py search --assigned-to me --format json
```

`--mentions` searches the full text of all comments and descriptions. `--since` and `--until` filter by last activity date.

### Edit a bug

```bash
python bug.py edit 12345 --status RESOLVED --resolution FIXED
python bug.py edit 12345 --assigned-to me --priority P1
```

### Recent activity

Show comments posted across the tracker in the last 24 hours:

```bash
python bug.py activity
python bug.py activity --since 2d --product MyProduct
python bug.py activity --format json --output report.json
```

## Global `bug` command

Instead of typing `python bug.py` every time, you can wire up a short `bug`
command. The wrapper calls the `.venv` Python directly, so the virtualenv does
not need to be activated in your shell session.

### Linux / macOS

Create a wrapper script in `~/.local/bin` (which is on `$PATH` by default on
most distributions):

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/bug << 'EOF'
#!/usr/bin/env bash
exec /path/to/bugzilla-cli/.venv/bin/python /path/to/bugzilla-cli/bug.py "$@"
EOF
chmod +x ~/.local/bin/bug
```

Replace `/path/to/bugzilla-cli` with the absolute path to your clone.

### Windows

**PowerShell** — add a function to your PowerShell profile (`$PROFILE`):

```powershell
function bug { & "C:\path\to\bugzilla-cli\.venv\Scripts\python.exe" "C:\path\to\bugzilla-cli\bug.py" @args }
```

**Command Prompt** — create a `bug.bat` file somewhere on your `%PATH%` (e.g. `C:\Windows\System32` or a personal scripts folder):

```bat
@echo off
"C:\path\to\bugzilla-cli\.venv\Scripts\python.exe" "C:\path\to\bugzilla-cli\bug.py" %*
```

### Verify

Once set up, all three platforms work the same way:

```bash
bug 12345
bug search --assigned-to me --status NEW
bug activity --since 2d
```

## Project structure

```
bugzilla-cli/
├── bug.py          # entry point and CLI commands
├── client.py       # Bugzilla REST API calls
├── render.py       # terminal formatting
├── requirements.txt
├── pyproject.toml
├── setup.sh        # Linux / macOS setup
├── setup.ps1       # Windows setup
└── .env.example
```
