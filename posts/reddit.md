# I replaced my entire agent orchestration framework with `mv`

I've been building multi-agent AI systems for months. Tried everything — custom event loops, signal files, message queues, state machines. Every orchestrator I built eventually broke in ways that were impossible to debug.

Then it hit me: the filesystem already solves this.

## What I built

**Pigeon** — a `.md` file that moves between directories. Each directory is an agent. When the file lands, the agent activates. When it's done, it moves the file. That's the entire orchestration.

```
loft/           → home base (completed jobs live here)
researcher/     → station.py (activates when pigeon lands)
writer/         → station.py
editor/         → station.py
publisher/      → station.py
pigeon.py       → 90 lines (create, check, stamp, send, retire)
```

## How it works

```bash
python3 researcher/station.py    # Creates PG-001.md, works, sends to writer/
python3 writer/station.py        # Sees PG-001.md, works, sends to editor/
python3 editor/station.py        # Works, sends to publisher/
python3 publisher/station.py     # Works, sends back to researcher/
python3 researcher/station.py    # Reads results, retires PG-001.md, creates PG-002.md
```

Every station is the same pattern:

```python
from pigeon import check, land, stamp, send

def run():
    pg = check("editor")          # File in my directory?
    if not pg: return             # No file, no work.
    content = land(pg)            # Read it.
    # ... do work ...
    stamp(pg, "editor", "Fixed 3 issues")
    send(pg, "publisher")         # Move it.
```

## The pigeon file is the audit trail

```markdown
# PG-001 — Q1 Report

## Journey
| When | Agent | What Happened |
|------|-------|---------------|
| 14:00 | loft | Born |
| 14:01 | researcher | Found 12 topics |
| 14:30 | writer | Wrote 12 articles |
| 14:45 | editor | Fixed 3 tone issues |
| 15:00 | publisher | Published 11 to prod |
```

`cat` any pigeon = full story. `ls loft/` = complete history. `find . -name "PG-*.md"` = where is everything.

## What I replaced

- ~~Custom Python loop~~ → `mv`
- ~~Signal files (done.flag)~~ → file location IS the signal
- ~~JSON state tracking~~ → markdown journey table
- ~~Message queue~~ → directory is the queue
- ~~Orchestrator process~~ → nothing. Each station is independent.

## Why it works

Directories don't crash. `mv` is atomic on most filesystems. `.md` files are human readable. Git tracks them for free. Any language that can move a file can participate.

## Why it won't work for you

Sub-millisecond latency, millions of concurrent jobs, or stateless request/response. Use a real queue for those.

## For everything else

Code breaks. Files don't.

**GitHub:** https://github.com/drew913s/pigeon

**MIT Licensed.** Built by RockTalk Holdings. Battle-tested on a 6-machine AI cluster running 5 agents, 17 brain-folder sub-agents, and real GPU training jobs.
