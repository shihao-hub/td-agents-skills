# Chapter 7: Mutexes and Condition Variables

## Core Idea
A mutex is for locking (mutual exclusion around shared data) and a condition variable is for waiting (sleeping until some condition becomes true); both are the fundamental building blocks of Posix.1 thread synchronization, and both can also synchronize processes when stored in shared memory with the process-shared attribute.

## Frameworks Introduced
- **Mutex lock/unlock protocol** — `pthread_mutex_lock` → critical region → `pthread_mutex_unlock`. Use to serialize threads' access to shared data; `pthread_mutex_trylock` (returns `EBUSY`) for nonblocking attempts.
- **Condition variable wait/signal protocol** — wait: lock mutex, `while (condition false) pthread_cond_wait`; signal: lock mutex, set condition, `pthread_cond_signal`, unlock. Use when a thread must sleep until a predicate holds.
- **Producer-consumer (bounded buffer)** — the classic synchronization problem; solved here with a shared buffer + mutex (+ condition variable in the evolved version), and again with semaphores in Chapter 10.

## Key Concepts
- `pthread_mutex_t` / `pthread_cond_t`: the two synchronization datatypes; statically initialize with `PTHREAD_MUTEX_INITIALIZER` / `PTHREAD_COND_INITIALIZER`.
- Mutexes protect data, not code: what's really protected is the shared data manipulated in the critical region.
- Mutex locks are cooperative: nothing stops a rogue thread from touching shared data without locking.
- `pthread_cond_wait(cptr, mptr)` atomically unlocks the mutex and sleeps; it relocks the mutex before returning.
- Spurious wakeups can occur — always retest the condition in a `while` loop after `pthread_cond_wait` returns.
- `pthread_cond_signal` wakes one waiter; `pthread_cond_broadcast` wakes all; `pthread_cond_timedwait` bounds the wait (absolute `timespec`, returns `ETIMEDOUT`).
- Process-shared attribute (`PTHREAD_PROCESS_SHARED` vs `PTHREAD_PROCESS_PRIVATE`) via `pthread_mutexattr_setpshared`/`pthread_condattr_setpshared`, needs `_POSIX_THREAD_PROCESS_SHARED`.
- Error convention: these functions return 0 on OK, a positive `Exxx` value on error (not −1/errno).
- Locks are not auto-released on process termination — only `fcntl` record locks always are (System V semaphores: optional via `SEM_UNDO`).

## Mental Models
- Use a **mutex** when the problem is mutual exclusion ("only one thread at a time touches this data").
- Use a **condition variable** when the problem is waiting ("sleep until this predicate is true") — never spin/poll on a mutex.
- Use **signal-after-unlock** (`dosignal` flag pattern) to avoid the awakened thread immediately stalling on a still-held mutex; Posix allows signaling without owning the mutex.
- Use **broadcast by default**; treat `signal` as an optimization only when all waiters are identically coded and exactly one should wake.

## Anti-patterns
- **Omitting the initializer** for a statically allocated mutex/cond because "zero works on this system" — incorrect code; use the `PTHREAD_*_INITIALIZER` constants.
- **Spinning/polling on a mutex** (lock, test, unlock, loop) to wait for a condition — wastes CPU; that's what condition variables are for.
- **Testing the condition with `if` instead of `while`** around `pthread_cond_wait` — spurious wakeups make the recheck mandatory.
- **Checking the return values as −1/errno** — these functions return the error code directly; wrap them accordingly.
- **Locking more than necessary**: minimize code inside a critical region (e.g., per-thread counters stay outside the lock).
- **Assuming kernel cleanup of a held mutex** on process death — it never happens, and even if released, data mid-update may be inconsistent; only fcntl record locks are auto-released.
- **Forgetting `set_concurrency`/`pthread_setconcurrency`** on M-to-N thread implementations (Solaris) — only the first thread runs.

## Code Examples
```c
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;  /* static init idiom */

int pthread_mutex_lock(pthread_mutex_t *mptr);
int pthread_mutex_trylock(pthread_mutex_t *mptr);   /* EBUSY if already locked */
int pthread_mutex_unlock(pthread_mutex_t *mptr);

int pthread_cond_wait(pthread_cond_t *cptr, pthread_mutex_t *mptr);
int pthread_cond_signal(pthread_cond_t *cptr);
int pthread_cond_broadcast(pthread_cond_t *cptr);
int pthread_cond_timedwait(pthread_cond_t *cptr, pthread_mutex_t *mptr,
                           const struct timespec *abstime);  /* ETIMEDOUT */
```
Exact signatures of the lock and wait families (all return 0 if OK, positive Exxx on error).

```c
/* Avoiding lock conflicts: signal only after releasing the mutex */
int dosignal;
Pthread_mutex_lock(&nready.mutex);
dosignal = (nready.nready == 0);
nready.nready++;
Pthread_mutex_unlock(&nready.mutex);
if (dosignal)
    pthread_cond_signal(&nready.cond);
```

## Reference Tables

### Mutex + condition variable function families (<pthread.h>)
| Function | Purpose |
|---|---|
| `pthread_mutex_init(mptr, attr)` / `pthread_mutex_destroy(mptr)` | dynamic init/destroy (attr NULL = defaults) |
| `pthread_mutex_lock` / `pthread_mutex_trylock` / `pthread_mutex_unlock` | lock (blocking) / lock (nonblocking, EBUSY) / unlock |
| `pthread_mutexattr_init` / `pthread_mutexattr_destroy` | init/destroy mutex attributes |
| `pthread_mutexattr_getpshared(attr, valptr)` / `pthread_mutexattr_setpshared(attr, value)` | fetch/set process-shared attribute |
| `pthread_cond_init(cptr, attr)` / `pthread_cond_destroy(cptr)` | dynamic init/destroy |
| `pthread_condattr_init` / `pthread_condattr_destroy` | init/destroy cond attributes |
| `pthread_condattr_getpshared` / `pthread_condattr_setpshared` | same attribute for condition variables |
| `pthread_cond_wait` / `pthread_cond_timedwait` | sleep on condition (optionally bounded by absolute time) |
| `pthread_cond_signal` / `pthread_cond_broadcast` | wake one / all waiters |

pshared values: `PTHREAD_PROCESS_PRIVATE` (default) or `PTHREAD_PROCESS_SHARED` (requires `_POSIX_THREAD_PROCESS_SHARED`; optional in Posix.1, required by Unix 98). Shared-memory footprint: `sizeof(pthread_mutex_t)`.

### timespec for timedwait
| Field | Meaning |
|---|---|
| `time_t tv_sec` | seconds past Jan 1, 1970 UTC (absolute, not a delta) |
| `long tv_nsec` | nanoseconds |

## Worked Example: the wait/signal idiom with while-loop recheck
```c
/* Shared state: gather data + sync variables into one struct (good technique) */
struct {
    pthread_mutex_t mutex;
    pthread_cond_t  cond;
    int nready;               /* number of items ready for consumer */
} nready = { PTHREAD_MUTEX_INITIALIZER, PTHREAD_COND_INITIALIZER };

/* Producer: set condition true and signal (optimization: signal only 0->1) */
Pthread_mutex_lock(&nready.mutex);
if (nready.nready == 0)
    pthread_cond_signal(&nready.cond);
nready.nready++;
Pthread_mutex_unlock(&nready.mutex);

/* Consumer: wait for condition — while() recheck guards spurious wakeups */
Pthread_mutex_lock(&nready.mutex);
while (nready.nready == 0)
    Pthread_cond_wait(&nready.cond, &nready.mutex);  /* atomically: unlock + sleep; relock on return */
nready.nready--;                                     /* mutex held here */
Pthread_mutex_unlock(&nready.mutex);
```
General shapes:
```c
/* Signaler */                          /* Waiter */
Pthread_mutex_lock(&var.mutex);         Pthread_mutex_lock(&var.mutex);
set condition true                      while (condition is false)
pthread_cond_signal(&var.cond);             Pthread_cond_wait(&var.cond, &var.mutex);
Pthread_mutex_unlock(&var.mutex);       modify condition;
                                        Pthread_mutex_unlock(&var.mutex);
```

## Key Takeaways
- Lock with mutexes, wait with condition variables — they solve different problems and both are usually needed together.
- Always retest the condition in a `while` loop after `pthread_cond_wait` (spurious wakeups are permitted).
- Group shared data with its synchronization variables in one struct to make the locking discipline visible.
- Dynamically allocated or shared-memory mutexes must be initialized at run time with `pthread_mutex_init` (and `PTHREAD_PROCESS_SHARED` for cross-process use).
- `pthread_cond_timedwait` takes an absolute time — safe to retry after an interruption without recomputing the timespec.
- Prefer `broadcast` unless you can prove `signal` suffices; treat `signal` as an optimization.
- No synchronization primitive except fcntl record locks is released automatically on process termination — plan for lock-holding crashes.

## Connects To
- Ch 5 (process-shared mutex/cond used to implement Posix message queues, Fig 5.22); Ch 8 (read-write locks — broadcast wakes all readers; cancellation cleanup handlers); Ch 9 (fcntl record locks, the only kernel-cleaned lock); Ch 10 (semaphore solution to producer-consumer); Ch 11 (System V semaphores, SEM_UNDO); Ch 12/14 (shared memory, prerequisite for process-shared mutexes).
