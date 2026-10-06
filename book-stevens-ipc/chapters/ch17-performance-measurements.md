# Chapter 17: Performance Measurements (Appendix A)

## Core Idea
Before choosing an IPC mechanism, measure it. Appendix A builds simple lmbench-style benchmark programs that quantify every IPC technique in the book — six message-passing forms (pipes, FIFOs, Posix MQ, System V MQ, doors, Sun RPC) and five synchronization forms (mutexes+condition variables, read-write locks, fcntl record locking, Posix semaphores, System V semaphores) — along two axes: **bandwidth** (bulk transfer rate, MB/sec, as a function of message size) and **latency** (round-trip time for a 1-byte message). Both numbers matter: bandwidth predicts bulk-data behavior, latency predicts control-message behavior.

## Frameworks Introduced
- **Two-metric measurement model**: bandwidth (millions of bytes, varying I/O operation size: expect bandwidth to rise with message size) vs latency (1-byte round trip = 2 context switches + 4 system calls + channel overhead).
- **Control-pipe/data-channel harness**: a separate control pipe synchronizes start of each timed transfer; only the data path is inside the timed region.
- **Shared-counter synchronization benchmark**: N threads (or N processes, via `my_shm` anonymous shared memory) each increment a shared counter 1,000,000 times; since the increment is trivial, elapsed time is dominated by the synchronization primitive. Lock is held by main before creating workers and released exactly when the timer starts; final counter is verified (correctness check doubles as a race detector).
- **Pre-fault discipline**: `valloc` page-aligned buffer + `touch()` (write 1 byte per page) before timing, so page faults don't pollute measurements.

## Key Concepts
- Bandwidth normally increases with message size (amortized per-call overhead).
- System V MQ kernel limits (`msgmax`, `msgmnb`, `msgseg`) had to be raised in `/etc/system` (Solaris) or `sysconfig` (Digital Unix) to allow 16384-byte messages.
- Asynchronous (message passing) vs synchronous (doors, RPC — `door_call` blocks): async channels need ~N/4 context switches for N messages with a queue depth of 8; synchronous calls force 2 context switches per message, yet doors still delivered the fastest bandwidth up to ~25000-byte messages on Solaris.
- Posix MQ capacity (`mq_maxmsg = 4`) is a performance-tuning "magic number" (affects context-switch frequency and mmap'd file size).
- Pathological synchronization test caveat: threads do nothing but lock; a descheduled thread holds the lock, so the next thread blocks immediately — explains Digital Unix Posix-semaphore anomalies (huge times, non-linear growth).
- fcntl record locking works between processes only — the thread test is meaningless with >1 thread (locks silently succeed, counter ends up wrong).
- Run-to-run variance is real (pipe latency runs: 278–397 µs on identical inputs); always average multiple runs.
- Explaining anomalies is far harder than measuring them; measure on *your* system before choosing.

## Mental Models
- Latency budget = 2 context switches + 4 system calls + per-byte channel overhead.
- Synchronization cost ladder (fastest to slowest): Posix mutex ≪ read-write lock < memory-based semaphore < named semaphore ≈ System V semaphore < System V semaphore with SEM_UNDO ≪ fcntl record locking.
- Procedure-call IPC (doors/RPC) trades context-switch density (2 per call) for kernel-side efficiency and caller identity.

## Anti-patterns
- Timing without pre-touching the buffer (page faults inside the timed region).
- Timing process/thread creation and setup: lock *before* forking/creating, start timer, then release the lock.
- Trusting a single run instead of averaging several (5-run averages used throughout).
- Comparing mechanisms using kernel-default limits (System V MQ defaults cripple large messages).
- Benchmarking fcntl locks across threads of one process — semantically invalid, silently wrong counter.
- Reading benchmark tables as universal truths — portability of conclusions ≠ portability of numbers.

## Code Examples
- `bench/bw_pipe.c` — pipe bandwidth: `writer()` child loops writing `xfersize` bytes driven by control-pipe byte counts; parent `reader()` reads; `Start_time()`/`Stop_time()` via `gettimeofday` + `tv_sub`; result = totalnbytes / seconds.
- `bench/bw_pxmsg.c` — Posix MQ bandwidth (queue created with `mq_maxmsg=4`, `mq_msgsize=xfersize`).
- `bench/bw_svmsg.c` — System V MQ bandwidth (`msgsnd`/`msgrcv`, payload `xfersize - sizeof(long)` for the mtype field).
- `bench/bw_door.c` — doors bandwidth: child creates+`fattach`es the door, parent times `door_call` loop; server procedure signals completion over a control pipe.
- `bench/bw_sunrpc.x/.c` — RPC bandwidth: one procedure taking variable-length opaque data; protocol (TCP/UDP) chosen at runtime.
- `bench/lat_pipe.c` — latency: two half-duplex pipes; child echoes 1 byte; parent times `doit()` loop of 10000.
- `bench/lat_pxmsg.c` — needs *two* queues (`mq_receive` always returns the head message; priorities can't split directions on one queue).
- `bench/lat_svmsg.c` — one queue suffices: type 1 = parent→child, type 2 = child→parent; `msgrcv` filters by type.
- `bench/lat_door.c`, `lat_sunrpc` client calling `NULLPROC` via `clnt_call`.
- `bench/incr_*` family — shared-counter timing: `incr_pxmutex1.c` (threads), `incr_pxmutex5.c` (processes: mutex in `my_shm()` shared memory with `PTHREAD_PROCESS_SHARED` attr, `waitpid` for children), variants for rwlock, memory/named Posix semaphores, System V semaphores (± `SEM_UNDO`), fcntl record locking.

## Reference Tables
Test systems: SparcStation 4/110, Solaris 2.6; DEC 3000/300 Alpha, Digital Unix 4.0B. (OCR of the source tables is lossy; well-attested cells shown, uncertain cells marked ~.)

**Figure A.1 — Latency, 1-byte round trip (µsec)**: pipe ≈ 324 µsec (Solaris, 5-run avg). Doors lowest of the book's mechanisms; TCP/UDP socket and Unix-domain socket values from lmbench for comparison (Solaris ≈ 150/130/65 µsec class; Digital Unix values similar order).

**Figure A.2 — Bandwidth, Solaris 2.6 (MBytes/sec)**

| Message size | Pipe | Posix MQ | System V MQ |
|---|---|---|---|
| 4096  | 12.7 | 10.2 | ~12.6 |
| 8192  | 13.1 | 11.6 | ~14.4 |
| 16384 | 13.2 | 13.4 | ~16.8 |
| 32768 | 13.7 | 14.4 | ~12.2 (drops — internal queue limits) |

Doors: fastest up to ~25000-byte messages (peak ≈ 16+ MB/sec). Sun RPC TCP/UDP substantially slower; TCP socket ≈ 16 MB/sec and Unix-domain socket fastest overall at 65536-byte messages (lmbench, 65536-byte messages only).

**Figure A.4 — Bandwidth, Digital Unix 4.0B (MBytes/sec)**

| Message size | Pipe | Posix MQ | Sun RPC TCP | Sun RPC UDP |
|---|---|---|---|---|
| 1024  | 1.8 | — | — | 0.6 |
| 4096  | 3.5 | — | — | 1.0 |
| 8192  | 5.9 / 16.5 (pipe) | — | — | 1.8 |
| 16384 | 8.6 | — | — | 2.5 |
| 32768 | 11.7 (pipe 15.9) | — | — | — |
| 65536 | 14.0 (pipe 14.2) | — | — | — |

**Figure A.6 — Thread synchronization, Solaris 2.6 (seconds; 1–5 threads × 1,000,000 increments)**

| #threads | Posix mutex | RW lock | Posix mem sem | Posix named sem | SysV sem | SysV sem+UNDO | fcntl |
|---|---|---|---|---|---|---|---|
| 1 | 0.7 | 2.0 | 4.5 | 15.4 | 16.3 | 21.1 | 89.4 |
| 2 | 1.5 | 5.4 | 9.0 | 31.1 | 31.5 | 37.5 | — |
| 3 | 2.2 | 7.5 | 14.4 | 46.5 | 48.3 | 57.7 | — |
| 4 | 2.9 | 13.7 | 18.2 | 62.5 | 65.8 | 75.8 | — |
| 5 | 3.7 | 19.7 | 22.8 | 76.8 | 81.8 | 90.0 | — |

**Figure A.8 — Thread synchronization, Digital Unix 4.0B (seconds)**: mutex 2.9 (1 thread), 12.9/13.2 class; RW lock ~14.2/26.6; fcntl ~96.4; Posix semaphores anomalously large with >1 thread (not graphed).

**Figure A.10 — Process synchronization, Solaris 2.6 (seconds, 1–5 processes)**: mutex 0.8; mem sem 1.9→22.1; named sem 13.6→90.7 class; fcntl 17.3 (single value plotted; rest too large).

**Figure A.12 — Process synchronization, Digital Unix 4.0B (seconds)**

| #procs | Posix mem sem | Posix named sem | SysV sem | SysV sem+UNDO | fcntl |
|---|---|---|---|---|---|
| 1 | 12.8 | 12.5 | 30.1 | 49.0 | 98.1 |
| 2 | 664.8 | 659.2 | 58.6 | 95.7 | 477.1 |
| 3 | 1236.1 | 1269.8 | ~88 | 146.2 | 1785.2 |
| 5 | 2179.9 | 2196.8 | 147.7 | 250.9 | 3419.2 |

(No process-shared mutex under Digital Unix 4.0B — `PTHREAD_PROCESS_SHARED` unsupported.)

## Worked Example (bandwidth/latency measurement methodology)
Pipe bandwidth, Solaris: `bw_pipe 5 10 65536` → 5 loops × 10 MiB each, 65536 bytes per write/read. Five consecutive runs printed 13.722 / 13.781 / 13.685 / 13.665 / 13.584 MB/sec → average 13.7, the Figure A.2 entry. Method: (1) `valloc` + `touch` the buffer; (2) create control and data pipes, fork; child `writer()` blocks reading byte-counts from the control pipe; (3) parent calls `Start_time()`, loops `reader()` which sends "nbytes" on the control pipe and reads until done; (4) bandwidth = totalnbytes / `Stop_time()` (µsec) × nloop; (5) kill child with SIGTERM. Latency analog: `lat_pipe 10000`, child echoes 1 byte between two half-duplex pipes; per-iteration time = `Stop_time()/nloop`, averaging ~324 µsec including 2 context switches and 4 system calls.

## Key Takeaways
1. Measure bandwidth *and* latency — they rank mechanisms differently.
2. Bigger messages → higher bandwidth, until kernel-internal limits bite (Solaris SysV MQ drops above 16384).
3. Mutexes are an order of magnitude cheaper than any semaphore; fcntl record locking is the slowest synchronization by far (and gets catastrophically worse with contention).
4. Synchronous procedure calls (doors/RPC) pay 2 context switches per message yet doors still win bandwidth for mid-size messages.
5. Queue capacity, kernel tunables, and even benchmark structure (pathological lock-holding) materially change results.
6. The programs are deliberately simple: port them, simulate your workload, measure on your own system — the numbers are hardware/OS-specific.

## Connects To
- Epilogue IPC-selection criteria (portability, networked vs local, realtime scheduling) — performance is only one of four decision inputs.
- Ch. 2/4 (pipes & FIFOs), Ch. 5 (Posix MQ), Ch. 3 (System V MQ limits), Ch. 15 (doors), Ch. 16 (Sun RPC, null procedure latency).
- Ch. 7 (mutexes, `PTHREAD_PROCESS_SHARED`), Ch. 8 (read-write locks), Ch. 10/11 (Posix/System V semaphores, SEM_UNDO), Ch. 9/13 (fcntl record locking), Ch. 12 (anonymous shared memory: `MAP_ANON`, `/dev/zero`).
- lmbench (McVoy & Staelin, 1996) — the general-purpose benchmark suite these programs are modeled on.
