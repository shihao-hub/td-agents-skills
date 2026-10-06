# Chapter 3: System V IPC

## Core Idea
System V message queues, semaphores, and shared memory share one common kernel-managed infrastructure: objects are named by `key_t` keys (usually via `ftok`), opened/created by `msgget`/`semget`/`shmget` with `IPC_CREAT`/`IPC_EXCL` flags, and described by a kernel `ipc_perm` structure with permissions, owner/creator IDs, and a slot usage sequence number.

## Frameworks Introduced
**key_t + ftok naming** — when unrelated processes need to reach the same IPC object: both sides agree on a pathname + small `id`, call `ftok(pathname, id)` to derive the same 32-bit key.
**getXXX creation/opening model** — `msgget`/`semget`/`shmget` take key + oflag (flags OR'ed with 9 permission bits) and return a systemwide integer identifier.
**ipc_perm bookkeeping** — kernel keeps owner (`uid`,`gid`), creator (`cuid`,`cgid`), `mode`, `seq`, `key` per object; `*ctl(IPC_SET/IPC_STAT)` reads/updates it.
**Identifier reuse (seq)** — kernel increments a slot sequence counter per table entry so identifiers are large, slowly reused, systemwide-unique values.
**ipcs/ipcrm tooling** — since SysV IPC objects live outside the filesystem, dedicated commands inspect and remove them.

## Key Concepts
- `key_t`: integer type (≥32 bits, `<sys/types.h>`) naming a System V IPC object; usually produced by `ftok`.
- `ftok(pathname, id)`: combines `st_dev`, `st_ino`, and low 8 bits of `id` into a key; mapping is one-way and collisions are possible.
- `IPC_PRIVATE`: special key (value 0) that always creates a new, unique object; the typical choice for a server creating a private channel to hand to a client (e.g., via fork).
- Identifier: integer returned by getXXX; systemwide (not per-process like file descriptors), used by all subsequent operations.
- `ipc_perm`: per-object kernel structure — `uid`, `gid`, `cuid`, `cgid`, `mode`, `seq`, `key`.
- `IPC_CREAT` / `IPC_EXCL`: analogues of `O_CREAT`/`O_EXCL`; both set ⇒ error `EEXIST` if object exists; `IPC_EXCL` alone is meaningless.
- Permission checking: two levels — a weak check at getXXX open time, and a real check (superuser → uid/cuid → gid/cgid → other) on every IPC operation.
- `seq`: slot usage sequence number; identifier grows by table size on each reuse, defeating identifier-guessing and short-term reuse.
- `ipcs` / `ipcrm`: list and remove SysV IPC objects (no `ls`/`rm` equivalents since objects aren't pathnames).
- Kernel limits: per-facility caps (e.g., `msgmni`, `semmns`, `shmmax`) inherited from the original PDP-11-era implementation, often too small and tuned per-OS (`/etc/system` on Solaris, `sysconfig` on Digital Unix).

## Mental Models
- Use `ftok` + a stable pathname when client and server both need to independently open the same pre-agreed object.
- Use `IPC_PRIVATE` when one process creates the object and passes the identifier to the other (via fork or descriptor passing), or when you must guarantee uniqueness.
- Server usually creates with `IPC_CREAT` (or `IPC_CREAT|IPC_EXCL` to detect an existing object); clients open with no flags.
- Think of the identifier as "file descriptor, but systemwide" — the same integer means the same object in every process, so identifier space is deliberately large.

## Anti-patterns
- Using a pathname the server creates/deletes at runtime as the `ftok` anchor — each recreation may get a new i-node and thus a new key.
- Relying on getXXX open-time permission checking for security — any process can bypass it by passing `oflag` 0; real enforcement happens per-operation.
- Assuming `ftok` never collides — more source bits than key bits means different pathnames can map to the same key.
- Assuming small, predictable identifiers — the seq mechanism makes identifiers large precisely to prevent enumeration; don't depend on their values.
- Assuming SysV getXXX honors the file mode creation mask — permissions are set to exactly what `oflag` specifies (unlike `mkfifo`).

## Code Examples
```c
/* Deriving a key from an agreed pathname (id of 0x57): */
key_t key = Ftok("/usr/local/etc/server.conf", 0x57);

/* Server: create-exclusively; client: open existing */
msqid = Msgget(key, SVMSG_MODE | IPC_CREAT | IPC_EXCL); /* server */
msqid = Msgget(key, 0);                                 /* client */
```
```c
/* Identifier reuse: create + remove a queue 10 times */
for (i = 0; i < 10; i++) {
    msqid = Msgget(IPC_PRIVATE, SVMSG_MODE | IPC_CREAT);
    printf("msqid = %d\n", msqid);   /* prints 0, 50, 100, ... */
    Msgctl(msqid, IPC_RMID, NULL);
}
```

## Reference Tables
| oflag | key does not exist | key already exists |
|---|---|---|
| no flags | error, `ENOENT` | OK, references existing object |
| `IPC_CREAT` | OK, creates new entry | OK, references existing (no tell which) |
| `IPC_CREAT\|IPC_EXCL` | OK, creates new entry | error, `EEXIST` |

| ipc_perm member | Meaning | Set when / mutable |
|---|---|---|
| `uid`, `gid` | owner IDs | set to creator's euid/egid; changeable via `*ctl(IPC_SET)` |
| `cuid`, `cgid` | creator IDs | set at creation; never change |
| `mode` | r/w permission bits (owner/group/other) | set from `oflag`; changeable via `*ctl(IPC_SET)` |
| `seq` | slot usage sequence number | kernel-managed |
| `key` | the `ftok`-generated key | fixed at creation |

| Permission bit (octal) | Message queue | Semaphore | Shared memory |
|---|---|---|---|
| 0400 read by user | `MSG_R` | `SEM_R` | `SHM_R` |
| 0200 write by user | `MSG_W` | `SEM_A` (alter) | `SHM_W` |
| 0040 / 0004 read grp/oth | `MSG_R>>3` / `MSG_R>>6` | `SEM_R>>3` / `>>6` | `SHM_R>>3` / `>>6` |
| 0020 / 0002 write grp/oth | `MSG_W>>3` / `>>6` | `SEM_A>>3` / `>>6` | `SHM_W>>3` / `>>6` |

| Facility | Header | Create/open | Control | Operations |
|---|---|---|---|---|
| Message queues | `<sys/msg.h>` | `msgget` | `msgctl` | `msgsnd`, `msgrcv` |
| Semaphores | `<sys/sem.h>` | `semget` | `semctl` | `semop` |
| Shared memory | `<sys/shm.h>` | `shmget` | `shmctl` | `shmat`, `shmdt` |

## Worked Example
Trace of `ftok("/etc/system", 0x57)` on Solaris 2.6: `st_dev=800018`, `st_ino=4a1b` → key `57018a1b`. Dissection: id (`0x57`) occupies the top 8 bits, low 12 bits of `st_dev` the next 12, low 12 bits of `st_ino` the last 12. FreeBSD packs differently (8/8/16 bits) — the layout is implementation-specific and the mapping is one-way, so never parse keys or assume portability; both peers must simply call `ftok` on the same pathname/id.

## Key Takeaways
- Generate keys with `ftok` from a pathname that exists for the application's whole lifetime; use distinct `id` values for multiple channels.
- Prefer `IPC_PRIVATE` when one process can hand the identifier to the peer — it guarantees uniqueness.
- Use `IPC_CREAT|IPC_EXCL` to atomically detect "already exists"; treat `EEXIST` accordingly.
- The real permission check happens on every IPC operation (superuser → owner/creator uid → gid/cgid → other), not at open.
- SysV IPC objects have no filesystem name: manage them with `ipcs`/`ipcrm`, and clean them up (`IPC_RMID`) explicitly.
- Expect small kernel limits (queue counts, semaphore counts, `shmmax`); check and tune them per OS before deploying SysV IPC-heavy applications.

## Connects To
- Chapter 6 (System V message queues), Chapter 11 (semaphores), Chapter 14 (shared memory) — each builds on keys, `ipc_perm`, and getXXX semantics defined here.
- Chapter 2 (Posix IPC) — contrast: Posix uses pathnames + `O_CREAT`/`O_EXCL` and cannot change owners; SysV uses keys, `IPC_*` flags, and `IPC_SET`.
- Chapter 4 (pipes/FIFOs) — pipes vanish on last close; SysV IPC objects persist until explicitly removed.
