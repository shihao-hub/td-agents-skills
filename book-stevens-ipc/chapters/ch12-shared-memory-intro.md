# Chapter 12: Shared Memory Introduction

## Core Idea
Shared memory is the fastest form of IPC: once a region is mapped into the address spaces of the sharing processes, data passes between them with no kernel involvement (no system calls, no kernel↔process copies). The cost is that the processes must synchronize access themselves using mutexes, condition variables, read-write locks, record locks, or semaphores.

## Frameworks Introduced
- **Kernel-mediated IPC vs shared memory (copy accounting)**: pipes/FIFOs/message queues require ~4 copies (file→server, server→kernel, kernel→client, client→file). Shared memory reduces this to 2 copies (file→shared memory→file). Use this framing to decide when shared memory pays off.
- **mmap as the universal mapping primitive** — three uses:
  1. Memory-mapped I/O on a regular file (no read/write/lseek; the kernel does I/O under the covers).
  2. Anonymous mappings for parent–child sharing (MAP_ANON on 4.4BSD; /dev/zero on SVR4).
  3. `shm_open` descriptors for Posix shared memory between unrelated processes (Chapter 13).
- **mmap + process-shared synchronization in shared memory** (the core pattern): map a region MAP_SHARED, store both the data and the synchronization object (memory-based semaphore via `sem_init(&sem, 1, value)`) in the region, and let all processes operate on both through their mappings.
- **Mappings survive fork**: memory mappings created by the parent before `fork` (MAP_SHARED) are retained in the child; parent changes are visible to the child and vice versa.

## Key Concepts
- mmap: maps a file or shared memory object into the address space; returns starting address or MAP_FAILED.
- MAP_SHARED: modifications visible to all sharing processes and written back to the underlying object.
- MAP_PRIVATE: copy-on-write; modifications private to the calling process, object unchanged.
- MAP_ANON + fd=-1: 4.4BSD anonymous mapping; zero-initialized, no file needed.
- /dev/zero mapping: SVR4 equivalent of anonymous memory; reads return zeros, writes discarded.
- munmap: removes a mapping; later references to those addresses raise SIGSEGV.
- msync: flushes a MAP_SHARED mapped region back to the file (MS_SYNC synchronous, MS_ASYNC queued writes, MS_INVALIDATE invalidates stale in-memory copies).
- SIGBUS vs SIGSEGV for mmap: SIGBUS = reference within the mapping but past the end of the underlying object; SIGSEGV = reference past the end of the mapping itself.
- Page granularity: the kernel permits touching the remainder of the final page beyond the mapping/object size, but writes there do not reach the file; protection works per page.
- mlock/munlock/mlockall/munlockall: force memory-residency of address ranges (not covered in depth).

## Mental Models
- Use a memory-mapped file when you also want filesystem persistence of the shared data or unrelated processes must share via a pathname.
- Use MAP_ANON or /dev/zero when only a parent and child (across fork) need shared, zero-initialized memory — no file creation/open needed.
- Use mmap before fork with MAP_SHARED to get parent–child shared memory; the child inherits the mapping.
- Map a size larger than the file and grow the file with ftruncate when handling a growing file — track the current file size and never reference past it.

## Anti-patterns
- Assuming globals are shared across fork: each process gets its own copy of the parent's data space; a "shared" counter silently double-counts (Figure 12.3 bug).
- Forgetting to size the underlying object before/at mmap: mapping larger than the object leads to SIGBUS on access beyond the object's end.
- Specifying MAP_FIXED or a non-null addr: not portable; pass NULL and let the kernel choose.
- Trying to mmap terminals or sockets: mmap only works on mappable objects; use read/write for those descriptors.
- Relying on writes beyond the object end (in the tail of the last page) being saved: they are silently discarded.
- Discarding the mapping without munmap and expecting state: MAP_PRIVATE changes are discarded on munmap.

## Code Examples
```c
/* Parent/child share a counter + semaphore both stored in shared memory (Fig 12.12) */
struct shared { sem_t mutex; int count; } ;   /* layout placed in shared memory */
fd = Open(path, O_RDWR | O_CREAT, FILE_MODE);
Write(fd, &shared, sizeof(struct shared));   /* zero-initialize the file */
ptr = Mmap(NULL, sizeof(struct shared), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
Close(fd);                                   /* mapping survives close */
Sem_init(&ptr->mutex, 1, 1);                 /* 2nd arg nonzero = process-shared */
if (Fork() == 0) { /* child: Sem_wait(&ptr->mutex); ptr->count++; Sem_post(&ptr->mutex); */ }
```
Demonstrates the core pattern: data + process-shared semaphore in one mmap'd MAP_SHARED region shared across fork.

```c
/* 4.4BSD anonymous mapping — no file at all (Fig 12.14) */
ptr = Mmap(NULL, sizeof(int), PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANON, -1, 0);
```

## Reference Tables
**mmap prot flags**: PROT_READ (readable) | PROT_WRITE (writable) | PROT_EXEC (executable) | PROT_NONE (no access). Common: PROT_READ|PROT_WRITE.

**mmap flags**: MAP_SHARED (changes shared + written to object; required for IPC) · MAP_PRIVATE (changes private) · MAP_FIXED (portability: avoid) · MAP_ANON (anonymous; fd = -1, offset ignored, zero-filled).

**msync flags**: MS_SYNC (return after writes complete) · MS_ASYNC (return once writes queued) · MS_INVALIDATE (invalidate inconsistent in-memory copies). Exactly one of MS_SYNC/MS_ASYNC.

**Signal taxonomy**: SIGSEGV = beyond mapping; SIGBUS = inside mapping but beyond underlying object's size.

## Worked Example
Counter in a memory-mapped file (Fig 12.10/12.12): server-style parent opens/creates a file, writes zeros to set its size, mmaps it MAP_SHARED, initializes a process-shared semaphore in the mapped struct, forks; parent and child each loop `Sem_wait; (*ptr)++; Sem_post` — output shows a single monotonic counter (0..19999) and `od` confirms the final value persisted in the file. Variant with MAP_ANON removes the file entirely; SVR4 variant maps /dev/zero instead.

## Key Takeaways
1. Shared memory eliminates kernel-mediated data copies; the price is explicit synchronization by the sharers.
2. mmap(..., MAP_SHARED, fd, 0) + close(fd) is the canonical setup; the mapping outlives the descriptor.
3. Store the synchronization object inside the shared region (sem_init with nonzero pshared) so data and lock travel together.
4. The kernel tracks the underlying object's size even after close: SIGBUS if you touch beyond it, SIGSEGV if beyond the mapping; page-tail accesses are legal but unpersisted.
5. For fork-only sharing, prefer anonymous mappings (MAP_ANON or /dev/zero) over creating a scratch file.
6. mmap is the foundation for Posix shared memory (Chapter 13) — only how the descriptor is obtained changes.

## Connects To
- Chapter 13 (Posix shared memory): shm_open produces the descriptor mmap maps.
- Chapter 14 (System V shared memory): shmget/shmat achieve the same effect without mmap.
- Part 3 (Chapters 6–11): mutexes, condition variables, read-write locks, semaphores — the required companions to shared memory.
- Chapters 5/10: Posix message queues and semaphores can themselves be built on mmap.
