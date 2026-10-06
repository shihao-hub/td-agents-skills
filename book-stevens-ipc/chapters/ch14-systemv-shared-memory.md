# Chapter 14: System V Shared Memory

## Core Idea
System V shared memory provides the same concept as Posix shared memory through a separate API: `shmget` creates/opens a segment identified by a key and returns a shmid, then `shmat` attaches the segment directly into the address space (no mmap involved). Segment size is fixed at creation, and segments persist in the kernel until explicitly destroyed with `shmctl(shmid, IPC_RMID, NULL)`.

## Frameworks Introduced
- **Two-call attach model**: `shmget(key, size, oflag)` → shmid (creation/open only, grants no access) followed by `shmat(shmid, shmaddr, flag)` → pointer (the actual attach). Contrast with Posix's shm_open + mmap.
- **Kernel-maintained per-segment metadata** (`struct shmid_ds` in `<sys/shm.h>`): ipc_perm (permissions), shm_segsz (segment size), shm_lpid/shm_cpid (last-op/creator pids), shm_nattch/shm_cnattch (attach counts), shm_atime/shm_dtime/shm_ctime.
- **ftok-based naming**: a pathname + id converted to a key_t; using the server executable's absolute pathname (its i-node) as the ftok argument is a common way to get a per-application identifier.
- **Explicit lifecycle management**: creation, sizing (fixed by shmget), stat via shmctl(IPC_STAT), and destruction via shmctl(IPC_RMID) — with `ipcs` for inspection.

## Key Concepts
- shmget: creates (size must be nonzero, contents zero-initialized) or opens (size = 0) a segment; key from ftok or IPC_PRIVATE; returns shared memory identifier.
- shmat: attaches the segment; shmaddr NULL lets the system choose (recommended, most portable); returns the attach address.
- SHM_RND: with a non-null shmaddr, attach at shmaddr rounded down to a multiple of SHMLBA (lower boundary address).
- SHM_RDONLY: attach read-only; default is read-write if permissions allow.
- shmdt: detaches the segment at shmaddr; all attached segments are detached automatically on process termination — but detach never deletes the segment.
- IPC_RMID via shmctl: the only way to remove/destroy a segment from the system.
- IPC_STAT / IPC_SET: fetch / set (uid, gid, mode) of the shmid_ds structure.
- Kernel persistence: segments survive process exit (NATTCH may be 0 yet the segment remains, as `ipcs` shows) until IPC_RMID.
- System limits: shmmax (max segment bytes), shmmin (min bytes), shmmni (max identifiers systemwide), shmseg (max segments attached per process).

## Mental Models
- Use System V shared memory when porting to or interoperating with historical System V codebases; prefer Posix (Ch 13) for new code.
- Use shmat(id, NULL, 0) always — kernel-chosen addresses are the portable choice, and like Posix, the segment may land at different addresses in different processes (offsets, not pointers, for cross-references).
- Use shmctl(id, IPC_STAT, &buf) to learn an existing segment's size (buf.shm_segsz) — the System V analogue of fstat on a shm object.
- Use ftok(server_executable_path, 0) when multiple processes must agree on the key without a shared configuration channel.

## Anti-patterns
- **Confusing shmdt with IPC_RMID**: `shmdt` merely detaches the calling process's mapping; the segment stays in the kernel forever (visible in `ipcs`) until `shmctl(shmid, IPC_RMID, NULL)`. Detaching and expecting deletion leaks the segment.
- **Trying to resize a segment**: size is fixed by shmget; Posix objects can grow via ftruncate, System V segments cannot — to grow you must create a new, larger segment.
- **Passing a nonzero size when opening an existing segment**: size should be 0 when referencing an existing segment; nonzero size is only for creation.
- **Specifying a non-null shmaddr without SHM_RND / relying on fixed attach addresses**: not portable; pass NULL.
- **Forgetting IPC_RMID on error paths**: unlike a pathname (unlink-able by anyone later), orphaned segments need IPC_RMID and persist across reboots-less-but-long uptimes; pair every shmget with cleanup.
- **Ignoring system limits**: shmmni/shmseg/shmmax (e.g. Digital Unix 4.0B: 128 ids, 32 attaches/process, 4 MB max; Solaris 2.6: 100 ids, 6 attaches, 1 MB max) can silently cap designs with many segments.

## Code Examples
```c
/* Create, attach, fill, verify, remove — the canonical System V shm sequence */
id  = Shmget(Ftok(path, 0), length, SVSHM_MODE | IPC_CREAT);  /* create: nonzero length */
ptr = Shmat(id, NULL, 0);                                     /* attach: kernel picks address */
Shctl(id, IPC_STAT, &buff);                                   /* size = buff.shm_segsz */
for (i = 0; i < buff.shm_segsz; i++) ptr[i] = i % 256;        /* use like ordinary memory */
Shmdt(ptr);                        /* detach — does NOT delete */
Shctl(id, IPC_RMID, NULL);         /* THIS deletes the segment */
```
Demonstrates the complete lifecycle: shmget → shmat → IPC_STAT → use → shmdt → IPC_RMID.

## Reference Tables
**Function summary**:
| Function | Purpose | Key args |
|---|---|---|
| `shmget(key, size, oflag)` | create/open segment → shmid | key: ftok value or IPC_PRIVATE; size: nonzero on create, 0 on open; oflag: perms \| IPC_CREAT [\| IPC_EXCL] |
| `shmat(shmid, shmaddr, flag)` | attach → address | shmaddr NULL (recommended); flag 0, SHM_RDONLY, and/or SHM_RND |
| `shmdt(shmaddr)` | detach this process | address returned by shmat |
| `shmctl(shmid, cmd, buff)` | control | cmd: IPC_RMID (destroy), IPC_STAT (read shmid_ds), IPC_SET (set uid/gid/mode) |

**shmid_ds members**: shm_perm · shm_segsz · shm_lpid · shm_cpid · shm_nattch · shm_cnattch · shm_atime · shm_dtime · shm_ctime.

**Posix vs System V shared memory**:
| Aspect | Posix (Ch 13) | System V (Ch 14) |
|---|---|---|
| Create+attach | shm_open → mmap | shmget → shmat |
| Name | Posix IPC name | key_t (ftok or IPC_PRIVATE) |
| Size | set/changed anytime via ftruncate | fixed by shmget |
| Query size | fstat st_size | shmctl IPC_STAT shm_segsz |
| Remove name/object | shm_unlink | shmctl IPC_RMID |
| Detach | munmap | shmdt (auto on exit) |
| Persistence | kernel (until unlink + close) | kernel (until IPC_RMID) |

**Typical limits**: shmmax 4,194,304 (DUnix) / 1,048,576 (Solaris 2.6); shmmni 128 / 100; shmseg 32 / 6; shmmin 1.

## Worked Example
**Limits probe (Fig 14.6)**: loops calling `shmget(IPC_PRIVATE, 1024, mode|IPC_CREAT)` until failure to count simultaneous identifiers; then creates segments and `shmat`s each until shmat returns (void*)-1 to count attaches per process; then binary-searches minimum size (try 1, 2, ...) and maximum size (grow by 4096) — always pairing creations with `Shmctl(id, IPC_RMID, NULL)` cleanup. Sample run on Digital Unix: 127 identifiers (128 limit minus one daemon's segment), 32 attached at once, min size 1, max 4,194,304. Also illustrates IPC_PRIVATE as the throwaway key for probe/private segments.

## Key Takeaways
1. shmget creates/opens, shmat attaches — creation alone gives no access to the memory.
2. shmdt ≠ deletion: only shmctl(id, IPC_RMID, NULL) destroys a segment; always pair create with remove.
3. Pass shmaddr = NULL to shmat for portability; expect different addresses in different processes (use offsets, not pointers).
4. Get an existing segment's size via shmctl IPC_STAT; sizes are immutable after creation.
5. Segments have kernel persistence and outlive processes — `ipcs` to inspect, IPC_RMID to clean up.
6. Check system limits (shmmni/shmseg/shmmax) before designing around many or large segments.
7. New segments are zero-initialized by shmget — unlike Posix, this is guaranteed.

## Connects To
- Chapter 13 (Posix shared memory): same concept, simpler name-based API, resizable objects.
- Chapter 12 (mmap): the mapping machinery System V avoids by attaching directly.
- Chapter 3 (System V IPC basics): ftok, ipc_perm, IPC_CREAT/IPC_EXCL semantics, ipcs/limits discussion shared with message queues and semaphores.
- Chapters 6 & 11: System V message queues and semaphores — the sibling IPC mechanisms with identical lifecycle rules.
