# 🕊️ Pigeon

**Multi-phase agentic software coordination using files instead of code.**

A pigeon is a `.md` file that moves between directories. Each directory is an agent. When the file lands, the agent activates. When it's done, it moves the file. That's the entire orchestration.

No orchestrator. No message queue. No database. No framework. Just files.

## Quick Start

```bash
pip install pigeon-coord
pigeon init researcher writer editor reviewer publisher
```

This creates:
```
project/
├── loft/           # Home base — pigeons born here, retire here
├── researcher/     # station.py
├── writer/         # station.py
├── editor/         # station.py
├── reviewer/       # station.py
├── publisher/      # station.py
└── pigeon.py       # The library
```

## How It Works

```bash
python3 researcher/station.py    # Creates PG-001.md, works, sends to writer/
python3 writer/station.py        # Sees PG-001.md, works, sends to editor/
python3 editor/station.py        # Sees PG-001.md, works, sends to reviewer/
python3 reviewer/station.py      # Sees PG-001.md, works, sends to publisher/
python3 publisher/station.py     # Sees PG-001.md, works, sends back to researcher/
python3 researcher/station.py    # Reads results, retires PG-001.md to loft/, creates PG-002.md
```

Each station is independent. Run them however you want — manually, cron, filesystem watcher, CI trigger.

## The Pigeon File

Every pigeon is human-readable markdown:

```markdown
# PG-001 — Quarterly Report
**Created:** 2026-03-22

## Plan
Research Q1 metrics, write summary, get editorial review, publish to blog.

## State
- articles: 12
- word_count: 9600
- approved: 11

## Journey
| When | Agent | What Happened |
|------|-------|---------------|
| 14:00 | loft | Born |
| 14:01 | researcher | Found 15 data sources, selected 12 topics |
| 14:30 | writer | Wrote 12 articles (avg 800 words) |
| 14:45 | editor | Fixed 3 tone issues, restructured 2 articles |
| 14:50 | reviewer | Approved 11, rejected 1 (factual error) |
| 15:00 | publisher | Published 11 to production |
| 15:01 | researcher | Read results. Retired to loft. |
```

`cat` any pigeon to see the full story. `ls loft/` to see all completed jobs.

## Writing a Station

Every station follows the same pattern:

```python
# editor/station.py
from pigeon import check, land, stamp, send

def run():
    pg = check("editor")           # File in my directory?
    if not pg: return              # No file, no work.

    content = land(pg)             # Read it.

    # ════════════════════════════
    # YOUR AGENT'S WORK GOES HERE
    # ════════════════════════════

    stamp(pg, "editor", "Fixed 3 tone issues", issues=3)
    send(pg, "reviewer")           # Move to next agent.

if __name__ == "__main__":
    run()
```

The first station creates and retires pigeons:

```python
# researcher/station.py
from pigeon import check, land, stamp, send, retire, create

def run():
    pg = check("researcher")
    if pg:                                    # Returning pigeon
        content = land(pg)                    # Read the results
        retire(pg)                            # Send home to loft

    new = create("Q2 Report", plan="...")     # New pigeon
    stamp(new, "researcher", "Researched 20 topics")
    send(new, "writer")                       # Fly!

if __name__ == "__main__":
    run()
```

## The Library

```python
from pigeon import create, check, land, stamp, send, retire, where

create(name, plan)          # PG-NNN.md born in loft/
check(agent)                # Pigeon in my directory? Returns path or None
land(path)                  # Read the markdown content
stamp(path, agent, action)  # Add journey row, update state fields
send(path, next_agent)      # shutil.move() to next directory
retire(path)                # Move back to loft/
where()                     # Find all pigeons across all directories
```

## Why

| Question | Answer |
|----------|--------|
| How do I debug? | `cat PG-001.md` |
| What's the history? | `ls loft/` |
| Where is the work stuck? | `find . -name "PG-*.md"` |
| How do I stop a job? | Delete the pigeon file |
| How do I resume? | Drop it in any station directory |
| How do I add an agent? | New directory + `station.py` |
| How do I run parallel jobs? | Multiple pigeons in flight |
| What language? | Any. If it can `mv` a file, it plays. |
| What breaks? | Nothing. Directories don't crash. |

## Why Not

- Sub-millisecond latency (filesystem is milliseconds)
- Millions of concurrent jobs (use a proper queue)
- Stateless request/response (use HTTP)

## The Principle

Every orchestration framework solves coordination with more code — more abstractions, more runtime state, more invisible failure modes.

Pigeon solves it with `mv`.

Code breaks. Files don't. The simplest coordination between agents is: **put a file where they can see it.**

## License

MIT

## Origin

Built by [RockTalk Holdings](https://rocktalk.holdings). Battle-tested on a 6-machine AI training cluster orchestrating model research, data encoding, GPU training, and evaluation — all coordinated by `.md` files moving between directories.
