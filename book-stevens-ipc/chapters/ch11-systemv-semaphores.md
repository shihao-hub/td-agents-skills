# Chapter 11: System V Semaphores

## Core Idea
A System V semaphore is a *set* of counting semaphores maintained in the kernel, manipulated atomically by `semop` with arbitrary increment/decrement/wait-for-zero operations — more general but far more awkward than Posix semaphores, chiefly because creation (semget) and initialization (semctl) are two separate, racy steps.

## Frameworks Introduced
- **Semaphore set**: `semget` creates a set of nsems counting semaphores (kernel-persistent); kernel keeps a `semid_ds` per set pointing at an array of per-member `sem` structures (semval, sempid, semncnt, semzcnt).
- **Atomic operation arrays**: `semop` applies an array of `sembuf` operations atomically — all succeed or none is applied.
- **SEM_UNDO**: per-process kernel-tracked `semadj` adjustment reversed automatically at process exit — releases resources held by a crashed process.
- **sem_otime initialization protocol**: the standard-correct way to close the create/init race.

## Key Concepts
- `semget(key, nsems, oflag)`: create/access a set; returns semid; oflag = SEM_R/SEM_A | IPC_CREAT | IPC_EXCL; nsems=0 when just opening; cannot change set size later.
- `semop(semid, struct sembuf *opsptr, nops)`: atomically apply nops operations; the kernel does all or none.
- `struct sembuf` fields: `sem_num` (member index 0..nsems-1), `sem_op` (<0 allocate, 0 wait-for-zero, >0 release), `sem_flg` (0, IPC_NOWAIT → EAGAIN, SEM_UNDO).
- `semctl(semid, semnum, cmd, union semun arg)`: control operations — GETVAL, SETVAL, GETPID, GETNCNT, GETZCNT, GETALL, SETALL, IPC_RMID, IPC_SET, IPC_STAT.
- `union semun { int val; struct semid_ds *buf; unsigned short *array; }` — must be declared by the application (Unix 98), passed by value.
- semget does **not** initialize semaphore values — only SETVAL/SETALL do; sem_otime is guaranteed 0 at creation, set only by a successful semop.
- SEM_UNDO: on each operation, sem_op is accumulated into the process's semadj; on exit the kernel adds semadj back to semval (max adjust value semaem limits it).
- Errors from semop: EAGAIN (IPC_NOWAIT), EINTR (slow syscall, caught signal), EIDRM (semaphore removed).

## Mental Models
- Use **System V semaphores** when you need multi-member sets atomically updated in one call (e.g., allocate several resources at once), wait-for-zero semantics, or SEM_UNDO crash recovery.
- Use **IPC_NOWAIT** when you'd rather poll or fail fast than block on a semaphore operation.
- Use `sem_op = 0` when you must wait until a resource count drains to exactly zero (Posix semaphores cannot express this).
- Use **SEM_UNDO on lock acquisition** so a process that dies holding the lock has the kernel post it back at exit.

## Anti-patterns
- **The create/init race** (the chapter's core lesson): semget + semctl is two steps. Process A creates (IPC_CREAT|IPC_EXCL succeeds) but is descheduled before SETVAL; process B gets EEXIST, reopens with plain semget, and uses an uninitialized (indeterminate, garbage) value. Fix: B must poll `IPC_STAT` until `sem_otime != 0` (guaranteed 0 at creation, nonzero only after the creator's first successful semop).
- **semadj exit-time undo hazards**: SEM_UNDO only undoes what the kernel tracked — if a process's total adjustment exceeds semaem (max adjust-on-exit, typically 16384), or undo structures (semmnu) run out, behavior is limit-bound; also undo fires only at process exit, not on thread cancellation, and releases resources regardless of other state.
- **Statically initializing `struct sembuf`**: member order and extra members are not guaranteed — always fill the struct at runtime.
- Assuming semget zeroes new semaphore values — XPG3/Unix 98 explicitly say values are not initialized; older systems left whatever garbage was in that kernel memory.
- Relying on a wrapper to fix everything: `union semun` portability differs (FreeBSD/Linux define it in headers) — guard the declaration.
- Removing a semaphore that other processes still use → their semop fails with EIDRM; with Posix semaphores destruction waits for the last close.

## Code Examples
```c
struct sembuf ops[2];
ops[0].sem_num = 0;  ops[0].sem_op = -1;  ops[0].sem_flg = SEM_UNDO; /* acquire */
ops[1].sem_num = 1;  ops[1].sem_op =  1;  ops[1].sem_flg = 0;        /* release other */
Semop(semid, ops, 2);  /* both applied atomically, or neither */
```
One-line: demonstrates atomic multi-member operation with undo — impossible with Posix semaphores.

```c
union semun arg;
unsigned short vals[3] = {1, 2, 3};
arg.array = vals;
Semctl(semid, 0, SETALL, arg);   /* initialize all members of the set */
```
One-line: SETALL initializes a whole set at once (caller allocates the ushort array).

## Reference Tables

**Posix vs System V semaphores:**
| Feature | Posix | System V |
|---|---|---|
| unit | single counting semaphore | set of counting semaphores |
| operations | -1 (wait), +1 (post) only | any integer delta, plus wait-for-zero |
| atomicity | single op | array of ops, all-or-none |
| create+init | one call (sem_open) | two calls (semget + semctl) — racy |
| crash recovery | none | SEM_UNDO adjusts at exit |
| removal | sem_unlink, ref-counted | IPC_RMID, immediate (EIDRM for users) |
| handle | name / sem_t * | integer semid from key |
| kernel persistence | named: kernel-persistent | kernel-persistent |

**sembuf fields:**
| Field | Meaning |
|---|---|
| sem_num | member index in set (0..nsems-1) |
| sem_op | >0 add (release); <0 subtract, block until semval ≥ \|sem_op\|; 0 block until semval == 0 |
| sem_flg | 0, IPC_NOWAIT (EAGAIN instead of blocking), SEM_UNDO (track semadj) |

**Typical System V limits (kernel variables):**
| Name | Meaning | DUnix 4.0B / Solaris 2.6 |
|---|---|---|
| semmni | max semaphore sets, systemwide | 16 / 10 |
| semmns | max semaphores, systemwide | 400 / 60 |
| semmsl | max semaphores per set | 25 / 25 |
| semopm | max operations per semop call | 10 / 10 |
| semaem | max adjust-on-exit (semadj) value | 16384 / 16384 |
| semmnu | max undo structures, systemwide | (none) / 30 |
| semume | max undo entries per process | 10 / 10 |
| semvmx | max semaphore value | 32767 / 32767 |

## Worked Example
Stevens's file-locking wrapper (`my_lock`/`my_unlock`, Figure 11.7) — the canonical 3-step race handling for create + initialize:

```c
#define MAX_TRIES 10
int semid, initflag;
struct sembuf postop, waitop;

void my_lock(int fd) {
    union semun arg;
    struct semid_ds seminfo;
    int i, oflag;

    if (initflag == 0) {
        /* 1. try exclusive create */
        oflag = IPC_CREAT | IPC_EXCL | SVSEM_MODE;
        if ((semid = semget(Ftok(LOCK_PATH, 0), 1, oflag)) >= 0) {
            /* success: we're the first, so initialize */
            arg.val = 1;
            Semctl(semid, 0, SETVAL, arg);        /* sem_otime still 0 */
        } else if (errno == EEXIST) {
            /* 2. someone else created; open without flags */
            semid = Semget(Ftok(LOCK_PATH, 0), 1, SVSEM_MODE);
            /* 3. wait until initializer finished: poll sem_otime */
            arg.buf = &seminfo;
            for (i = 0; i < MAX_TRIES; i++) {
                Semctl(semid, 0, IPC_STAT, arg);
                if (arg.buf->sem_otime != 0)
                    goto init;
                sleep(1);
            }
            err_quit("semget OK, but semaphore not initialized");
        } else
            err_sys("semget error");
    init:
        initflag = 1;
        /* runtime init: member order not guaranteed */
        waitop.sem_num = 0; waitop.sem_op = -1; waitop.sem_flg = SEM_UNDO;
        postop.sem_num = 0; postop.sem_op =  1; postop.sem_flg = SEM_UNDO;
    }
    Semop(semid, &waitop, 1);   /* down by 1 */
}

void my_unlock(int fd) {
    Semop(semid, &postop, 1);   /* up by 1 */
}
```
Why it works: only one process wins IPC_CREAT|IPC_EXCL and initializes; every loser polls `IPC_STAT` until `sem_otime != 0`, which proves the creator ran SETVAL *and* at least one semop. SEM_UNDO means a process dying while holding the lock has it auto-released by the kernel. Note the residual design pain: creating on first use is easy, but deciding *when to remove* the semaphore is hard (record locks may suit better).

## Key Takeaways
- System V "semaphore" = a set; semop applies operation arrays atomically (all or none) — verify with `semops -n` failing all three ops with EAGAIN and no partial changes.
- Creation and initialization are separate calls; always code the IPC_CREAT|IPC_EXCL → EEXIST → reopen → poll sem_otime dance, or let one dedicated process create/init before others start (then no race exists).
- semadj/SEM_UNDO gives kernel-enforced release on process exit — the feature Posix semaphores lack — but is bounded by semaem/semmnu/semume limits.
- Never statically initialize `struct sembuf`; declare `union semun` yourself unless the system header already does (portability guard).
- Check kernel limits (semmni/semmns/semmsl/semopm) before designing large semaphore usage — systemwide caps are tiny on classic systems.
- semctl(semid, 0, IPC_RMID) removes immediately; coordinate removal carefully.
- Prefer Posix semaphores for new code; reach for System V only for sets, arbitrary deltas, wait-for-zero, or SEM_UNDO.

## Connects To
Chapter 10 (Posix semaphores; Section 10.16 implements them atop System V), Chapter 3 (keys/ftok, ipc_perm, IPC_CREAT|IPC_EXCL semantics), Chapter 9 (record locking — auto-released on exit, contrast with semaphores), UNPv1 for slow-system-call EINTR semantics.
