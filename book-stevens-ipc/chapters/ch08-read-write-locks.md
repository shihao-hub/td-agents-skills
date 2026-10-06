# Chapter 8: Read-Write Locks

## Core Idea
A read-write lock (shared/exclusive lock) allows any number of threads to hold the lock for reading simultaneously, but grants a write lock only when no thread holds it for reading or writing — giving more concurrency than a mutex when data is read far more often than it is written.

## Frameworks Introduced
- **Read-Write Lock (shared-exclusive locking / readers-writer lock)** — Use when the critical region is read-dominant. Readers share; writers exclude all. Bank-account analogy: many threads may read a balance concurrently; an updater must wait for all readers and then exclude readers until done.
- **Unix 98 rwlock API (pthread_rwlock_*)** — Obtain/release: `pthread_rwlock_rdlock`, `pthread_rwlock_wrlock`, `pthread_rwlock_unlock`. Non-blocking variants return `EBUSY` instead of sleeping: `pthread_rwlock_tryrdlock`, `pthread_rwlock_trywrlock`. Statically initialized with `PTHREAD_RWLOCK_INITIALIZER`; dynamically with `pthread_rwlock_init` / `pthread_rwlock_destroy`. Attributes via `pthread_rwlockattr_init/destroy`; the only attribute is `PTHREAD_PROCESS_SHARED` (set/get with `pthread_rwlockattr_setpshared/getpshared`, values `PTHREAD_PROCESS_PRIVATE` or `PTHREAD_PROCESS_SHARED`) to share the lock across processes via shared memory.
- **Writer-preference policy** — When a writer waits, new readers are blocked too, so a continuous stream of read requests cannot starve a pending writer. Alternative implementations prefer readers (e.g., Butenhof 1997 §7.1.2); the choice is policy, not law.

## Key Concepts
- Shared lock = read lock; exclusive lock = write lock; only one writer, and zero readers while a writer holds the lock.
- `pthread_rwlock_t` — the lock datatype; manipulate only through the API.
- `rw_refcount` state encoding: −1 = writer holds lock, 0 = available, >0 = number of concurrent readers.
- `pthread_rwlock_tryrdlock/trywrlock` — return `EBUSY` immediately if the lock cannot be granted.
- `PTHREAD_RWLOCK_INITIALIZER` — static initialization for statically allocated locks.
- Writer priority: readers queue behind waiting writers to prevent writer starvation.
- `pthread_cond_signal` wakes one writer; `pthread_cond_broadcast` wakes all waiting readers.
- Thread cancellation: a thread blocked in `pthread_cond_wait` can be canceled by any thread's `pthread_cancel(tid)`; the mutex is reacquired before cleanup handlers run.
- Cleanup handlers (`pthread_cleanup_push/pop`) restore state (unlock mutex, fix counters) on cancellation or voluntary exit.

## Mental Models
- Use a read-write lock when reads vastly outnumber writes and the critical section is long enough to amortize the extra overhead; otherwise a plain mutex is often as fast.
- Use try-variants when the code can do useful work instead of blocking.
- Use `PTHREAD_PROCESS_SHARED` + shared memory when unrelated-thread/process sharing is needed.
- Use cleanup handlers around any `pthread_cond_wait` that may be canceled, to keep internal counters and mutexes consistent.

## Anti-patterns
- **Unbounded reader admission** — granting new read locks while a writer waits starves writers indefinitely; use a writer-preference check (`rw_nwaitwriters > 0` blocks new readers).
- **Cancellation without cleanup** — a thread canceled inside `pthread_cond_wait` dies holding the internal mutex; every subsequent lock operation deadlocks. Fix with `pthread_cleanup_push` handlers that decrement the waiter counter and unlock the mutex.
- **Collapsing the two unlock tests into one `if`** (`nwaitwriters > 0 && refcount == 0` … else readers) — subtle: omitting the refcount guard produces spurious signals while readers still hold the lock; the book's two-step form is correct and efficient.
- Assuming attribute support in hand-rolled implementations (the sample returns `EINVAL` for non-NULL `attr`).

## Code Examples
```c
/* Writer-preference rdlock core: block while a writer holds or wants the lock */
pthread_mutex_lock(&rw->rw_mutex);
while (rw->rw_refcount < 0 || rw->rw_nwaitwriters > 0) {
    rw->rw_nwaitreaders++;
    pthread_cleanup_push(rwlock_cancelrdwait, (void *) rw);
    result = pthread_cond_wait(&rw->rw_condreaders, &rw->rw_mutex);
    pthread_cleanup_pop(0);
    rw->rw_nwaitreaders--;
    if (result != 0) break;
}
if (result == 0)
    rw->rw_refcount++;          /* another reader holds the lock */
pthread_mutex_unlock(&rw->rw_mutex);
```
Demonstrates the read-lock loop with cancellation-safe cleanup handlers bracketing `pthread_cond_wait`.

```c
/* Unlock: prefer waiting writers, else wake all readers */
if (rw->rw_nwaitwriters > 0) {
    if (rw->rw_refcount == 0)
        result = pthread_cond_signal(&rw->rw_condwriters);   /* one writer */
} else if (rw->rw_nwaitreaders > 0)
    result = pthread_cond_broadcast(&rw->rw_condreaders);    /* all readers */
```
Demonstrates the release-time arbitration between waiters.

## Reference Tables

| Function | Action | Returns |
|---|---|---|
| `int pthread_rwlock_rdlock(pthread_rwlock_t *rwptr)` | acquire shared read lock (blocks) | 0 OK, positive Exxx on error |
| `int pthread_rwlock_wrlock(pthread_rwlock_t *rwptr)` | acquire exclusive write lock (blocks) | 0 / Exxx |
| `int pthread_rwlock_unlock(pthread_rwlock_t *rwptr)` | release either lock type | 0 / Exxx |
| `int pthread_rwlock_tryrdlock(pthread_rwlock_t *rwptr)` | nonblocking read lock | 0 or `EBUSY` |
| `int pthread_rwlock_trywrlock(pthread_rwlock_t *rwptr)` | nonblocking write lock | 0 or `EBUSY` |
| `int pthread_rwlock_init(pthread_rwlock_t *rwptr, const pthread_rwlockattr_t *attr)` | dynamic init (`attr==NULL` = defaults) | 0 / Exxx |
| `int pthread_rwlock_destroy(pthread_rwlock_t *rwptr)` | destroy (`EBUSY` if in use/waiters) | 0 / Exxx |
| `int pthread_rwlockattr_init/destroy(pthread_rwlockattr_t *attr)` | attribute object lifecycle | 0 / Exxx |
| `int pthread_rwlockattr_getpshared(const pthread_rwlockattr_t *attr, int *valptr)` | get sharing attribute | 0 / Exxx |
| `int pthread_rwlockattr_setpshared(pthread_rwlockattr_t *attr, int value)` | set `PTHREAD_PROCESS_PRIVATE`/`SHARED` | 0 / Exxx |

| Struct member | Role |
|---|---|
| `rw_mutex` | mutex guarding the whole structure |
| `rw_condreaders` | condvar for blocked readers |
| `rw_condwriters` | condvar for blocked writers |
| `rw_magic` | `RW_MAGIC` validates an initialized lock |
| `rw_nwaitreaders` / `rw_nwaitwriters` | counts of blocked waiters |
| `rw_refcount` | −1 writer, 0 free, >0 #readers |

## Worked Example — rwlock from mutex + 2 condvars
```c
typedef struct {
    pthread_mutex_t rw_mutex;        /* basic lock on this struct */
    pthread_cond_t  rw_condreaders;  /* for reader threads waiting */
    pthread_cond_t  rw_condwriters;  /* for writer threads waiting */
    int rw_magic;                    /* for error checking */
    int rw_nwaitreaders;             /* number waiting */
    int rw_nwaitwriters;             /* number waiting */
    int rw_refcount;                 /* -1 if writer has lock, else # readers */
} pthread_rwlock_t;

/* wrlock: wait until refcount == 0, then set it to -1 */
while (rw->rw_refcount != 0) {
    rw->rw_nwaitwriters++;
    pthread_cleanup_push(rwlock_cancelwrwait, (void *) rw);
    result = pthread_cond_wait(&rw->rw_condwriters, &rw->rw_mutex);
    pthread_cleanup_pop(0);
    rw->rw_nwaitwriters--;
    if (result != 0) break;
}
if (result == 0)
    rw->rw_refcount = -1;

/* cancellation handlers */
static void rwlock_cancelrdwait(void *arg) { rw->rw_nwaitreaders--; pthread_mutex_unlock(&rw->rw_mutex); }
static void rwlock_cancelwrwait(void *arg) { rw->rw_nwaitwriters--; pthread_mutex_unlock(&rw->rw_mutex); }
```
The test program (reader holds lock, second thread blocks in `wrlock` and is canceled via `pthread_cancel`) hangs without the cleanup handlers — after the fix all three counters end at 0 and `pthread_rwlock_destroy` no longer returns `EBUSY`.

## Key Takeaways
- Reach for rwlocks only under read-mostly access patterns; the win is concurrency among readers.
- Encode lock state in one integer (`refcount`): −1/0/N covers writer/free/N-readers.
- Arbitrate at release time: signal one waiting writer first; broadcast to readers only when no writer waits.
- Bracket every potentially-canceled `pthread_cond_wait` with `pthread_cleanup_push/pop` that restores counters and unlocks the mutex.
- Static init via `PTHREAD_RWLOCK_INITIALIZER`; dynamic init must unwind already-initialized members on failure.
- The implementation is exactly mutex + two condition variables + counters — nothing magical.

## Connects To
- Chapter 7 (mutexes and condition variables — the building blocks)
- Chapter 9 (fcntl record locking: the process-level "read-write lock" on file byte ranges; writer/reader priority questions recur there)
