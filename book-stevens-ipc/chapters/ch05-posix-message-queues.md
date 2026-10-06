# Chapter 5: Posix Message Queues

## Core Idea
A message queue is a kernel-persistent linked list of prioritized messages: any thread with permission can put messages on or take messages off, with no reader required to exist before a writer — unlike pipes and FIFOs, whose data dies with the last descriptor close.

## Frameworks Introduced
- **Posix MQ API** (`mq_open`/`mq_send`/`mq_receive`/`mq_getattr`/`mq_setattr`/`mq_close`/`mq_unlink`) — use when you need prioritized, record-oriented, persistent messaging between unrelated processes.
- **Asynchronous event notification** (`mq_notify` + `struct sigevent`) — use when you must not block in `mq_receive` nor poll; system tells you when a queue goes empty → non-empty (signal or spawned thread).
- **Realtime signals** (SIGRTMIN–SIGRTMAX, `SA_SIGINFO`, `sigqueue`, `sigwait`) — queued, FIFO-ordered, information-carrying signals; needed to understand `mq_notify`'s signal path.
- **Build-it-yourself IPC from lower primitives** (mmap + process-shared mutex/condvar) — Stevens' demonstration that "kernel" IPC is implementable in ~500 lines of user code.

## Key Concepts
- **Message**: a record with an unsigned priority, a length (may be 0), and data.
- **Kernel persistence**: queue + messages survive even when no process has it open, until `mq_unlink` and last close.
- **mqd_t**: message queue descriptor — need not be a small integer; often a pointer (Solaris: `void*`).
- **Delivery rule**: `mq_receive` always returns the *oldest message of the highest priority*.
- **mq_maxmsg / mq_msgsize**: fixed at creation; buffer for `mq_receive` must be ≥ `mq_msgsize` or `EMSGSIZE`.
- **MQ_PRIO_MAX**: upper bound on priority + 1; Posix requires ≥ 32 (Solaris 32, Digital Unix 256).
- **mq_notify rules**: empty→non-empty edge trigger; one registered process per queue; registration consumed on each notification; blocking `mq_receive` takes precedence.
- **Async-signal-safe**: only functions on the Posix list (e.g. `write`, `read`, `sem_post`) may run in a signal handler — `printf` and all `pthread_*` may not.
- **Realtime signal behavior**: queued, per-signal FIFO delivery, lowest-numbered RT signal delivered first, handler gets `(signo, siginfo_t*, void*)` when `SA_SIGINFO` is set.
- **SIGEV_THREAD**: `mq_notify` can start a (detached) thread function instead of sending a signal.

## Mental Models
- Use a **message queue** when senders and receivers live at different times (queue outlives both) or priorities matter.
- Use **pipes/FIFOs** when a byte stream between concurrently-open endpoints suffices — queues carry record boundaries and priorities, streams don't.
- Use **sigwait + nonblocking mq_receive** when waiting on a queue from a thread — synchronous wait for an async event beats a signal handler setting flags.
- Use **mq_notify + a pipe written from the handler** when you must multiplex the queue with `select`/`poll` (mqd_t is not a normal descriptor).

## Anti-patterns
- Calling `mq_notify`/`mq_receive`/`printf` from a signal handler — none are async-signal-safe (Fig 5.9's bug).
- Reregistering after reading instead of **before** — a second message arriving while you read is silently missed (notification only fires on empty→non-empty).
- Blocking `mq_receive` while registered for notification — blocking receive takes precedence; notification never fires.
- Assuming two notifications for two back-to-back messages — always drain the queue nonblocking after each notification (`EAGAIN` = done).
- Trusting sender identity embedded in a message — senders can lie; IPC messages don't authenticate (doors/credentials do).
- Assuming mqd_t works with `select`/`poll` or is an fd — it isn't.

## Code Examples
```c
/* open/create, read one message — the canonical usage skeleton */
mqd_t mqd = mq_open("/queue", O_RDONLY);
struct mq_attr attr;  mq_getattr(mqd, &attr);
char *buff = malloc(attr.mq_msgsize);
unsigned prio;
ssize_t n = mq_receive(mqd, buff, attr.mq_msgsize, &prio); /* oldest, highest priority */
```
```c
/* notification: reregister FIRST, then drain nonblocking */
sigev.sigev_notify = SIGEV_SIGNAL;  sigev.sigev_signo = SIGUSR1;
mq_notify(mqd, &sigev);
while ((n = mq_receive(mqd, buff, attr.mq_msgsize, NULL)) >= 0) { /* ... */ }
/* errno == EAGAIN means queue drained */
```
```c
/* sigwait variant: no handler at all */
sigprocmask(SIG_BLOCK, &newmask, NULL);   /* block SIGUSR1 first */
Sigwait(&newmask, &signo);                /* synchronous wait */
mq_notify(mqd, &sigev);                   /* reregister, drain nonblocking */
```

## Reference Tables

**struct mq_attr**
| Field | Meaning | Settable |
|---|---|---|
| mq_flags | 0 or O_NONBLOCK | via mq_setattr (per-open) |
| mq_maxmsg | max #messages on queue | only at creation |
| mq_msgsize | max message bytes | only at creation |
| mq_curmsgs | messages currently queued | read-only |

Default (Solaris): 128 msgs × 1024 bytes. File size ≈ product + ~8 bytes/msg overhead.

**mq_open oflags**: O_RDONLY, O_WRONLY, O_RDWR; | O_CREAT (mode+attr args required), O_EXCL, O_NONBLOCK. Errors: EEXIST, EMSGSIZE, EAGAIN, EBUSY (2nd registrant), ETIMEDOUT.

**Limits** (via `sysconf`): MQ_OPEN_MAX (≥8), MQ_PRIO_MAX (≥32); realtime signals SIGRTMIN..SIGRTMAX (≥8, RTSIG_MAX).

**mq_notify rules**
| # | Rule |
|---|---|
| 1 | Nonnull notification → register process for empty-queue arrival |
| 2 | NULL notification → unregister existing registration |
| 3 | Only one process registered per queue (else EBUSY) |
| 4 | Notification suppressed if any thread blocked in mq_receive on that queue |
| 5 | Registration is one-shot: consumed when fired; must reregister |

**sigevent**: SIGEV_NONE / SIGEV_SIGNAL (sigev_signo + sigev_value) / SIGEV_THREAD (sigev_notify_function(union sigval), detached, attrs via sigev_notify_attributes). si_code SI_MESGQ identifies queue-originated signals.

## Worked Example: Posix MQ from mmap + mutex + condvar (Section 5.8)

One memory-mapped file per queue (`MAP_SHARED`), laid out: `mq_hdr` at offset 0, then mq_maxmsg slots each of `msg_hdr` + data padded to long alignment (`MSGSIZE` macro). Linked lists use **byte indexes from file start**, not pointers, because mappings differ per process.

```c
struct mq_hdr  { struct mq_attr mqh_attr; long mqh_head, mqh_free, mqh_nwait;
                 pid_t mqh_pid; struct sigevent mqh_event;
                 pthread_mutex_t mqh_lock; pthread_cond_t mqh_wait; };
struct msg_hdr { long msg_next; ssize_t msg_len; unsigned int msg_prio; }; /* data follows */
struct mq_info { struct mq_hdr *mqi_hdr; long mqi_magic; int mqi_flags; }; /* per-open, malloc'ed */
typedef struct mq_info *mqd_t;
```
- Two lists: `mqh_head` (queued messages, sorted highest priority first, FIFO within priority — so receive just pops the head) and `mqh_free` (empty slots).
- **mq_open create race**: open with O_EXCL|O_CREAT; creator sets the file's user-execute bit as "initialization in progress", maps, builds free list, initializes mutex/condvar with `PTHREAD_PROCESS_SHARED`, then `fchmod` clears the bit. Openers poll `stat` up to MAX_TRIES waiting for that bit to clear.
- **mq_send**: lock → if curmsgs==0 and registrant and nwait==0, `sigqueue` + unregister; if full, `pthread_cond_wait`; take free slot, copy data, insert into list at correct priority spot, if queue was empty `pthread_cond_signal`, curmsgs++.
- **mq_receive**: lock → if empty, nwait++, `pthread_cond_wait`, nwait--; pop head, copy out, push slot onto free list, if queue was full `pthread_cond_signal`, curmsgs--.
- **mq_notify**: stores pid in `mqh_pid` + sigevent in `mqh_event`; checks prior registrant alive via `kill(pid, 0)` (EBUSY if so). **mq_close**: unregister, `munmap`, zero magic, `free`. **mq_unlink**: just `unlink`.
- Acknowledged simplifications: EINTR on interrupted cond wait is not delivered; send insertion is O(n) list walk; SI_QUEUE si_code instead of SI_MESGQ.

## Key Takeaways
1. Queues give record boundaries, priorities, and kernel persistence; pipes give neither — pick by semantics, not habit.
2. Always `mq_getattr` after opening to size the receive buffer (`mq_msgsize`), or get `EMSGSIZE`.
3. Notification is edge-triggered and one-shot: reregister *before* reading, then drain nonblocking until `EAGAIN`.
4. Prefer `sigwait` (or `SIGEV_THREAD`) over async signal handlers; if you must select/poll, bridge with a pipe written from the handler.
5. Realtime behavior (queued, FIFO, siginfo) requires SIGRTMIN..SIGRTMAX *and* SA_SIGINFO.
6. "Kernel IPC" can be a mapped file plus process-shared mutex/condvar — the O_EXCL + magic-mode-bit creation race pattern recurs (Posix semaphores, Ch 10).

## Connects To
- Ch 2 (IPC names, `px_ipc_name`, mode/flag rules), Ch 4 (FIFOs — contrast: no persistence, no priorities)
- Ch 6 System V message queues (type-based selection vs priority ordering; no notification)
- Ch 7 mutexes & condition variables; Ch 10 Posix semaphores (same creation race)
- Ch 12/13 memory-mapped I/O (`mmap`, `MAP_SHARED`, process-shared pshared attributes)
- Ch 15 doors (sender identification, which message queues lack)
