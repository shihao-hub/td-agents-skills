---
name: book-stevens-ipc
description: "Knowledge base from \"UNIX Network Programming, Volume 2: Interprocess Communications, Second Edition\" by W. Richard Stevens. Use when applying Stevens's IPC frameworks for pipes, FIFOs, Posix/System V message queues, mutexes, condition variables, read-write locks, record locking, semaphores, shared memory (mmap/shm), doors, Sun RPC, XDR, or IPC performance measurement, studying the book, or referencing its concepts."
---

<!-- argument-hint: [topic, API name, or chapter number] -->

# UNIX Network Programming, Volume 2: Interprocess Communications (2nd ed.)
**Author**: W. Richard Stevens | **Pages**: ~564 | **Chapters**: 16 + App A/B | **Generated**: 2026-10-06

## How to Use This Skill

- **Without arguments** — load core frameworks for reference
- **With a topic** — ask about `mq_notify`, `record locking`, `shared memory`; I find and read the relevant chapter
- **With chapter** — ask for `ch05`; I load that specific chapter
- **Browse** — ask "what chapters do you have?" to see the full index

When you ask about a topic not covered in Core Frameworks below, I will read
the relevant chapter file before answering.

---

## Core Frameworks & Mental Models

**The four IPC forms** (Stevens's own taxonomy): message passing (pipes, FIFOs, message queues), synchronization (mutexes, condition variables, read-write locks, record locks, semaphores), shared memory (anonymous and named), and remote procedure calls (doors, Sun RPC). Use this taxonomy to choose a mechanism before writing any IPC code.

**Persistence taxonomy** (Ch 1, Fig 1.3) — the first question to ask about any IPC object:
- *Process-persistent* (pipes, FIFOs, sockets): dies with last process holding it
- *Kernel-persistent* (System V IPC, Posix MQ/sem/shm): survives until reboot or explicit removal
- *Filesystem-persistent* (FIFO name, mmap'd file): survives reboot
Combine with the fork/exec/exit effect table (Fig 1.6) to reason about object lifecycles.

**Prefer Posix over System V when both exist** — Posix IPC has cleaner names (pathname-like, px_ipc_name), better permission semantics, and mq_notify/semaphore APIs that map onto mutex+condvar; System V wins only on universal availability (Ch 2, 3, 10 vs 6, 11, 14).

**Locking versus waiting** (Ch 7) — a mutex alone cannot make a thread wait for a condition; pair it with a condition variable. Always recheck the predicate with `while` after `pthread_cond_wait` returns (spurious wakeups + signaling before waiting).

**Producer-consumer with counting resources** (Ch 7, 10) — model a buffer with one binary semaphore/mutex (exclusion) plus two counting semaphores (`nempty = nbuffers`, `nstored = 0`): wait on mutex + one counter, signal both on completion. Same structure scales from threads (condvars) to processes (shared memory + process-shared primitives).

**Read-write locks when readers dominate** (Ch 8) — implement with one mutex + two condvars (one for readers waiting, one for writers); handle writer starvation explicitly with a waiting-writers counter. Only worth it when reads vastly outnumber writes.

**Implement IPC from first principles to understand it** (Ch 5, 8, 10, 11) — Stevens builds Posix message queues, read-write locks, and semaphores out of mmap + process-shared mutex/condvar, and System V semaphores out of FIFOs/mmap/SysV. Use these implementations as the definitive worked examples of each primitive's semantics.

**Shared memory = fastest, synchronization = mandatory** (Ch 12–14) — mmap (MAP_SHARED) or shm objects give zero-copy sharing; every shared data structure needs a process-shared mutex/condvar/semaphore stored *in* the shared region (PTHREAD_PROCESS_SHARED attribute). Store offsets, never pointers (addresses differ per process).

**Measure, don't guess** (App A) — bandwidth programs (vary message size, one-way) and latency programs (ping-pong, 1-byte round trips) are the standard tools; shared memory with a mutex is fastest, message-passing cost grows with system-call overhead, RPC adds marshaling.

---

## Chapter Index

| # | Title | Key Frameworks |
|---|-------|----------------|
| [ch01](chapters/ch01-introduction.md) | Introduction | persistence taxonomy, name spaces, fork/exec/exit effects, wrapper functions |
| [ch02](chapters/ch02-posix-ipc.md) | Posix IPC | IPC names, px_ipc_name, oflag create-or-open rules, permission test |
| [ch03](chapters/ch03-systemv-ipc.md) | System V IPC | key_t/ftok, ipc_perm, identifier reuse, ipcs/ipcrm, kernel limits |
| [ch04](chapters/ch04-pipes-fifos.md) | Pipes and FIFOs | pipe+fork, popen/pclose, mkfifo, O_NONBLOCK semantics, PIPE_BUF atomicity, framing |
| [ch05](chapters/ch05-posix-message-queues.md) | Posix Message Queues | mq_open family, mq_attr, mq_notify rules, realtime signals, mmap implementation |
| [ch06](chapters/ch06-systemv-message-queues.md) | System V Message Queues | msgget/msgsnd/msgrcv/msgctl, msqid_ds, type multiplexing, kernel limits |
| [ch07](chapters/ch07-mutexes-condition-variables.md) | Mutexes and Condition Variables | locking vs waiting, condvar wait/signal idiom, pshared attributes |
| [ch08](chapters/ch08-read-write-locks.md) | Read-Write Locks | rwlock family, mutex+2-condvar implementation, thread cancellation |
| [ch09](chapters/ch09-record-locking.md) | Record Locking | fcntl F_SETLK/F_GETLK, flock struct, advisory vs mandatory, daemon single-instance |
| [ch10](chapters/ch10-posix-semaphores.md) | Posix Semaphores | named vs memory-based, sem_wait/sem_post, producer-consumer, from-scratch impl |
| [ch11](chapters/ch11-systemv-semaphores.md) | System V Semaphores | semget/semop/semctl, sembuf, SEM_UNDO, create/init race fix |
| [ch12](chapters/ch12-shared-memory-intro.md) | Shared Memory Introduction | mmap/munmap/msync, anonymous mappings, /dev/zero mapping |
| [ch13](chapters/ch13-posix-shared-memory.md) | Posix Shared Memory | shm_open/shm_unlink, ftruncate, shared counter, message passing via shm |
| [ch14](chapters/ch14-systemv-shared-memory.md) | System V Shared Memory | shmget/shmat/shmdt/shmctl, limits |
| [ch15](chapters/ch15-doors.md) | Doors | door_call/door_create, server thread pools, door_server_create, descriptor passing |
| [ch16](chapters/ch16-sun-rpc.md) | Sun RPC | rpcgen, XDR, binding, auth flavors, timeout/retry, call semantics |
| [ch17](chapters/ch17-performance-measurements.md) | Performance Measurements (App A) | bandwidth/latency programs, IPC mechanism comparison results |
| [ch18](chapters/ch18-threads-primer.md) | A Threads Primer (App B) | pthread_create/join/self/exit, detach, shared vs per-thread state |

## Topic Index

- **advisory vs mandatory locking** → ch09
- **bandwidth / latency measurement** → ch17
- **bounded buffer / producer-consumer** → ch07, ch10, ch12, ch13
- **condition variables** → ch07 (basics), ch05 (mq_notify use)
- **deadlock** → ch04 (FIFO open order), ch10 (semaphore ordering)
- **descriptor passing** → ch15
- **doors** → ch15
- **fork/exec/exit effects on IPC** → ch01
- **ftok / key_t / ipc_perm** → ch03
- **framing a byte stream** → ch04, ch05
- **full-duplex channels** → ch04 (pipes), ch15 (doors)
- **ipc limits (kernel)** → ch03, ch05, ch06, ch10, ch11, ch14
- **mandatory locking** → ch09
- **mmap / MAP_SHARED / msync** → ch05, ch12, ch13
- **mq_notify / realtime signals** → ch05
- **msgsnd/msgrcv message types** → ch06
- **mutex / locking vs waiting** → ch07
- **named vs unnamed objects** → ch05 (sem_open vs sem_init), ch12 vs ch13
- **O_NONBLOCK** → ch04, ch05, ch06
- **popen / pclose** → ch04
- **Posix vs System V comparison** → ch02/ch03, ch05/ch06, ch10/ch11, ch13/ch14, ch17
- **priority: readers vs writers** → ch08, ch09
- **process-shared synchronization** → ch07, ch08, ch10, ch12, ch13
- **read-write locks** → ch08, ch09
- **record locking / fcntl** → ch09
- **RPC / rpcgen / XDR / auth** → ch16
- **semaphores** → ch10 (Posix), ch11 (System V)
- **server design: iterative vs concurrent** → ch04, ch05, ch06
- **shared memory** → ch12, ch13, ch14
- **SIGEV notification / realtime signals** → ch05
- **single daemon instance** → ch09
- **thread cancellation / cleanup** → ch08, ch18
- **threads basics** → ch18
- **wrapper functions / error handling** → ch01

## Supporting Files

- [glossary.md](glossary.md) — all key terms with definitions
- [patterns.md](patterns.md) — all techniques and design patterns
- [cheatsheet.md](cheatsheet.md) — quick reference tables and decision guides

---

## Scope & Limits

This skill covers the book content only (single-host IPC; sockets are Volume 1). Appendix C (unpipc.h source) and Appendix D (exercise solutions) are not chapter-ized; the essential wrapper functions appear in ch01. Combine with project-specific tooling for hands-on implementation.
