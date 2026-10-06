# Chapter 16: Sun RPC

## Core Idea
Sun RPC (ONC/RPC) extends the door idea to different hosts: the client calls what looks like a local procedure, and generated stubs plus the RPC runtime marshal arguments over TCP or UDP to a server — network programming made implicit. `rpcgen` compiles a `.x` specification into client stub, server stub (with `main`), and XDR conversion routines.

## Frameworks Introduced
- **RPC via rpcgen** — write `square.x` (program/version/procedure numbers + argument/result structures), run `rpcgen`, fill in client `main` and the `*_svc` server procedure. Use when distributing an application across hosts without hand-writing sockets/XTI code.
- **10-step call model** — client → client stub (marshals args) → kernel → network → server stub (unmarshals) → server procedure → back again. Marshaling = packaging arguments into network messages.
- **Port mapper (RPCBIND) binding** — servers bind ephemeral ports and register (program, version, protocol → port) with the port mapper on port 111; `clnt_create` queries it first. Inspect with `rpcinfo -p`.
- **XDR (RFC 1832)** — external data representation: implicit typing, all items multiples of 4 bytes, big-endian, IEEE floats; usable standalone (via `xdrmem_create`) for machine-independent files/streams.
- **Timeout/retransmission + XID** — total timeout (TCP & UDP) vs retry timeout (UDP only); 32-bit transaction ID matches replies to requests; server duplicate-request cache (`svc_dg_enablecache`) for UDP.
- **Call semantics** — exactly-once / at-most-once / at-least-once; transport and cache choice determines which you actually get.

## Key Concepts
- Program (32-bit) / version / procedure numbers — three-level naming; user programs use range 0x20000000–0x3fffffff; 0x40000000+ transient.
- `clnt_create(host, prognum, versnum, "tcp"|"udp")` — returns a `CLIENT *` handle (like a `FILE *`); errors via `clnt_sperror`.
- rpcgen naming convention — `SQUAREPROC` in `.x` becomes client call `squareproc_1(&in, cl)` and server function `squareproc_1_svc(inp, rqstp)`.
- Multithreaded servers — `rpcgen -M -A`; signature changes to `bool_t squareproc_2_svc(inp, outp, rqstp)` plus a `*_freeresult` function calling `xdr_free`; default (non `-M`) server is iterative, single-threaded.
- Authentication flavors — AUTH_NONE (default), AUTH_SYS (hostname + uid/gids, spoofable), AUTH_SHORT, AUTH_DES (secure RPC), AUTH_KERB; credentials vs verifier = printed ID info vs the picture on it.
- Total timeout default — rpcgen stubs hardcode 25 s in a `TIMEOUT` passed to `clnt_call`; change with `clnt_control(CLSET_TIMEOUT)`, never by editing the stub.
- XID selection — `getpid() ^ timeval.sec ^ timeval.usec`; constant across retransmissions.
- XDR discriminated union — integer/enum/bool discriminant, then only the matching arm; `default: void;` transmits nothing.
- Optional data — three equivalent encodings: boolean-discriminated union, variable-length array `<1>`, or XDR pointer (`datatype *arg` → 4-byte flag + value, or 0 for NULL); the pointer form recursively encodes linked lists.
- TCP record marking — 4-byte fragment header (high bit = last fragment, 31-bit length) gives message boundaries over the TCP byte stream; UDP limits request+reply to one datagram (~8192 bytes in many pre-TI-RPC implementations).

## Mental Models
- Use Sun RPC when client and server live on different hosts and you want procedure-call transparency instead of explicit sockets; use doors (Ch.15) for same host.
- Use TCP by default; use UDP without a cache only for idempotent, small-payload procedures where connection overhead dominates.
- Use XDR standalone (via `xdrmem_create` + generated `xdr_*` functions) whenever binary data must move between architectures — files, sockets, or any medium.
- Use `rpcgen -M -A` whenever the server procedure may block (sleep, I/O) and concurrent clients must not serialize.

## Anti-patterns
- **UDP without a server cache for nonidempotent procedures** — dangerous: lost replies trigger retransmission and the procedure (e.g., bank debit) executes twice. Use TCP or a transaction system.
- **Hardcoded/assumed timeouts** — the stub's 25 s `TIMEOUT` overrides the "default"; set total timeout explicitly with `clnt_control(CLSET_TIMEOUT)` and verify UDP retry (15 s) rather than trusting `CLGET_TIMEOUT` (-1 for UDP).
- **AUTH_SYS as security** — trivially forged packets can claim any uid/gid; even NFS's reserved-port trick fails against a superuser on the network. Use AUTH_DES/AUTH_KERB for real authentication.
- **Static result variable in a multithreaded server** — the classic `static square_out out;` return-by-pointer pattern is not thread-safe; the `-M` interface (caller-provided `outp` + `xdr_free` in `*_freeresult`) exists precisely to fix this.
- **Editing generated stubs** — modify `.x` or use `clnt_control`/`rpcgen` options instead; regenerated files overwrite hand edits.
- **UDP for large payloads** — request and reply must each fit in one datagram (65507 B IPv4 max, ~8 K in many implementations); TCP's fragment stream has no such limit.
- **Expecting the server to notice client death under TCP** — the server thread finishes its 6-second sleep and its reply hits an RST; Sun RPC has no doors-style cancellation. Only a timeout covers all failure modes.

## Code Examples
```c
/* square.x — rpcgen spec: program/version/procedure numbering plus XDR structs. */
struct square_in  { long arg1; };            /* input  */
struct square_out { long res1; };            /* output */
program SQUARE_PROG {
    version SQUARE_VERS {
        square_out SQUAREPROC(square_in) = 1;   /* procedure #1 */
    } = 1;                                       /* version #1 */
} = 0x31230000;                                  /* program # (user range) */
```
One-line: the complete `.x` file that rpcgen turns into `square.h`, `square_clnt.c`, `square_svc.c`, `square_xdr.c`.

```c
/* Multithreaded server procedure (rpcgen -M -A). */
bool_t
squareproc_2_svc(square_in *inp, square_out *outp, struct svc_req *rqstp)
{
    outp->res1 = inp->arg1 * inp->arg1;
    return (TRUE);
}
int
squareprog_2_freeresult(SVCXPRT *transp, xdrproc_t xdr_result, caddr_t result)
{
    xdr_free(xdr_result, result);
    return (1);
}
```
One-line: thread-safe signature — result written through caller's pointer, memory freed via `xdr_free`.

## Reference Tables
**Auth flavors**
| Flavor | Meaning | Trust |
|---|---|---|
| AUTH_NONE (0) | null auth, no identity | none |
| AUTH_SYS (1) | hostname + euid + egid + gids | spoofable |
| AUTH_SHORT (2) | compact handle returned by server in verifier | shorthand for AUTH_SYS |
| AUTH_DES | secret/public key (secure RPC) | cryptographic |
| AUTH_KERB | Kerberos-based | cryptographic |

**Client (clnt_*) family** — `clnt_create`, `clnt_call` (stub uses it; total timeout arg), `clnt_control` (CLGET/CLSET_TIMEOUT, CLGET_RETRY_TIMEOUT), `clnt_destroy` (closes TCP connection), `clnt_sperror` (decode ~30 RPC_* errors).

**Server (svc_*) family** — `svc_create` (bind + register with port mapper), `svc_run` (server loop), `svc_dg_enablecache(xprt, size)` (UDP duplicate-request cache, keyed on prog/vers/proc/XID/client address), `svc_tli_create`/`svc_reg` (inetd-started servers).

**XDR filter types (xdr_*)** — `xdr_int/long/hyper`, `xdr_u_*`, `xdr_float/double/quadruple`, `xdr_bool`, `xdr_enum`, `xdr_opaque` (fixed), `xdr_bytes` (variable opaque), `xdr_string`, `xdr_array`, `xdr_reference`/`xdr_pointer` (linked structures), `xdr_union`, `xdr_free`; streams: `xdrmem_create(XDR_ENCODE|XDR_DECODE)`, `xdr_getpos`.

**Runtime scale** — 164 functions total: 11 auth_, 26 clnt_, 5 pmap_, 24 rpc_, 44 svc_, 54 xdr.

## Worked Example (rpcgen square, step by step)
1. Write `square.x` (above).
2. `rpcgen -C square.x` (ANSI prototypes) — or `rpcgen -C -M -A square.x` for multithreaded server.
3. Write `client.c`: `cl = clnt_create(host, SQUARE_PROG, SQUARE_VERS, "tcp"); outp = squareproc_1(&in, cl);` (result memory allocated by RPC runtime).
4. Write `server.c` with `squareproc_1_svc` returning `&out` (`static`).
5. Build client: `cc -o client client.o square_clnt.o square_xdr.o libunpipc.a -lnsl`; server similarly with `square_svc.o`.
6. Start server (it registers with the port mapper; daemonizes unless compiled `-DDEBUG`), then `client bsdi 11` → `result: 121`. Cross-architecture (Sparc big-endian ↔ x86 little-endian) works automatically via XDR.
7. `rpcinfo -p` shows program `824377344` (0x31230000) registered on ephemeral TCP and UDP ports.

## Key Takeaways
- rpcgen turns a `.x` spec into everything except your client `main` and server procedure — no explicit network code.
- Pick the transport deliberately: TCP default; UDP acceptable only for idempotent procedures (add `svc_dg_enablecache` if nonidempotent), TCP preferred over UDP+cache.
- Semantics ladder: TCP+reply = exactly once; TCP no reply = at most once; UDP no cache = at least once; exactly-once despite crashes needs a transaction system.
- Manage timeouts explicitly via `clnt_control`; the generated stub's 25 s overrides library defaults.
- XDR is a standalone skill: 4-byte units, big-endian, RNDUP-sized buffers, pointer notation for optional data and linked lists.
- Program numbers are namespaced (Sun / user / transient / reserved); version numbers let procedures evolve compatibly.
- Multithreading (`-M -A`) changes both signatures and requires `xdr_free` cleanup — plan for it before the server must scale.

## Connects To
- Chapter 15 (Doors): same RPC concepts minus networking, threads, and XDR; doors detect peer death via EINTR/cancellation, Sun RPC via TCP FIN or timeout.
- Chapters 7–8 (threads): multithreaded servers, thread safety of server procedures.
- Chapter 12 / Appendix A: performance comparison of IPC mechanisms vs RPC.
- UNPv1 (sockets/XTI, inetd, tcpdump): the transport underneath; `inetd.conf` `wait` entries and rpcgen's stdin-is-XTI detection.
