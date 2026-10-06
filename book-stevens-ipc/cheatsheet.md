# Cheatsheet — UNP Vol 2 (Stevens)

## Choosing an IPC mechanism

| Need | Pick | Why |
|---|---|---|
| Parent↔child byte stream | pipe | no names needed, cheapest |
| Unrelated processes, one host | FIFO / Posix MQ | name-based rendezvous |
| Message boundaries preserved | Posix MQ > System V MQ | native records, priorities, mq_notify |
| Shared structured data, max speed | mmap MAP_SHARED + process-shared mutex | zero-copy |
| Lock a file region | fcntl record locking | advisory, per-byte-range |
| Single-daemon guarantee | PID file + fcntl write lock | kernel auto-releases on death |
| Read-mostly concurrent access | read-write lock | readers don't block |
| Cross-host procedure call | Sun RPC / sockets | doors & shm are local-only |
| Solaris local fast RPC | doors | thread library call, no network stack |

## Posix vs System V (same decision, four facilities)

| Dimension | Posix | System V |
|---|---|---|
| Naming | pathname-like, px_ipc_name | key_t / ftok / IPC_PRIVATE |
| Create+init | atomic (mq/sem/shm_open) | two steps → race to fix (sem_otime poll) |
| Removal | mq_unlink / sem_unlink / shm_unlink | ctl(IPC_RMID), ipcs/ipcrm |
| Portability | newer (realtime/threads std) | universal |
| Rule | **prefer Posix when available** | use only for legacy reach |

## Persistence & lifecycle quick test

- pipe/FIFO/socket → **process-persistent** (FIFO *name* is filesystem-persistent; data discarded on last close)
- Posix & System V MQ/sem/shm → **kernel-persistent** (survive owners; must remove explicitly)
- mmap'd file → **filesystem-persistent** (msync to flush)
- After **fork**: child gets copies of fds/mappings (shared object); after **exec**: descriptors without FD_CLOEXEC survive, mappings vanish; on **exit**: pipes die with last fd, SysV/Posix IPC persists.

## Blocking & atomicity tells

- FIFO `open(O_RDONLY)` blocks until a writer opens (and vice versa) → always open opposite ends in opposite order or deadlock; `O_NONBLOCK` read-open returns immediately, write-open fails `ENXIO`.
- `write` ≤ PIPE_BUF to pipe/FIFO is **atomic**; larger may interleave. Nonblocking changes *blocking*, never atomicity.
- Reader gone → write returns EPIPE **and** SIGPIPE kills by default: ignore SIGPIPE, check EPIPE.
- `mq_receive` on empty queue blocks or, with O_NONBLOCK, returns EAGAIN.
- System V msgsnd blocks when queue full (EAGAIN under IPC_NOWAIT) — mind msgmax/msgmnb limits.

## Synchronization decision rules

- Mutex = exclusion. **Waiting for a state needs a condition variable**: `while(pred) pthread_cond_wait` — never `if`.
- Bounded buffer: mutex(1) + nempty(N) + nstored(0); always acquire mutex first, and always in the same order everywhere.
- Read-write lock only when reads ≫ writes; naive implementations starve writers.
- Cross-process (shared memory): set PTHREAD_PROCESS_SHARED attr and put the primitive *in* the shared region; remember a crashed process leaves it locked forever.
- System V semaphores: creation race → IPC_CREAT|IPC_EXCL, EEXIST, reopen, poll sem_otime≠0. Avoid SEM_UNDO unless you accept exit-time ordering hazards.
- Locking a file: just try F_SETLK; EACCES/EAGAIN means held. Never F_GETLK-then-set (race). Closing ANY fd on that file drops ALL your locks on it.
- Advisory locks stop only cooperating processes; mandatory locking needs special mount flags and breaks read/write atomicity assumptions — treat as a trap, not a tool.

## Error-handling conventions (Stevens's own)

- Wrap every IPC call: on failure print errno string + exit (his err_sys family).
- Pthreads functions **return error codes, don't set errno** — check return, don't perror blindly.
- EINTR from slow syscalls: retry the call (or block signals during critical sections).
- SA_RESTART off for handlers that should interrupt waits.

## Performance rules of thumb (App A)

- Throughput ranking (large messages): shared memory ≫ message queues > pipes/FIFOs > doors > RPC — bandwidth grows ~1/message-size, latency is flat.
- Small-message cost is dominated by context switch + syscall count, not copying.
- Measure with: bandwidth program (one-way, vary message size) + latency program (ping-pong 1 byte) — don't trust intuition.
- Thread sync ≪ process sync cost: prefer threads + shared address space when only data sharing is needed.

## Tells & smells

- Server never returns on a FIFO → you forgot the dummy write-open to prevent EOF churn.
- Intermittent deadlock right after startup → create-then-init race (SysV sem/msgget) or FIFO open order.
- Program killed, semaphore stuck at 0 → no kernel auto-release for Posix sems in shm; add recovery or use file locks for crash-safety.
- Numbers garbled across processes → pointer stored in shared memory (use offsets).
- RPC call "sometimes" executes twice → UDP + retry = at-least-once; make procedure idempotent or use TCP/dup-cache.
