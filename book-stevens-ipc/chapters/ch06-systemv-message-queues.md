# Chapter 6: System V Message Queues

## Core Idea
System V message queues are kernel-persistent linked lists of typed messages accessed via an integer identifier (not a descriptor); any process with adequate privileges can write to or read from a queue, and the per-message type field enables selective (non-FIFO) retrieval and multiplexing of messages from many senders onto one queue.

## Frameworks Introduced
- **msgget/msgsnd/msgrcv/msgctl API family** — the four System V message queue calls. Use when maintaining/porting legacy System V IPC code; prefer Posix message queues for new applications.
- **Typed-message multiplexing** — use the `mtype` field (must be > 0) to tag messages by sender/priority; `msgrcv`'s `type` argument selects which message to read.
- **Queue topology patterns** — (a) one queue per direction, (b) single shared queue with type 1 for client→server and client PID as reply type, (c) one well-known server queue + one `IPC_PRIVATE` queue per client (concurrent server, fork per client).

## Key Concepts
- `msqid_ds`: kernel-maintained per-queue structure (permissions, counts, PIDs, timestamps).
- `msgget(key, oflag)`: creates or opens a queue; key from `ftok` or `IPC_PRIVATE`; returns identifier used by other msg functions.
- `msgsnd(msqid, ptr, length, flag)`: appends a message (`long mtype` + data); length excludes the type field and may be 0.
- `msgrcv(msqid, ptr, length, type, flag)`: retrieves a message selectively by type; returns data-byte count.
- `msgctl(msqid, cmd, buff)`: `IPC_RMID` (remove), `IPC_SET` (set uid/gid/mode/qbytes), `IPC_STAT` (fetch status).
- `type == 0` → oldest message; `type > 0` → first message of that type; `type < 0` → lowest type ≤ |type|.
- `IPC_NOWAIT`: nonblocking send (`EAGAIN`) / receive (`ENOMSG`); `MSG_NOERROR` truncates oversized messages instead of `E2BIG`.
- Kernel persistence: queues survive until explicitly removed (`msgctl IPC_RMID` / `ipcrm`) or kernel reboot.
- Identifiers are not descriptors → cannot be used with `select`/`poll` (AIX extension is nonportable).

## Mental Models
- Use a **single queue with type multiplexing** when you want bidirectional client-server traffic over one IPC channel; type 1 = requests, PID = replies.
- Use **one queue per client (`IPC_PRIVATE`)** when a concurrent (fork-per-client) server must not contend on one reply channel.
- Use **nonblocking writes in the server** to detect the deadlock that always threatens a single shared queue (clients fill it, server blocks in `msgsnd`).
- Use the **child-blocks-in-msgrcv + pipe** bridge when a server must `select` over both network descriptors and message queues.

## Anti-patterns
- **Relying on queue auto-cleanup**: queues are kernel-persistent; a client that dies leaves its private queue (and messages) until reboot or explicit `ipcrm` — always `msgctl(id, IPC_RMID, NULL)` on exit.
- **Assuming generous limits**: systemwide caps exist — `msgmax` (bytes/message, e.g. 2048), `msgmnb` (bytes/queue, e.g. 4096), `msgmni` (queues, e.g. 50), `msgtql` (messages systemwide, e.g. 40). Heavy use requires kernel tuning.
- **Blocking `msgrcv` for an absent type** without `IPC_NOWAIT`: the call hangs until that type arrives; interrupt-driven servers must also handle `EINTR` (SIGCHLD handlers interrupt `msgrcv`).
- **Treating identifiers as descriptors**: no `select`/`poll`, no message peek (no `MSG_PEEK` equivalent).
- **Assuming a portable max message size**: there is no API to query it; define your own bound or probe like the book's `limits.c`.

## Code Examples
```c
/* Template message structure: a long type followed by application data */
struct msgbuf {
    long mtype;     /* message type, must be > 0 */
    char mtext[1];  /* message data (binary or text; kernel never interprets it) */
};

/* Typical app-specific message: length passed as sizeof(Message) - sizeof(long) */
typedef struct {
    long   mtype;
    int16_t mshort;
    char   mchar[8];
} Message;
```
Defines the msgbuf template and the custom-structure idiom for message data.

```c
msqid = Msgget(IPC_PRIVATE, SVMSG_MODE | IPC_CREAT);
Msgsnd(msqid, &buf, 1, 0);
Msgctl(msqid, IPC_STAT, &info);
system("ipcs -q");
Msgctl(msqid, IPC_RMID, NULL);   /* lifecycle: create → use → inspect → remove */
```
Full queue lifecycle using all four msg functions.

## Reference Tables

### struct msqid_ds members (<sys/msg.h>)
| Member | Meaning |
|---|---|
| `struct ipc_perm msg_perm` | ownership & permissions (uid, gid, cuid, cgid, mode) |
| `msg_qnum` | current # of messages on queue |
| `msg_qbytes` | max # of bytes allowed on queue (system limit at creation) |
| `msg_cbytes` | current # of bytes on queue |
| `msg_lspid` / `msg_lrpid` | PID of last `msgsnd` / `msgrcv` |
| `msg_stime` / `msg_rtime` / `msg_ctime` | time of last send / receive / `msgctl` change |
| `msg_first` / `msg_last` | kernel-internal list pointers (useless to apps; not in Unix 98) |

### msgctl commands
| Command | Effect |
|---|---|
| `IPC_RMID` | remove queue, discard all messages (3rd arg ignored) |
| `IPC_SET` | set `msg_perm.uid`, `msg_perm.gid`, `msg_perm.mode`, `msg_qbytes` |
| `IPC_STAT` | copy current `msqid_ds` to caller's buffer |

### Typical kernel limits
| Name | Description | Solaris 2.6 | DUnix 4.0B |
|---|---|---|---|
| `msgmax` | max bytes per message | 2048 | 8192 |
| `msgmnb` | max bytes per queue | 4096 | 16384 |
| `msgmni` | max queues systemwide | 50 | 64 |
| `msgtql` | max messages systemwide | 40 | 40 |

## Worked Example: msgctl IPC_RMID lifecycle + msgrcv type selection
```c
/* msgrmid: remove a queue given its ftok pathname */
msqid = Msgget(Ftok(argv[1], 0), 0);
Msgctl(msqid, IPC_RMID, NULL);

/* Type selection against queue holding types 100(1B), 200(2B), 300(3B):
   msgrcv -t 200   -> "read 2 bytes, type = 200"   (exact type match)
   msgrcv -t -300  -> "read 1 bytes, type = 100"   (lowest type <= 300)
   msgrcv          -> "read 3 bytes, type = 300"   (FIFO: oldest first)
   msgrcv -n       -> ENOMSG ("No message of desired type") */

/* Single-queue multiplexing convention (server side) */
mesg.mesg_type = 1;                      /* read client requests: type 1 */
n = Mesg_recv(readfd, &mesg);
/* parse client PID from message data */
mesg.mesg_type = pid;                    /* replies carry client PID as type */
Mesg_send(writefd, &mesg);

/* EINTR-safe receive wrapper (SIGCHLD interrupts msgrcv) */
ssize_t Mesg_recv(int id, struct mymesg *mptr) {
    ssize_t n;
    do {
        n = mesg_recv(id, mptr);
    } while (n == -1 && errno == EINTR);
    if (n == -1) err_sys("mesg_recv error");
    return n;
}
```

## Key Takeaways
- Always remove queues explicitly (`msgctl IPC_RMID` or `ipcrm -q id` / `ipcrm -Q key`); the kernel never garbage-collects them.
- Exploit the type field: selective receive order (`0`/positive/negative) and multiplexing many clients onto one queue.
- Any process can read a queue knowing only the identifier (from `ipcs`) plus read permission — msgget is not a gate.
- Both `msgsnd` and `msgrcv` block by default; handle `EAGAIN`, `EIDRM` (queue removed while blocked), and `EINTR` (signal interruption).
- For new code prefer Posix message queues; the one System V feature Posix lacks is reading by specified priority/type.
- Budget against systemwide limits (`msgmax`/`msgmnb`/`msgmni`/`msgtql`) and tune the kernel for queue-heavy applications.

## Connects To
- Ch 3 (ftok keys, ipc_perm, IPC_CREAT/IPC_EXCL, system limits); Ch 5 (Posix message queues comparison — no notification capability in System V); Ch 4 (pipes/FIFOs client-server recoded here); Ch 10–11 (semaphores as alternative synchronization); Ch 12/14 (shared memory + queue-as-flag to avoid triple-copying in the select bridge).
