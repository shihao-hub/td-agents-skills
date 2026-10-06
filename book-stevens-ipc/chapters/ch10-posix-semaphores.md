# Chapter 10: Posix Semaphores

## Core Idea
A semaphore is a synchronization primitive whose value is atomically tested-and-decremented (wait) and incremented (post); Posix provides named semaphores (`sem_open`) and memory-based/unnamed semaphores (`sem_init`), both usable between threads or processes, with only -1/+1 operations.

## Frameworks Introduced
- **Binary semaphore**: value 0 or 1; used like a mutex for mutual exclusion (init to 1). No difference in system code vs counting semaphore.
- **Counting semaphore**: initialized to N = number of available resources (buffers); the count tracks resource availability.
- **Named semaphores**: identified by a Posix IPC name (often a pathname); kernel-persistent (value survives even with no process holding it open); for synchronizing unrelated processes.
- **Memory-based (unnamed) semaphores**: application allocates the `sem_t`; when `shared=1` must live in shared memory; persistence equals that of the containing memory.
- **Producer-consumer with three semaphores**: mutex (init 1), nempty (init NBUFF), nstored (init 0) — canonical pattern for circular buffers, multiple producers/consumers, and multiple buffering (double buffering is a special case).

## Key Concepts
- `sem_wait`: atomically test value > 0 and decrement; block if 0 (aka Dijkstra P, down, lock).
- `sem_post`: increment value, wake one waiter; atomic; may be called by a different thread than waiter (unlike mutex unlock).
- `sem_trywait`: nonblocking `sem_wait`; returns -1/EAGAIN if value is 0.
- `sem_getvalue`: return current value (implementations may return negative = count of waiters, or 0).
- `sem_open(name, oflag, /* mode_t mode, unsigned int value */)` returns `sem_t *` (SEM_FAILED on error); O_CREAT initializes only if it does not already exist.
- `sem_close`: close the semaphore (automatic on process termination); does not remove it.
- `sem_unlink`: remove name from system; destruction deferred until last close (reference counted, like file unlink).
- `sem_init(sem, shared, value)`: initialize caller-allocated memory-based semaphore; `shared!=0` requires it to be in shared memory; always initializes — call only once.
- `sem_destroy`: destroy a memory-based semaphore.
- Semaphore posts are remembered (state = count); condition-variable signals are lost if nobody waits.
- Limits: SEM_NSEMS_MAX (≥256), SEM_VALUE_MAX (≥32767), via `sysconf(_SC_SEM_VALUE_MAX)`.

## Mental Models
- Use a **binary semaphore** when you need mutex-like exclusion but the "unlock" (post) may come from a different thread/process than the "lock" (wait).
- Use **named semaphores** when unrelated processes must find the semaphore by name; use **memory-based semaphores** when threads share memory (or processes share a shared-memory region) and no name is needed.
- Use **counting semaphores** (nempty/nstored pair around a buffer) when coordinating producer/consumer over N slots — not just for mutual exclusion.
- Use semaphores (per Posix rationale) primarily for **interprocess** synchronization; mutexes + condvars for interthread; but use whichever fits.

## Anti-patterns
- Initializing a `sem_t` in ordinary (non-shared) memory then using it across `fork` — the child gets a copy, not shared memory; synchronization silently fails.
- Copying a `sem_t` datatype: Posix explicitly says references to copies are undefined (mmap-based implementations break).
- Calling `sem_init` more than once on the same semaphore — undefined.
- Swapping the two `sem_wait` calls (mutex before nstored) in the consumer — classic deadlock: producer holds mutex waiting for nempty, consumer holds mutex waiting for nstored.
- Assuming the kernel releases a held semaphore on process termination — it does NOT (unlike fcntl record locks); a crashed lock holder leaves the value at 0.
- Forgetting `sem_unlink` for named semaphores at program end — names persist (kernel-persistent).
- Relying on `sem_wait` detecting deadlock (EDEADLK is optional; Solaris/Digital Unix don't report it).

## Code Examples
```c
/* Producer-consumer core: circular buffer with 3 semaphores */
Sem_wait(&shared.nempty);   /* wait for >= 1 empty slot      */
Sem_wait(&shared.mutex);
shared.buff[i % NBUFF] = i; /* critical region               */
Sem_post(&shared.mutex);
Sem_post(&shared.nstored);  /* 1 more stored item            */
```
One-line: demonstrates the nempty/mutex/nstored triple that solves bounded-buffer coordination atomically.

```c
sem = Sem_open(px_ipc_name("mutex"), O_CREAT | O_EXCL, FILE_MODE, 1);
```
One-line: exclusive create of a named binary semaphore initialized to 1 (O_EXCL guarantees we are the initializer).

## Reference Tables

**Posix semaphore APIs (named vs memory-based):**
| Operation | Named | Memory-based |
|---|---|---|
| create/open | `sem_open` | `sem_init` |
| wait/trywait/post/getvalue | same functions | same functions |
| close/destroy | `sem_close` | `sem_destroy` |
| remove | `sem_unlink` | — |
| persistence | kernel-persistent | that of containing memory |

**Posix vs mutex/condvar:**
| Property | Mutex | Condition variable | Semaphore |
|---|---|---|---|
| unlock/post by other thread | no | — | yes |
| state | binary | none (signal lost) | count (post remembered) |

**Posix limits:** SEM_NSEMS_MAX ≥ 256; SEM_VALUE_MAX ≥ 32767.

## Worked Example
Stevens's from-scratch counting semaphore using a mutex + condition variable, memory-mapped so multiple processes share it (Section 10.15):

```c
typedef struct {
    pthread_mutex_t sem_mutex;   /* protect count           */
    pthread_cond_t  sem_cond;    /* signal 0 -> nonzero     */
    unsigned int    sem_count;   /* the semaphore value     */
    int             sem_magic;
} sem_t;

int sem_wait(sem_t *sem) {
    Pthread_mutex_lock(&sem->sem_mutex);
    while (sem->sem_count == 0)
        pthread_cond_wait(&sem->sem_cond, &sem->sem_mutex);
    sem->sem_count--;
    Pthread_mutex_unlock(&sem->sem_mutex);
    return 0;
}

int sem_post(sem_t *sem) {
    Pthread_mutex_lock(&sem->sem_mutex);
    if (sem->sem_count == 0)
        pthread_cond_signal(&sem->sem_cond);
    sem->sem_count++;
    Pthread_mutex_unlock(&sem->sem_mutex);
    return 0;
}
```
`sem_open` creates the file with the user-execute bit set (O_CREAT|O_EXCL, only the creator initializes: mutex/cond with PTHREAD_PROCESS_SHARED attributes, then `mmap` MAP_SHARED, then `fchmod` clears the execute bit). Openers poll `stat` until the execute bit is off — that is the race-free "initialized" signal. ~300 lines total; applications should not have to reinvent this. Alternative implementations: FIFO-based (semaphore value = bytes in FIFO; sem_post writes 1 byte, sem_wait reads 1) and System V-based (Section 10.16, one-member set; init via SETVAL=0 then semop += value so sem_otime becomes nonzero).

## Key Takeaways
- Model bounded-buffer problems with three semaphores: mutex=1, nempty=N, nstored=0.
- Post from a different thread is legal and is the key power over mutexes; posts are never lost.
- Prefer memory-based semaphores inside one process; named semaphores across unrelated processes; always `sem_unlink` named semaphores.
- Never place a process-shared `sem_t` outside actual shared memory; never copy a `sem_t`.
- The kernel does not auto-release a semaphore when its holder dies — design for crash recovery (unlike record locks).
- Multiple buffering / double buffering is just producer-consumer with NBUFF buffers.
- Order of nested sem_waits matters; a wrong order deadlocks, and the system probably won't tell you.

## Connects To
Chapter 7 (mutexes, condition variables — the implementation substrate), Chapter 9 (record locks as alternative file locking; locks auto-released on exit), Chapter 11 (System V semaphores, used by Section 10.16 implementation), Chapters 12–13 (memory-mapped I/O used by Section 10.15), Part 4 shared memory.
