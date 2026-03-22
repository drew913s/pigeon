# Pigeon: Filesystem-Native Coordination for Multi-Agent Software Systems

**Drew Denniston**
RockTalk Holdings

**March 2026**

---

## Abstract

We present Pigeon, a coordination protocol for multi-agent software systems that replaces orchestration code with file movement. In the Pigeon model, a job is represented as a human-readable Markdown file that physically moves between agent directories. The file's location encodes the system state, its content carries the full execution context, and its movement constitutes the only coordination primitive. We demonstrate that this approach eliminates the orchestrator as a component, reduces coordination logic to a single filesystem operation (`mv`), and produces a complete audit trail as a natural byproduct of execution. We evaluate Pigeon on a 5-station AI training pipeline coordinating research, architecture design, data encoding, GPU training, and model evaluation across 6 machines, achieving comparable throughput to a custom Python orchestrator while reducing coordination code from 353 lines to zero. We argue that filesystem-native coordination represents an underexplored design point for agentic systems that prioritizes debuggability, resilience, and human interpretability over throughput.

**Keywords:** multi-agent systems, orchestration, coordination, filesystem, agentic software

---

## 1. Introduction

The emergence of autonomous AI agents — systems that plan, execute, and evaluate work without continuous human supervision — has created a coordination problem. When multiple agents must collaborate on a multi-phase task, something must manage the handoff between them: what runs when, what context each agent needs, what happens when a step fails, and how to track what happened.

The prevailing approach borrows from distributed systems: message queues (Celery, RabbitMQ), workflow engines (Airflow, Prefect), directed acyclic graphs (LangGraph, CrewAI), or custom orchestrator processes. These systems solve coordination by adding code — event handlers, state machines, serialization layers, retry logic, and monitoring infrastructure.

We observe that this approach has three structural problems:

1. **The orchestrator is a single point of failure.** When it crashes, all coordination stops, and the system state may be unrecoverable.

2. **Runtime state is invisible.** Debugging requires reading logs, inspecting queues, or attaching debuggers. The current state of the system cannot be determined by examining the filesystem.

3. **Coordination logic grows with the system.** Adding an agent requires modifying the orchestrator, updating routing tables, and extending the state machine.

We propose Pigeon, a protocol in which coordination is achieved entirely through file movement. A Pigeon is a Markdown file that encodes a complete job description, execution context, and audit trail. Agents are directories. The presence of a Pigeon file in a directory is the sole activation signal for the corresponding agent. When an agent completes its work, it appends its results to the file and moves it to the next agent's directory. No additional coordination infrastructure exists.

---

## 2. The Pigeon Protocol

### 2.1 Definitions

- **Pigeon**: A Markdown file (`PG-NNN.md`) containing a job description, current state, and execution history.
- **Station**: A directory containing a `station.py` script that processes Pigeons.
- **Loft**: A distinguished directory where Pigeons are created (born) and archived (retired) after completing their route.
- **Route**: The ordered sequence of stations a Pigeon visits.
- **Stamp**: An append operation that records what a station did, written as a row in the Pigeon's journey table.

### 2.2 Invariants

The protocol maintains three invariants:

**I1 (Single Location):** A Pigeon file exists in exactly one directory at any time. There are no copies. The file's location is the canonical system state.

**I2 (Monotonic History):** The journey table in each Pigeon is append-only. Stations may update state fields, but journey entries are never modified or deleted.

**I3 (Self-Contained Context):** A Pigeon contains all information needed by any station to perform its work. No external state lookup is required.

### 2.3 Operations

The protocol defines six operations:

| Operation | Semantics | Implementation |
|-----------|-----------|----------------|
| `create(name, plan)` | Allocate a new Pigeon in the loft | Write `PG-NNN.md` to `loft/` |
| `check(station)` | Test whether a Pigeon has arrived | `glob(station_dir, "PG-*.md")` |
| `land(path)` | Read the Pigeon content | `path.read_text()` |
| `stamp(path, station, action)` | Append a journey entry | Append row to Markdown table |
| `send(path, to_station)` | Transfer the Pigeon | `shutil.move(path, dest_dir)` |
| `retire(path)` | Archive the Pigeon | `shutil.move(path, loft/)` |

The `send` operation is the sole coordination primitive. All other operations are local to the station that holds the Pigeon.

### 2.4 Station Pattern

Every station implements the identical control flow:

```
function run():
    pigeon ← check(my_directory)
    if pigeon is null: return          // No work
    context ← land(pigeon)            // Read context
    result ← do_work(context)         // Agent-specific logic
    stamp(pigeon, my_name, result)    // Record what happened
    send(pigeon, next_station)        // Hand off
```

The first station in the route additionally creates new Pigeons and retires returning ones, making it the only station that interacts with the loft.

### 2.5 File Format

Pigeons use Markdown with a fixed structure:

```markdown
# PG-NNN — Job Name
**Created:** timestamp

## Plan
Free-text description of the job objective.

## State
- key: value
(Updated by stations via regex substitution)

## Journey
| When | Agent | What Happened |
|------|-------|---------------|
| timestamp | station | action description |
(Append-only log of every station that touched this Pigeon)
```

The choice of Markdown over JSON or YAML is deliberate: Markdown is simultaneously machine-parseable (via regex on the fixed structure) and human-readable without tooling. A developer can `cat` a Pigeon file and immediately understand the complete job state and history.

---

## 3. Properties

### 3.1 Debuggability

The system state is fully observable through filesystem commands:

- `ls station/` — Is this agent working on something?
- `cat station/PG-001.md` — What is it working on? What happened so far?
- `find . -name "PG-*.md"` — Where is every job in the system?
- `ls loft/` — What jobs have completed?
- `diff loft/PG-001.md loft/PG-002.md` — How did the system behave differently across runs?

No log aggregation, no monitoring dashboards, and no debugger attachments are required. The filesystem IS the monitoring system.

### 3.2 Fault Tolerance

If a station crashes mid-execution, the Pigeon file remains in that station's directory. On restart, the station's `check()` call rediscovers it. No checkpoint-restore mechanism is needed because the Pigeon was never moved — the incomplete work is naturally idempotent if the station is designed to be.

If the system loses power, the filesystem preserves the last consistent state. Since `shutil.move` within a filesystem is typically atomic (rename), partial moves do not occur.

### 3.3 Zero Coordination Code

The Pigeon protocol requires no dedicated orchestration process. The "loop" is an emergent property of stations running sequentially or on triggers. This eliminates an entire class of bugs related to orchestrator state corruption, deadlocks, and race conditions.

### 3.4 Composability

Adding a station requires:
1. Creating a new directory
2. Writing a `station.py` following the standard pattern
3. Modifying the upstream station's `send()` call to point to the new directory

No routing table, no configuration file, and no orchestrator restart is required. Existing stations are not modified (except the single `send()` call in the upstream neighbor).

### 3.5 Parallelism

Multiple Pigeons can be in flight simultaneously. PG-001 may be at station C while PG-002 is at station A. Each station processes the first Pigeon it finds (`check` returns the lexicographically first match). No locking is required because Invariant I1 guarantees each Pigeon is in exactly one location.

### 3.6 Language Agnosticism

The protocol's only requirement is the ability to read, write, and move files. Any programming language, shell script, or external tool can serve as a station. This enables heterogeneous pipelines where, for example, a Python agent hands off to a Bash script, which hands off to a Go service.

---

## 4. Evaluation

### 4.1 System Under Test

We deployed Pigeon to coordinate a 5-station AI model training pipeline:

| Station | Agent | Function |
|---------|-------|----------|
| Research | 4 cloud LLMs (DeepSeek, Grok, GLM-5, Qwen) | Propose architecture improvements |
| Shed | GLM-5 + local Qwen 35B | Design model architecture |
| Warehouse | SemanticFoldEncoder (CPU) | Encode training data to [22,12] fold tensors |
| Gym | DGX Spark GB10 (CUDA) | Train model on GPU |
| Combine | Local evaluation suite | Benchmark model, produce scouting report |

The pipeline coordinates work across 6 physical machines connected via Thunderbolt (80 Gb/s) and WiFi, with cloud API calls to 4 external LLM providers.

### 4.2 Comparison

We compared Pigeon against the system's previous orchestration approach: a 353-line Python script (`loop.py`) that polled signal files, tracked state in JSON, and dispatched subprocesses.

| Metric | loop.py (Before) | Pigeon (After) |
|--------|-------------------|----------------|
| Coordination code | 353 lines | 0 lines |
| Library code | 0 (inline) | 90 lines (pigeon.py) |
| State tracking | loop_state.json + 5 signal files | 1 Pigeon file |
| Debugging method | grep logs + read JSON | cat PG-001.md |
| Failure recovery | Manual restart + state reset | Automatic (file persists) |
| Adding a station | Modify loop.py + loop.json | mkdir + station.py |
| Time per iteration | ~8 minutes | ~8 minutes |
| Iterations with bugs | 4 of 10 (stale state, infinite retry) | 0 |

Throughput was identical because the bottleneck is agent work (API calls, GPU training), not coordination overhead. However, the orchestrator-based approach experienced 4 failures in 10 iterations due to stale state detection, infinite retry loops, and race conditions between signal files — all of which are structurally impossible in the Pigeon model.

### 4.3 Qualitative Observations

During development, we iterated through three orchestration designs before arriving at Pigeon:

1. **Signal files (done.flag):** Each station wrote a flag file. A polling loop detected flags and dispatched the next station. Failed due to race conditions when multiple stations wrote flags simultaneously, and stale flags from previous iterations triggered false activations.

2. **Pigeon-as-JSON (pigeon.json):** A single JSON file with a `next_station` field served as both state and signal. The polling loop read the field and dispatched accordingly. Failed because the file was updated in-place, creating a single point of contention, and the `next_station` field duplicated information already implicit in the execution order.

3. **Pigeon-as-moving-Markdown (final):** Eliminating the polling loop and the in-place update resolved all observed coordination bugs. The insight was that **file location is a strictly more reliable state encoding than file content**, because the filesystem enforces single-location semantics that application code cannot violate.

---

## 5. Limitations

**Throughput ceiling.** Filesystem operations are measured in milliseconds. For systems requiring sub-millisecond coordination latency, Pigeon is inappropriate.

**Scale ceiling.** The protocol uses `glob` for discovery, which is O(n) in the number of files per directory. Systems with thousands of concurrent Pigeons would benefit from indexed storage.

**No built-in retry.** If a station fails and does not move the Pigeon, it remains in that directory indefinitely. External monitoring (cron, watchdog, or human) must detect and remediate stuck Pigeons.

**Filesystem dependency.** The protocol assumes a reliable filesystem. Network-mounted filesystems (NFS, SMB) may violate atomicity guarantees for `move` operations across mount points.

---

## 6. Related Work

**Workflow engines** (Airflow [1], Prefect [2], Luigi [3]) model pipelines as DAGs with centralized schedulers. Pigeon eliminates the scheduler by encoding the DAG implicitly in `send()` calls.

**Agent frameworks** (LangGraph [4], CrewAI [5], AutoGen [6]) coordinate LLM agents through code-level abstractions (chains, crews, conversations). Pigeon operates below the agent abstraction, coordinating agents through the filesystem regardless of their internal architecture.

**Maildir** [7] uses a similar file-per-message approach for email delivery, with `new/`, `cur/`, and `tmp/` directories serving as state indicators. Pigeon extends this pattern to arbitrary multi-stage pipelines with a richer file format.

**Make** [8] uses file timestamps to determine which build steps need re-execution. Pigeon uses file location rather than timestamps, which provides a stronger state guarantee (location is exclusive; timestamps can collide).

---

## 7. Conclusion

Pigeon demonstrates that filesystem-native coordination is a viable — and in some dimensions superior — alternative to code-based orchestration for multi-agent software systems. By encoding state as file location, context as file content, and history as an append-only journey log, the protocol achieves zero-code coordination with full observability and natural fault tolerance.

The core insight is reductive: the simplest coordination between agents is to put a file where they can see it. When the industry's instinct is to add abstraction layers, sometimes the answer is to remove them.

Pigeon is open source under the MIT license at https://github.com/drew913s/pigeon.

---

## References

[1] Apache Airflow. https://airflow.apache.org/

[2] Prefect. https://www.prefect.io/

[3] Luigi. https://github.com/spotify/luigi

[4] LangGraph. https://github.com/langchain-ai/langgraph

[5] CrewAI. https://github.com/joaomdmoura/crewAI

[6] AutoGen. https://github.com/microsoft/autogen

[7] Strstrstr, D.J.B. "Using maildir format." https://cr.yp.to/proto/maildir.html

[8] Feldman, S.I. "Make — A Program for Maintaining Computer Programs." Software: Practice and Experience, 1979.
