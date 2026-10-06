# Patterns — UNP Vol 2 (Stevens)

## pipe + fork one-way channel
**When to use**: parent/child (related processes) need a unidirectional byte stream.
**How**: pipe(fd); fork(); parent closes fd[0], child closes fd[1] (each closes the unused end first).
**Trade-offs**: no names (can't be opened by unrelated processes); data crosses the kernel twice.

## Two-pipe bidirectional protocol
**When to use**: request/response between parent and child over pipes.
**How**: create pipe1 and pipe2; parent writes pipe1 & reads pipe2, child the mirror; close the three unused ends in each.
**Trade-offs**: deadlocks if both sides block on read — fix with select/poll or O_NONBLOCK.

## FIFO client-server rendezvous
**When to use**: unrelated processes, one server many clients, same host.
**How**: server reads a well-known-pathname FIFO; each client mkfifo's /tmp/serv.<pid>, embeds pid in request; server opens each per-client FIFO for write. Server holds a dummy write fd on the well-known FIFO so read never sees EOF.
**Trade-offs**: iterative server is DoS-prone; go concurrent (fork per client).

## Byte-stream framing
**When to use**: pipes/FIFOs/TCP carry records but are unstructured byte streams.
**How**: (1) in-band delimiter (newline) — escape if data can contain it; (2) fixed/length-prefixed header — no scanning; (3) one record per connection.
**Trade-offs**: delimiter is cheapest but fragile with binary data; length-prefix needs both ends to agree on width/endianness.

## Create-or-open with exclusive semantics
**When to use**: any IPC object that might already exist (mq_open, sem_open, shm_open, open O_CREAT, msgget IPC_CREAT).
**How**: try O_CREAT|O_EXCL (or IPC_CREAT|IPC_EXCL); on EEXIST, reopen without it. For System V semaphores the opener must then poll IPC_STAT until sem_otime != 0 — the creator sets it nonzero only after initialization completes.
**Trade-offs**: System V's create+init is two steps, hence the race fix; Posix does create+init atomically.

## Condition-variable wait/signal idiom
**When to use**: a thread must wait for a state predicate (buffer not full/empty), not just mutual exclusion.
**How**: lock mutex; while (predicate false) pthread_cond_wait(&c, &m); act; unlock (signal/broadcast before or after unlock — both correct under the idiom).
**Trade-offs**: `if` instead of `while` breaks under spurious wakeups and multi-consumer signals; broadcast instead of signal wastes wakeups but is safe.

## Producer-consumer with counting semaphores
**When to use**: bounded buffer between producers and consumers (threads or processes).
**How**: mutex=1, nempty=nbuffers, nstored=0. Producer: wait(mutex)+wait(nempty), store, post both. Consumer: wait(mutex)+wait(nstored), fetch, post both. Multiple consumers terminate via a sentinel item per consumer.
**Trade-offs**: always acquire in the same order (mutex then counter); swapping the order deadlocks.

## Read-write lock from mutex + two condition variables
**When to use**: read-mostly data needing concurrent readers; implementing rwlocks yourself to learn/control policy.
**How**: one mutex, rwlock's nreaders counter, waiting-writer flag, reader-wait and writer-wait condvars. Readers skip waiting only if no waiting writer; a writer signals readers or next writer on unlock.
**Trade-offs**: naive versions starve writers — the waiting-writer counter is what enforces fairness.

## Record locking with fcntl
**When to use**: cooperative byte-range locking on a real file (config, database, log offsets).
**How**: fill struct flock (l_type F_RDLCK/F_WRLCK/F_UNLCK, l_whence SEEK_SET, l_start, l_len=0-to-EOF); F_SETLK (non-blocking, retry on EACCES/EAGAIN) or F_SETLKW; never F_GETLK to test-then-set — that's a race, just try to set.
**Trade-offs**: advisory only unless the filesystem is mounted for mandatory locking (rare, risky); closing any fd on the file releases all the process's locks on it.

## Single-instance daemon
**When to use**: exactly one copy of a daemon must run.
**How**: open(pidfile, O_RDWR|O_CREAT), write pid, fcntl-write-lock byte 0. A second instance's F_SETLK fails → exit.
**Trade-offs**: kernel releases the lock on death — no stale-lock problem; PID in the file is for humans, the lock is the guarantee.

## Shared memory + process-shared synchronization
**When to use**: highest-throughput sharing of structured data between processes.
**How**: mmap (MAP_SHARED, ftruncate'd file, or shm_open object, or anon MAP_SHARED between parent/child); place a mutex/condvar/semaphore *inside* the region initialized with PTHREAD_PROCESS_SHARED before other processes map it; store offsets, not pointers.
**Trade-offs**: fastest but no kernel cleanup — a crashed process can leave the mutex locked (no auto-release); persistence must be managed by unlink/msync.

## mq_notify notification
**When to use**: waiting on a Posix MQ without blocking a thread.
**How**: exactly one process may be registered; signal (SIGEV_SIGNAL + sigaction with SA_RESTART off) or a new thread per message (SIGEV_THREAD) — but a signal only means "queue became non-empty", so drain with non-blocking mq_receive until EAGAIN.
**Trade-offs**: registration is consumed by one message; re-register each iteration.

## System V semaphore wrapper (10-op helper)
**When to use**: needing Posix-like binary semaphores on platforms lacking Posix sems.
**How**: implement sem_create (create/init with race fix), sem_wait (sem_op=-1, undo), sem_post (sem_op=+1) over semget/semop/semctl.
**Trade-offs**: SEM_UNDO adjustments run in undefined order at exit — processes can release locks they shouldn't; avoid undo where possible.

## Doors client/server
**When to use**: Solaris-local, low-latency RPC to a library procedure.
**How**: server door_create(proc) + fattach; client open(door path) + door_call with door_arg_t (in/out buffers + descriptor array); door_return returns data; credentials via door_cred.
**Trade-offs**: default thread-per-invocation is unbounded — install door_server_create with your own pool; handle client death (door revoke/cancel) and signal-block/EINTR retry.

## rpcgen RPC service
**When to use**: network-transparent procedure calls (Sun RPC).
**How**: write the .x spec (program/version/procedure, XDR types incl. discriminated unions); rpcgen generates stubs + xdr filters; client clnt_create; server svc_run. Set timeouts via clnt_control; use TCP or a duplicate-request cache when at-most-once matters.
**Trade-offs**: UDP+timeout-retry default is at-least-once (idempotent procedures only); stub's 25s total timeout is hardcoded — override it.
