# Chapter 9: Record Locking

## Core Idea
`fcntl` record locking provides kernel-maintained read/write locks over byte ranges of a file, shared between related or unrelated processes (owner identified by PID) — better termed "range locking" since Unix has no record concept. Posix defines only advisory locking; cooperation is required for correctness.

## Frameworks Introduced
- **Posix fcntl record locking** — lock/unlock byte ranges of a file via `fcntl(fd, F_SETLK/F_SETLKW/F_GETLK, &flock)`. Use for mutual exclusion between unrelated processes (e.g., sequence-number files, single-instance daemons) where shared-memory sync is impractical.
- **Sequence-number-increment pattern** — read / use / increment-and-write a number file; the three steps must be atomic w.r.t. other processes; wrap them in `my_lock`/`my_unlock` (a critical region).
- **Lock file via open(O_CREAT|O_EXCL)** — atomic create-if-not-exists as a lock; release by `unlink`. Legacy; inferior to fcntl (orphan files, polling, slow).
- **link() and O_CREAT|O_WRONLY|O_TRUNC-mode-0 tricks** — older filesystem-based locking hacks; recognize, don't write new code with them.
- **Single-daemon-instance lock file** — write-lock a PID file at startup; kernel auto-releases the lock if the daemon crashes.
- **NFS locking (lockd/statd)** — fcntl locking over NFS works via lockd (lock requests) and statd (crash recovery); slower (~80x) and implementation-quality-dependent.

## Key Concepts
- Granularity: size of lockable object; Posix record locking granularity is a single byte; finer granularity → more simultaneous users.
- Whole-file lock: `l_whence=SEEK_SET, l_start=0, l_len=0` (length 0 = to EOF, incl. future growth).
- Advisory locking: kernel tracks locks but doesn't block I/O; only affects processes that explicitly test/set locks.
- Mandatory locking: kernel checks every read/write against locks (SVR3+; enabled by set-group-ID on + group-execute off; `ls` shows `l`, `chmod +l`).
- Locks removed when ANY descriptor for that file is closed by the process, or on process termination; locks not inherited across fork.
- F_SETLK vs F_SETLKW: non-blocking (EACCES/EAGAIN) vs blocking ("wait") acquisition.
- F_GETLK tests whether a conflicting lock exists; returns holder's PID in `l_pid`, or sets `l_type=F_UNLCK`; F_GETLK + F_SETLK is NOT atomic.
- Per-process, not per-thread: locks are owned by (pid, file); a second thread in the same process can "overwrites"/release locks unknowingly — not for intra-process thread sync.
- Read lock requires fd open for reading; write lock requires open for writing.
- fcntl record locking is the ONLY sync technique (besides optional SysV sems) whose locks the kernel releases on process termination.

## Mental Models
- Use fcntl write lock (F_SETLKW, whole file) when multiple unrelated processes read-modify-write the same file.
- Use a write-locked PID file when a daemon must guarantee only one running copy.
- Use F_GETLK only for diagnostics (who holds the lock); never as a test-then-set — use F_SETLK/F_SETLKW directly.
- Use read/write locks on ranges when multiple processes access different records of one file concurrently; use whole-file lock when they touch the same data.
- Don't use record locking with stdio (internal buffering); use raw read/write on locked files.

## Anti-patterns
- Relying on advisory locks against uncooperative processes — a nonlocking process reads/writes right through the lock.
- Believing mandatory locking fixes rogue processes — it blocks reads *during* the lock, but a process mid-update (read done, write pending) is still clobbered; mandatory locking still yields corrupt data (measured 14,378 vs 20,001).
- Closing any fd on the file drops the process's locks on that entire file — a stray close in a library routine silently releases everything.
- F_GETLK then F_SETLK as an atomic sequence — another process can grab the lock between the calls.
- Static initializer `struct flock lock = {F_WRLCK, SEEK_SET, 0, 0, 0}` — member order is unspecified; assign fields individually.
- Using pid_t with %d — cast to long, print %ld.
- lock-file-with-O_EXCL polling loops — orphaned lock files after crash, CPU-wasting retries, ~75x slower than fcntl.
- Assuming writer/reader priority — unspecified; Solaris/Digital Unix grant FIFO, BSD/OS favors readers; readers can starve writers.
- Locking between threads of one process — locks are per-process, so threads can unlock each other's "locks".

## Code Examples
```c
/* Write-lock an entire file, blocking until granted (lock/lockfcntl.c) */
void my_lock(int fd)
{
    struct flock lock;
    lock.l_type   = F_WRLCK;   /* exclusive write lock */
    lock.l_whence = SEEK_SET;  /* offset from start of file */
    lock.l_start  = 0;
    lock.l_len    = 0;         /* 0 = lock whole file, to EOF */
    fcntl(fd, F_SETLKW, &lock); /* W = wait (block) if held */
}
void my_unlock(int fd)
{
    struct flock lock;
    lock.l_type   = F_UNLCK;
    lock.l_whence = SEEK_SET;
    lock.l_start  = 0;
    lock.l_len    = 0;
    fcntl(fd, F_SETLK, &lock); /* release never blocks */
}
```
Demonstrates the canonical whole-file mutual-exclusion lock/unlock pair.

```c
/* Generic wrapper (lib/lock_reg.c) backing macros:
   writew_lock(fd,offset,whence,len), read_lock(...), un_lock(...) */
int lock_reg(int fd, int cmd, int type, off_t offset, int whence, off_t len)
{
    struct flock lock;
    lock.l_type   = type;    /* F_RDLCK, F_WRLCK, F_UNLCK */
    lock.l_start  = offset;
    lock.l_whence = whence;
    lock.l_len    = len;
    return fcntl(fd, cmd, &lock);
}
```

## Reference Tables

**struct flock fields**

| Field | Meaning |
|---|---|
| `l_type` | F_RDLCK (shared), F_WRLCK (exclusive), F_UNLCK (release) |
| `l_whence` | SEEK_SET / SEEK_CUR / SEEK_END — interpretation of l_start |
| `l_start` | relative starting byte offset |
| `l_len` | number of bytes; 0 = from start offset to EOF (whole file if start 0) |
| `l_pid` | output: PID of lock holder, filled in by F_GETLK |

**fcntl lock commands**

| cmd | Behavior on conflict | Returns |
|---|---|---|
| F_SETLK | returns immediately | -1 with EACCES or EAGAIN |
| F_SETLKW | blocks until grantable | 0 on grant |
| F_GETLK | test only (not atomic with SETLK) | overwrites flock: l_type=F_UNLCK if free, else holder's l_pid |

**Advisory vs mandatory locking**

| | Advisory (Posix.1) | Mandatory (SVR3+, non-Posix) |
|---|---|---|
| Enforcement | kernel tracks locks; I/O never blocked | kernel checks every read/write against locks |
| Uncooperative process | reads/writes right through lock | blocking fd sleeps, nonblocking fd gets EAGAIN |
| Correctness | works iff all processes cooperate | still corruptible (update mid-range not atomic); rogue still causes havoc |
| Enable | default | group-execute off + set-group-ID on (chmod +l) |
| Recommendation | use this | avoid; doesn't solve the problem |

## Worked Example: start only one copy of a daemon
```c
#define PATH_PIDFILE "pidfile"
int pidfd = Open(PATH_PIDFILE, O_RDWR | O_CREAT, FILE_MODE);
if (write_lock(pidfd, 0, SEEK_SET, 0) < 0) {
    if (errno == EACCES || errno == EAGAIN)
        err_quit("unable to lock %s, is %s already running?",
                 PATH_PIDFILE, argv[0]);
    else
        err_sys("unable to lock %s", PATH_PIDFILE);
}
/* write my PID, leave file open to hold the write lock */
snprintf(line, sizeof(line), "%ld\n", (long) getpid());
Ftruncate(pidfd, 0);              /* avoid stale leftover digits */
Write(pidfd, line, strlen(line));
```
Walkthrough: 1) open/create the PID file; 2) attempt a nonblocking write lock of the whole file — failure with EACCES/EAGAIN proves another copy holds the lock (running), so exit with a clear message; 3) truncate then write our PID (truncation prevents a shorter new PID leaving residue like `123\n6\n`); 4) never close the descriptor — the lock lives as long as the fd; the kernel releases it automatically if the daemon crashes, which (unlike O_EXCL lock files) leaves no stale lock file behind.

## Key Takeaways
- Wrap read-use-write sequences on shared files in F_SETLKW write locks; test correctness with high loop counts (e.g., 20 × 10,000 → expect 200,001), since short runs can hide races.
- Never depend on advisory locks to stop processes that don't lock; and don't expect mandatory locking to save you either — all updaters must cooperate.
- Keep the locked fd open for the daemon's lifetime; any close of any fd on that file releases all the process's locks on it.
- Use SEEK_SET/0/0 for whole-file locks; fill struct flock member-by-member (order unspecified).
- Prefer fcntl locking over O_EXCL/link/O_TRUNC lock-file tricks: kernel crash cleanup, blocking instead of polling, ~75x faster.
- Reader/writer grant priority is implementation-defined (FIFO on Solaris/Digital, reader-priority on BSD/OS); if it matters, build your own read-write lock (Ch. 8).
- fcntl locks are per-process — use them between processes, not threads; use read/write instead of stdio on locked files; NFS locking (lockd/statd) works but is slower and quality-dependent.

## Connects To
- Chapter 7 (Mutexes/Condition Variables): same mutual-exclusion problem, in-process; termination cleanup contrast.
- Chapter 8 (Read-Write Locks): fcntl locks are range-based read-write locks; priority differences motivate custom rwlock implementations.
- Part 4 (Shared Memory): alternative for unrelated-process sharing with in-memory sync variables.
- Chapters on semaphores (Posix/SysV): alternative single-instance-daemon and locking mechanism; only SysV sems (optionally) share the auto-cleanup property.
