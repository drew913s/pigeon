"""pigeon CLI — Initialize and manage pigeon projects."""

import sys
from pathlib import Path


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print("pigeon — File-driven agent coordination")
        print()
        print("  pigeon init agent1 agent2 agent3    Create a pigeon project")
        print("  pigeon status                       Show all pigeons")
        print("  pigeon create 'job name'            Create a new pigeon")
        print("  pigeon fly agent                    Run a station")
        return

    if args[0] == "init":
        agents = args[1:]
        if not agents:
            print("Usage: pigeon init agent1 agent2 agent3 ...")
            return
        _init(agents)

    elif args[0] == "status":
        _status()

    elif args[0] == "create":
        name = " ".join(args[1:]) or "unnamed"
        _create(name)

    elif args[0] == "fly":
        agent = args[1] if len(args) > 1 else None
        if not agent:
            print("Usage: pigeon fly <agent>")
            return
        _fly(agent)


def _init(agents):
    root = Path.cwd()
    (root / "loft").mkdir(exist_ok=True)

    for agent in agents:
        agent_dir = root / agent
        agent_dir.mkdir(exist_ok=True)

        is_first = agent == agents[0]
        next_agent = agents[1] if is_first and len(agents) > 1 else agents[(agents.index(agent) + 1) % len(agents)]

        if is_first:
            station = f'''from pigeon import check, land, stamp, send, retire, create

AGENT = "{agent}"
NEXT = "{next_agent}"

def run():
    pg = check(AGENT)
    if pg:
        content = land(pg)
        print(f"[{{AGENT}}] Pigeon returned: {{pg.name}}")
        retire(pg)
        print(f"[{{AGENT}}] Retired to loft")

    new = create("job", plan="Describe the plan here")
    stamp(new, AGENT, "Started new cycle")
    new = send(new, NEXT)
    print(f"[{{AGENT}}] Pigeon sent to {{NEXT}}: {{new.name}}")

if __name__ == "__main__":
    run()
'''
        else:
            station = f'''from pigeon import check, land, stamp, send

AGENT = "{agent}"
NEXT = "{next_agent}"

def run():
    pg = check(AGENT)
    if not pg:
        print(f"[{{AGENT}}] No pigeon.")
        return

    print(f"[{{AGENT}}] Pigeon received: {{pg.name}}")
    content = land(pg)

    # ════ YOUR WORK HERE ════

    stamp(pg, AGENT, "Did the work")
    pg = send(pg, NEXT)
    print(f"[{{AGENT}}] Pigeon sent to {{NEXT}}")

if __name__ == "__main__":
    run()
'''

        (agent_dir / "station.py").write_text(station)

    # Copy pigeon.py
    src = Path(__file__).parent / "pigeon.py"
    if src.exists():
        import shutil
        shutil.copy2(str(src), str(root / "pigeon.py"))
    else:
        print("Warning: pigeon.py not found — copy it manually")

    print(f"Initialized pigeon project with {len(agents)} agents:")
    print(f"  loft/  (home base)")
    for a in agents:
        marker = " ← creates & retires pigeons" if a == agents[0] else ""
        print(f"  {a}/station.py{marker}")
    print(f"  pigeon.py")
    print()
    print(f"Run: python3 {agents[0]}/station.py")


def _status():
    sys.path.insert(0, str(Path.cwd()))
    try:
        from pigeon import where
        pigeons = where()
        if not pigeons:
            print("No pigeons in flight or retired.")
            return
        for pg_id, location in sorted(pigeons.items()):
            print(f"  {pg_id}  →  {location}/")
    except ImportError:
        print("No pigeon.py in current directory. Run 'pigeon init' first.")


def _create(name):
    sys.path.insert(0, str(Path.cwd()))
    try:
        from pigeon import create
        pg = create(name)
        print(f"Created: {pg}")
    except ImportError:
        print("No pigeon.py in current directory.")


def _fly(agent):
    station = Path.cwd() / agent / "station.py"
    if not station.exists():
        print(f"No station.py in {agent}/")
        return
    import subprocess
    subprocess.run([sys.executable, str(station)])


if __name__ == "__main__":
    main()
