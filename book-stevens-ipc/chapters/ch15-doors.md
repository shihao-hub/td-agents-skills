# Chapter 15: Doors

## Core Idea
Doors are a Solaris IPC mechanism that let a process call a procedure in another process on the same host — a synchronous, same-host RPC with kernel support, faster than all other message-passing IPC (Appendix A). A server attaches a door (created with `door_create`) to a filesystem pathname via `fattach`; clients `open` the pathname and call `door_call`.

## Frameworks Introduced
- **Doors RPC model** — three procedure-call types: local, remote-on-same-host (doors), remote-across-network (RPC, Ch.16). Use doors when client and server share a host and you want procedure-call semantics with minimal latency.
- **Door lifecycle** — server: `door_create(proc, cookie, attr)` → create file → `fattach(fd, path)` → `pause`. Client: `open(path, O_RDWR)` → `door_call(fd, &arg)`. Server procedure ends with `door_return(...)` (never `return`).
- **Automatic thread management** — the doors library spawns server threads on demand; one thread per concurrent client call → concurrent server by default. Override with `door_server_create` + your own `pthread_create` loop.
- **Descriptor passing** — door calls can carry open descriptors (`door_desc_t` array) in both directions; inherent to doors, no separate socket machinery.
- **DOOR_UNREF reference-count protocol** — server procedure is invoked with `dataptr == DOOR_UNREF_DATA` when the last external reference (client descriptors + pathname) drops away; used for cleanup.

## Key Concepts
- `door_arg_t` — the 6-member struct (data_ptr/data_size, desc_ptr/desc_num, rbuf/rsize) describing both arguments and results; all members may change on return.
- `door_return` — the only way a server procedure completes; it performs a system call back into the kernel and never returns to the caller on success.
- `door_cred` — server-side call returning client's euid/egid/ruid/rgid/pid per invocation (no descriptor argument; valid only inside a server procedure).
- `door_info` — client-side query of server PID, procedure address, cookie, attributes, and a systemwide unique door ID; `S_ISDOOR` on `fstat` verifies a pathname is a door.
- `DOOR_PRIVATE` — gives a door its own thread pool separate from the process-wide pool; pairs with `door_bind`/`door_unbind`.
- Result-buffer growth — if `rbuf` is too small, the library `mmap`s a page-sized buffer and updates `rbuf`/`rsize`; client should always read results via `data_ptr`, never via the original variable.
- Premature server termination → client's `door_call` returns `EINTR`; `door_call` is not restartable — block signals during the call.
- Premature client termination → server thread receives a pthread cancellation request (cleanup handlers run) if cancellation is enabled.
- Idempotent procedure — safe to call any number of times (e.g., square); nonidempotent (e.g., bank debit) makes blind retry after EINTR dangerous.

## Mental Models
- Use doors when both processes are on the same Solaris host and you want the fastest IPC with procedure-call syntax; use Sun RPC (Ch.16) across hosts.
- Use `door_cred` on every call when the server must authorize per-client (like an implicit credential handshake); plain `open` permission bits are the only other gate.
- Use `door_server_create` when you need custom thread attributes (stack size, cancellation on, bound threads); rely on the default pool otherwise.
- Use descriptor passing when the server should open a resource (e.g., a file) and hand the handle back, instead of copying the data.

## Anti-patterns
- **Reading results through the original buffer variable** — the library may have reallocated `rbuf` via `mmap`; always dereference `arg.data_ptr` after `door_call`, and `munmap` if `rbuf` changed.
- **Retrying `door_call` on EINTR without thinking** — a caught signal (e.g., SIGCHLD) interrupting the call does NOT stop the server procedure; retrying executes the procedure a second time. Only safe for idempotent procedures; better: block signals around the call.
- **Server procedures that aren't thread-safe** — multiple instances run concurrently (one thread per client); static/automatic shared state without locks corrupts results.
- **Passing descriptors then trying to close them after `door_return`** — `door_return` never returns, so the server leaks descriptors (values keep climbing). Pre-2.7 workaround is messy bookkeeping; `DOOR_RELEASE` attribute fixes it.
- **Unbound threads (`PTHREAD_SCOPE_PROCESS`) in custom server creation** — doors requires the same lightweight process that received the invocation to execute `door_return`; use `PTHREAD_SCOPE_SYSTEM` and detached threads.
- **Forgetting the `fd` race in `door_server_create`** — the creation procedure runs before `door_create` returns, so the door descriptor isn't valid yet; guard it with the mutex trick (lock around `door_create`, lock/unlock in the thread start function).

## Code Examples
```c
/* Minimal door server procedure: squares a long passed as raw data. */
void
servproc(void *cookie, char *dataptr, size_t datasize,
         door_desc_t *descptr, size_t ndesc)
{
    long arg = *((long *) dataptr);
    long result = arg * arg;
    door_return((char *) &result, sizeof(result), NULL, 0); /* never returns */
}
/* server main: fd = door_create(servproc, NULL, 0);
   unlink(path); close(open(path, O_CREAT|O_RDWR, FILEMODE));
   fattach(fd, path); for(;;) pause(); */
```
One-line: the complete doors server-procedure pattern — arguments via `dataptr`, results via `door_return`.

## Reference Tables
| Function | Role |
|---|---|
| `door_call(fd, argp)` | client invokes server procedure (synchronous) |
| `door_create(proc, cookie, attr)` | server creates door descriptor; attr: 0 / DOOR_PRIVATE / DOOR_UNREF |
| `door_return(dataptr, datasize, descptr, ndesc)` | server procedure returns data/descriptors to client |
| `door_cred(cred)` | server gets client credentials (euid/egid/ruid/rgid/pid) |
| `door_info(fd, info)` / `DOOR_QUERY` | info about a door (server) or calling thread (server proc) |
| `door_server_create(proc)` | install custom server-thread creation procedure |
| `door_bind(fd)` / `door_unbind()` | bind/unbind calling thread to a door's private pool |
| `door_revoke(fd)` | creator invalidates a door; in-progress calls complete |
| `fattach(fd, path)` / `fdetach` | associate door descriptor with a pathname |

## Worked Example (client/server flow)
1. Server starts: `fd = door_create(servproc, NULL, 0)`; `unlink("/tmp/server1")`; create file; `fattach(fd, "/tmp/server1")`; main thread `pause()`s forever.
2. Client: `fd = open("/tmp/server1", O_RDWR)`; fill `door_arg_t`: `data_ptr=&ival, data_size=sizeof(long), desc_ptr=NULL, desc_num=0, rbuf=&oval, rsize=sizeof(long)`.
3. `door_call(fd, &arg)` → kernel switches control into a doors-library thread in the server; `servproc` runs, squares the value, calls `door_return`.
4. Control returns to the client; print `*((long *) arg.data_ptr)` → `result: 81` for input 9. `ls -l` shows the pathname's type character `D` (door).
5. Concurrency check: run 3 clients during a 5-second `sleep` in `servproc` — the library spawns threads 5 and 6; all three results appear after 5 s total → concurrent server, thread-safe procedures required.

## Key Takeaways
- Doors = same-host RPC with the lowest latency; learn RPC concepts here before Ch.16 adds networking.
- A server procedure never returns; it terminates with `door_return`, which carries both data and descriptor results.
- Always read door results through `arg.data_ptr`, and watch for the `mmap`-allocated result buffer (`rbuf` change).
- `door_cred` gives free per-call client credentials — use them for server-side authorization decisions.
- Block signals around `door_call` (EINTR is unrestartable), and classify every procedure idempotent vs nonidempotent before writing any retry logic.
- Default thread pooling is fine; only take over with `door_server_create` + `door_bind` when you must control thread attributes.

## Connects To
- Chapter 16 (Sun RPC): doors are the same-host special case; Ch.16 generalizes to networked hosts and adds XDR.
- Chapter 7/8 (mutexes, threads): custom thread pools need detached, system-scope, cancellation-disabled threads.
- Chapter 12/Section 12.2 (`mmap`): automatic result-buffer allocation; `munmap` to release.
- Chapter 4/17 (descriptor passing): compare with Unix-domain-socket `sendmsg` and SVR4 `I_SENDFD`/`I_RECVFD`.
- Appendix A: doors benchmark as fastest IPC.
