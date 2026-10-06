# Chapter 2: Posix IPC

## Core Idea
Posix message queues, Posix semaphores, and Posix shared memory ("Posix IPC") share a common interface pattern: a name passed to mq_open / sem_open / shm_open, open-like oflag constants, and file-like permission bits. The chapter covers those common properties — names, creation flags, and permission testing.

## Frameworks Introduced
- **Posix IPC function families (Figure 2.1)**: each type has create/open/delete functions (mq_open/mq_close/mq_unlink; sem_open/sem_close/sem_unlink; shm_open/ftruncate), control operations (mq_getattr/mq_setattr; sem_getvalue; fstat), and IPC operations (mq_send/mq_receive/mq_notify; sem_wait/sem_trywait/sem_post; mmap/munmap).
- **IPC naming rules**: name must conform to pathname rules (≤ PATH_MAX bytes including terminating null); if it begins with a slash, all calls reference the same object; otherwise implementation-dependent; additional slashes implementation-defined. For portability: begin with a slash, no other slashes.
- **px_ipc_name function**: Stevens's solution to name portability — prefix the correct directory per system (env var `PX_IPC_NAME` overrides). Use instead of hardcoding IPC names.
- **Creation/open logic (Figures 2.5/2.6)**: decision table for O_CREAT/O_EXCL vs. object existence; the existence check + creation is atomic with regard to other processes.

## Key Concepts
- Posix IPC: message queues (Ch 5), semaphores (Ch 10), shared memory (Ch 13), collectively — similar access functions and descriptor information.
- S_TYPEISMQ / S_TYPEISSEM / S_TYPEISSHM: macros taking a `stat` structure pointer, nonzero if the IPC object is implemented as a distinct file type (often useless — Solaris 2.6 always returns 0).
- mode argument: required with O_CREAT; permission bits formed from S_IRWXU/S_IRWXG/S_IRWXO constants in `<sys/stat.h>`, modified by the process's file mode creation mask (umask).
- Ownership of a new IPC object: user ID = effective user ID of creating process; group ID = effective group ID (message queues), or effective group ID or system default (semaphore, shared memory).
- Permission test: four sequential steps — superuser; effective UID vs owner bits; effective/supplementary GID vs group bits; other bits; first matching step decides exclusively.
- O_TRUNC: shared memory only — truncate existing object to 0 length when opened read-write.
- EEXIST: returned when O_CREAT|O_EXCL specified and object already exists.
- ENOENT: object does not exist and O_CREAT not specified. ENOSPC: system tables full. EACCES: permission denied.

## Mental Models
- Think of mq_open / sem_open / shm_open as "open for IPC": same oflag vocabulary as the file `open`, plus a mode argument on creation.
- Use O_CREAT|O_EXCL as an atomic "create-only" test when exactly one process must own creation; use plain O_CREAT when any opener may create-or-reference.
- Treat Posix IPC names as a portability hazard, not a pathname: always route them through px_ipc_name or a `#define` in an easily changed header.
- Think of the permission algorithm as "first match wins": owner check excludes group/other consideration entirely.

## Anti-patterns
- Hardcoding a name like "/tmp/test.1234": fails under Solaris (forbids additional slashes); a name like "/test1234" fails under Digital Unix (tries to create in root directory). The standard is "a standard way of being nonstandard."
- Using sprintf instead of snprintf: sprintf cannot check destination-buffer overflow — a classic exploit vector; snprintf takes the buffer size.
- Specifying O_RDONLY/O_WRONLY/O_RDWR for sem_open — semaphores always require read and write access (implementations assume O_RDWR).
- Relying on the S_TYPEIS* macros to detect IPC objects — implementations need not use distinct file types.
- Expecting O_CREAT without O_EXCL to tell you whether a new object was created — it gives no such indication.

## Code Examples
```c
#include "unpipc.h"

char *
px_ipc_name(const char *name)
{
    char *dir, *dst, *slash;

    if ((dst = malloc(PATH_MAX)) == NULL)
        return(NULL);

    /* 4can override default directory with environment variable */
    if ((dir = getenv("PX_IPC_NAME")) == NULL) {
#ifdef POSIX_IPC_PREFIX
        dir = POSIX_IPC_PREFIX;     /* from "config.h" */
#else
        dir = "/tmp/";              /* default */
#endif
    }
    /* 4dir must end in a slash */
    slash = (dir[strlen(dir) - 1] == '/') ? "" : "/";
    snprintf(dst, PATH_MAX, "%s%s%s", dir, slash, name);
    return(dst);        /* caller can free() this pointer */
}
```
*What it demonstrates:* portable construction of a Posix IPC name — env-var override, compile-time prefix, slash normalization, and overflow-safe snprintf; `px_ipc_name("test1")` returns `/test1` under Solaris 2.6 but `/tmp/test1` under Digital Unix 4.0B.

## Reference Tables
Posix IPC function summary (Figure 2.1):

| | Message queues (`<mqueue.h>`) | Semaphores (`<semaphore.h>`) | Shared memory (`<sys/mman.h>`) |
|---|---|---|---|
| Create/open/delete | mq_open, mq_close, mq_unlink | sem_open, sem_close, sem_unlink | shm_open (+ftruncate) |
| Control operations | mq_getattr, mq_setattr | sem_getvalue | fstat, ftruncate |
| IPC operations | mq_send, mq_receive, mq_notify | sem_wait, sem_trywait, sem_post | mmap, munmap |

oflag constants (Figure 2.3):

| Constant | Description | mq_open | sem_open | shm_open |
|---|---|---|---|---|
| O_RDONLY / O_WRONLY / O_RDWR | open mode | all three allowed | none (needs rd+wr) | no write-only |
| O_CREAT | create if not existing | • | • | • |
| O_EXCL | exclusive create (error EEXIST if exists) | • | • | • |
| O_NONBLOCK | nonblocking queue reads/writes | • | — | — |
| O_TRUNC | truncate existing object to 0 length | — | — | • |

Create-or-open decision table (Figure 2.6):

| oflag argument | Object does not exist | Object already exists |
|---|---|---|
| no special flags | error, errno = ENOENT | OK, references existing object |
| O_CREAT | OK, creates new object | OK, references existing object |
| O_CREAT \| O_EXCL | OK, creates new object | error, errno = EEXIST |

mode constants: S_IRWXU (user read/write/execute), S_IRWXG, S_IRWXO; OR-ed together, then modified by the process umask.

## Worked Example
Opening a message queue: the server calls `mq_open(px_ipc_name("test1"), O_CREAT | O_EXCL | O_RDWR, FILE_MODE, NULL)`. Following Figure 2.5: if both O_CREAT and O_EXCL are set and the object exists → EEXIST; if system tables are full → ENOSPC; if O_CREAT set and it doesn't exist → new object created with permission bits = mode argument filtered through umask, user ID = effective user ID, group ID = effective group ID. A client later calls `mq_open(name, O_RDONLY)`; the kernel walks the four permission steps (superuser → owner bits → group/supplementary bits → other bits, first match exclusive) and returns EACCES if the appropriate bit is off.

## Key Takeaways
- Always build Posix IPC names via px_ipc_name (or a single `#define`): one slash at the start, none elsewhere, per-system directory.
- O_CREAT|O_EXCL is the only way to atomically know you created the object; plain O_CREAT silently references an existing one.
- On creation, always pass the mode argument; remember it is AND-ed with the complement of the process's umask.
- Permission testing mirrors file permissions: sequential superuser/owner/group/other checks, first match decides.
- Prefer snprintf over sprintf everywhere — buffer overflow safety costs nothing.

## Connects To
- Ch 1 (persistence and name spaces — Figures 1.3/1.4), Ch 5 (Posix message queues, mq_send/mq_receive/mq_notify), Ch 10 (Posix semaphores), Ch 13 (Posix shared memory with shm_open/mmap), Ch 3 (System V IPC's key_t alternative to names), Ch 9 (fcntl record locking permission semantics, APUE references).
