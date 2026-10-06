# Chapter 13: Posix Shared Memory

## Core Idea
Posix shared memory extends mmap-based sharing to unrelated processes via a named object: `shm_open` returns a descriptor for a named shared memory object, which is then mapped with the same `mmap` call used for files. After creation you must set its size with `ftruncate`, and remove its name with `shm_unlink` when done.

## Frameworks Introduced
- **Two-step object model**: `shm_open(name, oflag, mode)` → descriptor → `ftruncate(fd, length)` → `mmap(..., fd, 0)` → `close(fd)`. The two-step split exists because mmap already existed; shm_open returns a descriptor precisely because a descriptor is what mmap consumes.
- **Two Posix ways to share memory between unrelated processes**:
  1. Memory-mapped files: `fd = open(pathname, ...)` then mmap — real file backing, filesystem persistence.
  2. Shared memory objects: `fd = shm_open(name, ...)` then mmap — a memory object that need not be a file (though Solaris/Digital Unix implement it as one, e.g. `/tmp/.SHMname`).
- **Offsets, not pointers (shared-memory struct layout)**: because each process maps the object at a different address, structures in shared memory must reference other locations by byte offsets (e.g. `msgoff[]` array) — never raw addresses.
- **Process-shared memory-based semaphores in the object**: initialize semaphores with `sem_init(&sem, 1, value)` inside the mapped region to synchronize unrelated processes with no named objects needed.
- **Nonblocking producers with overflow accounting**: use `sem_trywait` on the "empty slots" semaphore; on EAGAIN increment a shared `noverflow` counter under its own mutex instead of blocking.

## Key Concepts
- shm_open: opens/creates a named shared memory object; oflag must include O_RDONLY or O_RDWR, plus optional O_CREAT, O_EXCL, O_TRUNC; mode must always be specified (0 if no O_CREAT).
- shm_unlink: removes the object's name; existing mappings/references stay valid until all are closed — only new opens fail.
- ftruncate on a shared memory object: sets the object's size exactly (a newly created object has size 0; the standard does not guarantee zero-fill on extension — implementations do zero it, but relying on it is technically unspecified / a potential security hole).
- fstat on a shared memory descriptor: only st_mode, st_uid, st_gid, st_size are meaningful.
- Kernel persistence: a Posix shared memory object survives process termination until explicitly unlinked (and all references closed).
- Different attach addresses: the same object legitimately maps at different addresses in different processes (Fig 13.6) — hence offsets not pointers.
- Minimum mutex scope: grab shared values under the lock, release it before doing slow work (e.g. printf) — "minimum number of operations while a mutex is held."
- IPC names: no implementation guarantee distinguishing mq/sem/shm namespaces — use distinct names.

## Mental Models
- Use shm_open+mmap when unrelated processes need to share memory and you don't want a real file in the filesystem (or want at-least-kernel rather than filesystem persistence).
- Use open+mmap (memory-mapped file, Ch 12) when you want the shared data itself to persist as a file.
- Use memory-based semaphores in the object (sem_init pshared≠0) for self-contained synchronization; use named semaphores (sem_open) when a separate bootstrap process creates infrastructure before clients run.
- Use sem_trywait + overflow counter when a producer (often itself a server, e.g. logging to syslogd) must never block on a full buffer.

## Anti-patterns
- **mmap'ing a fresh shm_open object without ftruncate**: new objects have size 0 — mapping succeeds but accessing memory raises SIGBUS. Always ftruncate first.
- **Storing pointers inside shared memory**: mmap return values differ per process, so pointers into the object are invalid in other processes; use offsets (`msgoff[i]`, `&ptr->msgdata[offset]` computed locally).
- **Forgetting shm_unlink**: the name (and possibly the object) persists in the system indefinitely — later runs hit EEXIST or leak memory.
- **Calling ftruncate/fstat before the mapping exists is fine, but calling mmap with prot incompatible with the open mode** (e.g. PROT_WRITE on O_RDONLY) is an error; match shm_write O_RDWR vs shmread O_RDONLY to PROT flags.
- **Assuming zero-initialized contents from the standard**: only the Rationale (not the normative text) promises zeros in extended shared memory — don't build security-sensitive code on it.
- **Doing slow work (printf) while holding the shared mutex** — copy the value out, post, then print.

## Code Examples
```c
/* Create + size + map a Posix shared memory object (Fig 13.2/13.7) */
shm_unlink(Px_ipc_name(name));                       /* OK if this fails: idempotent cleanup */
fd = Shm_open(Px_ipc_name(name), O_RDWR | O_CREAT | O_EXCL, FILE_MODE);
Ftruncate(fd, sizeof(struct shmstruct));             /* REQUIRED: new object has size 0 */
ptr = Mmap(NULL, sizeof(struct shmstruct), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
Close(fd);                                           /* mapping survives close */
Sem_init(&ptr->mutex, 1, 1);                         /* pshared=1: process-shared, in-shm semaphore */
```
Demonstrates the full canonical sequence: unlink-stale → shm_open → ftruncate → mmap → close → init in-object semaphores.

```c
/* Nonblocking producer on a full buffer (Fig 13.12) */
if (sem_trywait(&ptr->nempty) == -1 && errno == EAGAIN) {
    Sem_wait(&ptr->noverflowmutex); ptr->noverflow++; Sem_post(&ptr->noverflowmutex);
    continue;                                        /* drop the message, count the overflow */
}
```

## Reference Tables
**shm_open oflags**: O_RDONLY | O_RDWR (one required) · O_CREAT · O_EXCL · O_TRUNC (with O_RDWR, truncates existing object to 0).

**fstat members valid for shm objects**: st_mode (permissions) · st_uid · st_gid · st_size (bytes).

**Posix shared memory vs memory-mapped file**: descriptor from shm_open vs open; object need not be a file vs is a file; size set by ftruncate vs by writing; both require mmap with MAP_SHARED; both keep working after close(fd).

**Persistence**: at least kernel persistence — object lives until shm_unlink and all references closed; implementations may map names to files under /tmp (Solaris `.SHM*`, Digital Unix plain name).

## Worked Example
**Multiple clients logging to one server through shared memory (Figs 13.10–13.12)** — a multiple-producer / single-consumer ring of NMESG=16 slots × MESGSIZE=256 bytes. Shared layout: `sem_t mutex, nempty, nstored; int nput; long noverflow; sem_t noverflowmutex; long msgoff[NMESG]; char msgdata[NMESG*MESGSIZE];` — all links by offset, never by pointer. Server: shm_unlink → shm_open(O_CREAT|O_EXCL) → mmap → ftruncate → init msgoff[] and the four semaphores (pshared=1), then consumer loop: `Sem_wait(nstored); Sem_wait(mutex); print msgdata[msgoff[index]]; index=(index+1)%NMESG; Sem_post(mutex); Sem_post(nempty);` plus an overflow check with value copied out before printing. Clients: open existing object, `sem_trywait(nempty)` (overflow path on EAGAIN), grab offset & bump nput under mutex, release mutex, `strcpy` the message, `Sem_post(nstored)`. Result: no messages lost; overflow correctly reported (e.g. "noverflow = 25").

## Key Takeaways
1. shm_open + ftruncate + mmap + close is the complete Posix shared memory recipe; ftruncate is mandatory because new objects are size 0.
2. Unlink-then-create (shm_unlink ignoring errors, then O_CREAT|O_EXCL) makes initialization idempotent across runs.
3. Use offsets, not pointers, for any cross-references inside shared memory.
4. Put semaphores inside the object with pshared≠0 for self-contained sync; init exactly once, by the creator, before clients attach.
5. Never block a producer that can't wait: sem_trywait + shared overflow counter under its own small mutex.
6. Match mmap prot to the shm_open mode, and remember objects persist until shm_unlink — clean up.
7. Posix shared memory is a thin shell over mmap; if the implementation maps files, shm_open≈open and shm_unlink≈unlink.

## Connects To
- Chapter 12 (mmap mechanics, MAP_SHARED semantics, SIGBUS/SIGSEGV behavior) — the substrate.
- Chapter 14 (System V shared memory): shmget/shmat as the alternative API.
- Chapter 10 (Posix semaphores): sem_init/sem_wait/sem_trywait used throughout.
- Chapter 5 (Posix message queues): the same trywait/overflow discipline applies to full message queues.
