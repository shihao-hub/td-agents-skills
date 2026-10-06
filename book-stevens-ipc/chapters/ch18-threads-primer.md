# Chapter 18: A Threads Primer (Appendix B)

## Core Idea
Threads ("lightweight processes") solve the two big problems of the fork-a-child model: fork is expensive (memory/descriptor duplication, even with copy-on-write) and post-fork IPC is needed to return information. Thread creation is 10–100× faster than process creation, and all threads in a process share global memory — making sharing trivial at the price of needing synchronization. This appendix distills the five basic Pthread functions needed for the rest of the book.

## Frameworks Introduced
- **Shared vs per-thread state model**: a precise inventory of what is process-wide versus thread-private.
- **Five-function core API**: `pthread_create`, `pthread_join`, `pthread_self`, `pthread_detach`, `pthread_exit` — mapped one-to-one onto the familiar process analogues (`fork`, `waitpid`, `getpid`, daemon, `_exit`).
- **Error-convention rule for Pthreads**: functions return 0 on success or the positive `Exxx` error code directly; they do not set `errno`.

## Key Concepts
- Shared by all threads in a process: process instructions, most data (global memory), open file descriptors, signal handlers and dispositions, current working directory, user and group IDs.
- Private to each thread: thread ID, register set (PC, stack pointer), stack, `errno`, signal mask, priority.
- Per-thread `errno` is what makes it safe to call errno-based library functions from multiple threads.
- `pthread_t` thread ID is process-local (unlike a PID); no analogue of `waitpid(-1)` — you must wait for a specific thread.
- Joinable (default) vs detached threads: a joinable thread's ID and exit status are retained until joined; a detached thread releases all resources on termination and cannot be waited for. Detach when no one needs to know; leave joinable otherwise.
- Three ways a thread terminates: return of the start function (return value = exit status); `pthread_exit`; process-wide termination when `main` returns or any thread calls `exit`/`_exit` (kills all threads immediately).
- `func`/`arg` protocol: one `void *` in, one `void *` out; package multiple arguments in a struct and pass its address.

## Mental Models
- Translation table: `pthread_create`↔`fork`, `pthread_join`↔`waitpid`, `pthread_self`↔`getpid`, detached thread↔daemon process, start-function return↔`_exit`.
- A thread = "shared everything, except a private register set + stack + errno + signal mask + priority."
- Pthread error handling = check return value against 0/`Exxx`, not `errno`/`-1`.

## Anti-patterns
- Checking `errno` after Pthread calls, or expecting `-1` returns — the error code *is* the return value.
- Passing a pointer to a thread-local (automatic) variable as `pthread_exit`'s status — the object vanishes when the thread terminates.
- Joining a detached thread (or detaching then joining) — resources are already gone.
- Assuming a `waitpid(-1)`-style "wait for any thread" exists — it does not.
- Leaking joinable threads you never join: their IDs and status are retained forever.
- Calling `exit` from a worker thread to end just that thread — it kills the whole process, including running threads.

## Code Examples
```c
int pthread_create(pthread_t *tid, const pthread_attr_t *attr,
                   void *(*func)(void *), void *arg);
/* Returns: 0 if OK, positive Exxx on error. attr = NULL for defaults. */

int pthread_join(pthread_t tid, void **status);   /* like waitpid */
/* Returns: 0 if OK, positive Exxx on error. *status gets thread's return value. */

pthread_t pthread_self(void);                     /* like getpid */

int pthread_detach(pthread_t tid);                /* common idiom: */
pthread_detach(pthread_self());                   /* self-detach */

void pthread_exit(void *status);                  /* does not return to caller */
```
Typical creation pattern: define `void *worker(void *arg)`, package extra arguments into a struct, `pthread_create(&tid, NULL, worker, &args)`, later `pthread_join(tid, &status)` — or have the worker call `pthread_detach(pthread_self())` first thing and return when done.

## Worked Example (bandwidth/latency measurement methodology)
N/A for this appendix — it is a pure API primer. Its content is exercised implicitly by Appendix A's thread synchronization benchmarks (Ch. 17), which create 1–5 threads with `pthread_create`, drive them from a locked release point, and collect them with `pthread_join`.

## Key Takeaways
1. Threads fix fork's two costs: creation expense and mandatory IPC for return values.
2. Sharing is automatic (global memory) but demands synchronization (Part 2 of the book).
3. Memorize the shared-vs-private lists — they define exactly what state races need protection.
4. Five functions cover the basics: create, join, self, detach, exit.
5. Pthreads return error codes, not `errno` — a different convention from nearly all other Unix APIs.
6. `main` returning or any `exit` call terminates every thread in the process.

## Connects To
- Ch. 7 (mutexes & condition variables — the synchronization this primer foreshadows), Ch. 8 (read-write locks).
- Ch. 17 / Appendix A (thread creation/join used in the synchronization benchmarks).
- `pthread_attr_t` attributes (stack size, priority, process-shared) introduced as needed in Chapters 7–8.
