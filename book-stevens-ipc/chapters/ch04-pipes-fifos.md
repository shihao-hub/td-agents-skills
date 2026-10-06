# Chapter 4: Pipes and FIFOs

## Core Idea
Pipes (created by `pipe`, no name, usable only between related processes) and FIFOs (created by `mkfifo`, have a pathname, usable between unrelated processes) both provide a unidirectional byte stream accessed with normal `read`/`write`, governed by rules about blocking opens, `PIPE_BUF`-atomic writes, `SIGPIPE`, and end-of-file semantics.

## Frameworks Introduced
**pipe + fork pattern** — when a parent and child need a one-way channel: create pipe, fork, each process closes the end it doesn't use (the shell's `who | sort | lp` works this way).
**Two pipes for bidirectional flow** — Posix.1 pipes are half-duplex; for two-way exchange create pipe1 and pipe2, then close opposite ends in parent (write pipe1, read pipe2) and child.
**popen/pclose** — when you just need to run a shell command and read its output (type `"r"`) or feed its input (type `"w"`): handles pipe/fork/exec/wait for you.
**FIFO client-server pattern** — one long-running server reads a well-known-pathname FIFO; each client creates its own FIFO named with its PID and embeds the PID in its request; server replies per-client FIFO.
**Framing a byte stream** — three techniques to impose record boundaries: in-band delimiter (newline/CR-LF, needs escaping), explicit length prefix (no scanning/escaping), one record per connection.

## Key Concepts
- `int pipe(int fd[2])`: returns `fd[0]` open for reading, `fd[1]` for writing; data flows one way through the kernel (each byte crosses user–kernel boundary twice).
- `S_ISFIFO` macro on `st_mode`: tests whether a descriptor/file is a pipe or FIFO (via `fstat`/`stat`/`lstat`).
- Full-duplex pipe (SVR4 `pipe`, `socketpair`): really two half-duplex pipes — writes to `fd[1]` are read at `fd[0]` and vice versa; never one shared buffer (you'd read back your own data).
- `popen(command, type)`: forks, execs `sh -c command`, returns a `FILE*`; `pclose` closes it and returns the shell's termination status.
- `mkfifo(pathname, mode)`: implies `O_CREAT|O_EXCL` — creates new or fails with `EEXIST`; to open-if-exists, catch `EEXIST` and `open`.
- FIFO open rule: `open` for reading blocks until someone opens for writing (and vice versa) — ordering of opens matters or you deadlock.
- `O_NONBLOCK`: settable at `open` or via `fcntl(F_GETFL)` then `F_SETFL` with OR (never plain F_SETFL — it clears other flags); makes empty reads return `EAGAIN` instead of blocking.
- `PIPE_BUF` (Posix ≥512; typically 1024–5120): writes of ≤`PIPE_BUF` bytes are atomic (never interleaved); larger writes are not. Nonblocking does not affect atomicity, only whether `write` returns `EAGAIN`.
- `SIGPIPE`: writing to a pipe/FIFO not open for reading kills the process by default; ignore the signal and check `write`'s `EPIPE` return instead.
- Last close: a pipe vanishes on last close; a FIFO's data is discarded on last close but its pathname stays until `unlink`.
- Iterative vs concurrent server: iterative = one request at a time (blocking-prone, DoS-vulnerable); concurrent = fork a child per client so a stuck client stalls only its child.
- `OPEN_MAX` (query `sysconf`, change `ulimit -n`/`setrlimit`) and `PIPE_BUF` (`pathconf`/`fpathconf`, `getconf PIPE_BUF`) are the only pipe/FIFO limits.

## Mental Models
- Use a pipe when the peers have a common ancestor (parent/child after `fork`).
- Use a FIFO when the server and client are unrelated but on the same host — the name in the filesystem is the rendezvous point.
- Use `popen` when shell features (PATH lookup, redirection, pipelines) are welcome; use raw `pipe`/`fork`/`exec` when you need control and precise error messages.
- Use a length-prefixed message format (like `mymesg`) when the data may contain the delimiter; use newline framing only for text that never embeds newlines.

## Anti-patterns
- Assuming a single pipe is bidirectional — on half-duplex systems reading `fd[1]` yields `EBADF`; always allocate two pipes for two-way traffic.
- `fcntl(fd, F_SETFL, O_NONBLOCK)` without `F_GETFL`-first — clobbers all other file status flags.
- Both sides opening FIFOs for reading first — both block in `open` forever: a deadlock; open in opposite orders (one reads first, other writes first).
- Letting a server open the well-known FIFO only for reading — each client exit causes `read` to return 0; hold an extra write-only descriptor (the "dummy fd" trick) so `read` just blocks waiting for the next request.
- Iterative servers without blocking analysis — a client that never opens its reply FIFO wedges the whole server (denial of service); go concurrent or add timeouts.
- Expecting FIFOs to work across NFS — they are local-host IPC only; no data flows between hosts through an NFS-visible FIFO.
- Expecting data to survive in a FIFO after all closes — remaining data is discarded on last close.
- Forgetting to handle short `read`s — reading more than available returns only what's there; never assume the requested count.

## Code Examples
```c
/* Two pipes: bidirectional parent-child channel */
int pipe1[2], pipe2[2];
Pipe(pipe1); Pipe(pipe2);
if ((childpid = Fork()) == 0) {        /* child */
    Close(pipe1[1]); Close(pipe2[0]);
    server(pipe1[0], pipe2[1]); exit(0);
}
Close(pipe1[0]); Close(pipe2[1]);      /* parent */
client(pipe2[0], pipe1[1]);
Waitpid(childpid, NULL, 0);
```
```c
/* Correctly set nonblocking on an open descriptor (e.g., a pipe) */
int flags = fcntl(fd, F_GETFL, 0);
flags |= O_NONBLOCK;
fcntl(fd, F_SETFL, flags);
```
```c
/* Length-prefixed message framing over a byte stream */
struct mymesg { long mesg_len; long mesg_type; char mesg_data[MAXMESGDATA]; };
/* MAXMESGDATA = PIPE_BUF - 2*sizeof(long) keeps each message atomically written */
```

## Reference Tables
| Property | Pipe | FIFO |
|---|---|---|
| Creation | `pipe(fd)` (one call) | `mkfifo(pathname, mode)` + `open` |
| Name | none | filesystem pathname |
| Usable between | processes with common ancestor | any processes on the same host |
| Lifetime | disappears on last close | pathname persists until `unlink`; data discarded on last close |
| Nonblocking setup | only `fcntl` (no `open`) | `O_NONBLOCK` at `open` or `fcntl` |
| seek | `ESPIPE` error | `ESPIPE` error |
| NFS | n/a | local filesystems only |

| Operation | Blocking (default) | `O_NONBLOCK` set |
|---|---|---|
| open FIFO read-only, no writer | blocks until opened for writing | returns OK |
| open FIFO write-only, no reader | blocks until opened for reading | error `ENXIO` |
| read empty pipe/FIFO with a writer | blocks until data or all writers close | error `EAGAIN` |
| read empty pipe/FIFO, no writers | returns 0 (EOF) | returns 0 (EOF) |
| write ≤`PIPE_BUF`, no room | blocks until room | error `EAGAIN` |
| write >`PIPE_BUF`, no/partial room | blocks, partial transfers | transfers what fits or `EAGAIN` if full |
| write, no reader open | `SIGPIPE` (default kills); if ignored → `EPIPE` | same |

| Framing technique | Pros | Cons |
|---|---|---|
| In-band delimiter (newline, CR/LF) | simple, human-readable | must escape delimiter in data (FTP/SMTP/HTTP style) |
| Explicit length prefix | no scanning, no escaping | two reads per message (header then body); needs `mesg_len == 0` end marker |
| One record per connection | unambiguous end | new connection per record (HTTP/1.0 style) |

## Worked Example
One FIFO server, multiple clients: server `mkfifo("/tmp/fifo.serv")`, opens it `O_RDONLY` and also `O_WRONLY` (dummy fd so client exits never produce EOF), then loops on `readline`. Each client `mkfifo("/tmp/fifo.<pid>")`, builds the request line `"<pid> <pathname>\n"`, opens `/tmp/fifo.serv` write-only and writes it. Server parses PID, opens `/tmp/fifo.<pid>` `O_WRONLY` (blocks until client opens for reading), copies the file or an error string, closes; client reads its FIFO to EOF, then `unlink`s its own FIFO. Writes are atomic because each request line ≤ `PIPE_BUF` — two simultaneous clients never interleave inside the well-known FIFO. Testable purely from the shell: `mkfifo`, `echo "$Pid /etc/inet/ntp.conf" > /tmp/fifo.serv`, `cat < /tmp/fifo.$Pid`.

## Key Takeaways
- Close the unused end of every pipe in every process — otherwise EOF and full-close detection never work.
- For bidirectional flow use two pipes (or `socketpair`), and open FIFO ends in opposite order to avoid open-deadlock.
- Keep message writes ≤ `PIPE_BUF` for atomicity; query it with `pathconf`/`getconf` rather than hard-coding.
- Ignore `SIGPIPE` and check for `EPIPE` from `write`; always handle short reads and `EAGAIN` under `O_NONBLOCK`.
- In a FIFO server, keep a write-only descriptor open on the well-known FIFO so you never see spurious EOFs between clients.
- Frame your byte stream explicitly (length prefix beats delimiter escaping); pipes/FIFOs carry no record boundaries — message queues (Ch. 5–6) do.
- Iterative servers invite DoS; prefer concurrent (fork/thread-per-client) designs for untrusted clients.

## Connects To
- Chapter 3 (System V IPC) — SysV objects persist until removed, unlike pipes; `ftok` anchors vs FIFO pathnames.
- Chapters 5 & 6 (Posix and System V message queues) — built-in record boundaries and priorities replace the hand-rolled `mymesg` framing.
- Chapter 15 — passing descriptors between unrelated processes (the only other way pipes span unrelated processes).
- UNPv1 Chapters 14 & 27 — `socketpair` and concurrent-server techniques applied to IPC.
