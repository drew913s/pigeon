"""
pigeon — Multi-phase agentic software coordination using files.

A pigeon is a .md file that moves between directories.
Each directory is an agent. When the file lands, the agent activates.
When it's done, it moves the file. That's the entire orchestration.

    from pigeon import create, check, land, stamp, send, retire, where

MIT License — RockTalk Holdings 2026
"""

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

__version__ = "0.1.0"

# Auto-detect project root (directory containing loft/)
def _find_root(start: Path = None) -> Path:
    p = start or Path.cwd()
    for _ in range(10):
        if (p / "loft").is_dir():
            return p
        if p.parent == p:
            break
        p = p.parent
    return Path.cwd()

ROOT = _find_root()
LOFT = ROOT / "loft"


def create(name: str, plan: str = "", **fields) -> Path:
    """Create a new pigeon in the loft.

    Args:
        name: Job name (appears in the pigeon header)
        plan: What this job needs to accomplish
        **fields: Initial state fields (key=value)

    Returns:
        Path to the new PG-NNN.md file in loft/
    """
    LOFT.mkdir(exist_ok=True)

    # Find next number across ALL pigeons
    nums = [int(m.group(1)) for p in ROOT.rglob("PG-*.md")
            if (m := re.search(r"PG-(\d+)", p.name))]
    n = max(nums) + 1 if nums else 1
    pg_id = f"PG-{n:03d}"

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    state = "\n".join(f"- {k}: {v}" for k, v in fields.items()) if fields else ""

    content = (
        f"# {pg_id} — {name}\n"
        f"**Created:** {ts}\n\n"
        f"## Plan\n{plan or 'No plan specified.'}\n\n"
        f"## State\n{state}\n\n"
        f"## Journey\n"
        f"| When | Agent | What Happened |\n"
        f"|------|-------|---------------|\n"
        f"| {ts} | loft | Born |\n"
    )

    path = LOFT / f"{pg_id}.md"
    path.write_text(content)
    return path


def check(agent: str) -> Path:
    """Check if a pigeon has landed at this agent.

    Args:
        agent: Directory name to check

    Returns:
        Path to the first pigeon found, or None if empty
    """
    d = ROOT / agent
    if not d.exists():
        return None
    pgs = sorted(d.glob("PG-*.md"))
    return pgs[0] if pgs else None


def check_all(agent: str) -> list:
    """Find all pigeons at this agent.

    Returns:
        List of paths to all pigeon files
    """
    d = ROOT / agent
    if not d.exists():
        return []
    return sorted(d.glob("PG-*.md"))


def land(path: Path) -> str:
    """Read a pigeon's content.

    Args:
        path: Path to the pigeon file

    Returns:
        The full markdown content
    """
    if path and path.exists():
        return path.read_text()
    return ""


def stamp(path: Path, agent: str, action: str, **fields):
    """Stamp the pigeon — record what happened and update state.

    Args:
        path: Path to the pigeon file
        agent: Name of the agent stamping
        action: What the agent did (one line)
        **fields: State fields to update (matched by "- key: " pattern)
    """
    if not path or not path.exists():
        return

    content = path.read_text()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Add journey row
    content = content.rstrip() + f"\n| {ts} | {agent} | {action} |\n"

    # Update state fields
    for key, value in fields.items():
        pattern = f"- {key}: .*"
        replacement = f"- {key}: {value}"
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
        else:
            # Add new field to State section
            state_match = re.search(r"(## State\n)", content)
            if state_match:
                insert_at = state_match.end()
                content = content[:insert_at] + f"- {key}: {value}\n" + content[insert_at:]

    path.write_text(content)


def send(path: Path, to_agent: str) -> Path:
    """Move the pigeon to the next agent's directory.

    Args:
        path: Current pigeon path
        to_agent: Destination directory name

    Returns:
        New path after move
    """
    if not path or not path.exists():
        return None

    dest_dir = ROOT / to_agent
    dest_dir.mkdir(exist_ok=True)
    dest = dest_dir / path.name
    shutil.move(str(path), str(dest))
    return dest


def retire(path: Path) -> Path:
    """Return the pigeon to the loft. Journey complete.

    Args:
        path: Current pigeon path

    Returns:
        Path in loft/
    """
    if not path or not path.exists():
        return None
    LOFT.mkdir(exist_ok=True)
    dest = LOFT / path.name
    shutil.move(str(path), str(dest))
    return dest


def where() -> dict:
    """Find all pigeons — where they are right now.

    Returns:
        Dict mapping pigeon ID to directory name.
        Example: {"PG-001": "loft", "PG-002": "editor", "PG-003": "writer"}
    """
    result = {}
    for p in ROOT.rglob("PG-*.md"):
        result[p.stem] = p.parent.name
    return result
