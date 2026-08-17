# PTorrent Core — C

The platform-independent core. Every GUI is a *face* over this library; nothing
in here knows a face exists.

```
    ┌──────────────── libptorrent ────────────────┐
    │  .ptorrent parse + validate                 │
    │  j_expr compile + evaluate                  │
    │  σ-face classification + tally              │
    │  JSON (no external dependency)              │
    │  ───────────── stable C ABI ─────────────   │
    └──┬─────────┬──────────┬──────────┬──────────┘
       │         │          │          │
    curses    Android    Windows     Swift
    (direct)   (JNI)   (P/Invoke)   (module map)
```

## Build

```sh
make          # static + shared + tests
make test     # build and run the suite
make static   # libptorrent.a only
make install  PREFIX=/usr/local
```

No dependencies beyond a C99 compiler and libc. If this ever needs a platform
SDK to produce `libptorrent`, the layering has failed.

Cross-compiling is the normal case, not the exception:

```sh
make CC=aarch64-linux-android21-clang               # Android NDK
make CC="xcrun -sdk iphoneos clang -arch arm64"     # iOS
make CC=x86_64-w64-mingw32-gcc SHLIB=ptorrent.dll   # Windows
```

## The design contract

Eight rules, stated in full at the top of `include/ptorrent.h`. The short form:

1. **C ABI only.** C++ name mangling is not stable across compilers; every
   consumer speaks C.
2. **Opaque handles.** Callers hold pointers, never layouts.
3. **No struct-by-value across the boundary.** P/Invoke and JNI marshal
   by-value aggregates inconsistently.
4. **No callbacks into the caller.** Progress is polled. Cross-FFI callbacks
   require attaching foreign threads to a managed runtime and are the largest
   single source of FFI crashes.
5. **The core never owns the process.** No daemonising, no `fork`, no signal
   handlers, no thread outliving a call the caller did not make.
6. **No ambient paths.** Every filesystem root is injected by the host.
7. **Cooperative, flag-based cancellation.** Never signals.
8. **UTF-8 everywhere.** Returned strings are owned by the handle that produced
   them.

Rules 5 and 6 exist because **iOS is the most constrained target**, and obeying
it makes the core embeddable in an Android Service, a Windows service, a .NET
GUI, and a `select()` loop without changing a line. Fix it for the hardest
platform and the rest follow.

## Evaluation is data, not code

`j_expr` is a whitelisted arithmetic expression over column names. There is no
escape hatch, no dynamic loading, no host callback, and no operation outside
the published list.

That is what makes it safe to accept another researcher's evaluation over the
distribution network and run it. A whitelisted expression is sandboxable on
every platform; a downloaded shared object is sandboxable on none, and iOS
forbids the latter outright (App Store 2.5.2).

```
expr    := term (('+' | '-') term)*
term    := unary (('*' | '/') unary)*
unary   := ('-' | '+') unary | power
power   := primary ('**' unary)?          right-associative
primary := NUMBER | IDENT | CALL | '(' expr ')'
```

Functions `sqrt abs log log10 exp` (1 argument), `max min` (2 arguments).
Constants `pi e`. Precedence follows Python exactly — `-2**2` is `-4` and
`2**-1` is `0.5` — because every published `j_expr` was written by someone
thinking in Python, and a silent sign flip corrupts a result rather than
failing it.

### NaN discipline

Division by zero yields **NaN, not infinity**, and a non-finite J classifies as
`PT_SIGMA_UNDEFINED`, never `PT_SIGMA_INF`.

This is deliberate and load-bearing. The INF face is entered from *both* ends
of the published band table — it means "compressible limit" below `d*` and
"force extreme" above `1/d* + Ω`. If an unmeasurable row could also land there,
the one already-ambiguous bucket would silently fill with rows carrying no
measurement at all. A row that could not be measured must be counted as
unmeasured.

Missing/NULL columns, `sqrt` of a negative, `log` of a non-positive, and
overflow all produce NaN and propagate. A column bound to NULL is a *data*
condition (NaN, `PT_OK`); a column never bound at all is a *configuration*
error (`PT_E_NOTFOUND`), surfaced on the first row rather than after
traversing 128 GB.

## Fail-closed choices

Places where this core deliberately differs from the Python reference:

| situation | Python | here |
|---|---|---|
| corpus job with neither `txt` nor `urls` | "fails silently" (spec note) | rejected at parse |
| corpus job with no `bin` | accepted | rejected at parse |
| evaluation with no J method | accepted | rejected at parse |
| unreadable corpus list file | `except OSError: pass` → empty list | `PT_E_IO` |
| corpus tag with `_` or a digit | silently dropped by `^\[([A-Z]+)\]` | parsed |
| unparseable corpus line | silently skipped | counted and reported |
| duplicate URL in a list | invisible | counted and reported |
| unmodelled JSON fields | discarded | retained, so a v1.1 core carries a v1.2 file through a distribution hop intact |

## Parked

The `security` block is parsed and goes no further. No `.ptorrent` in the
repository carries one, and the `embargo_until` date model is wrong for the
case it was aimed at: coordinated disclosure gates on a record **state**, not a
calendar date. A CVE ID that is RESERVED is not shareable; the same ID once
PUBLISHED is, and that transition is an event that can arrive far from any date
written into a file months earlier. `pt_ptfile_embargoed()` answers only the
narrow question the spec field asks. It is not a disclosure gate and should not
be built into one without replacing the model.

## Status

Implemented and tested — **236 checks, clean under AddressSanitizer and
UndefinedBehaviorSanitizer, zero warnings** under `-Wall -Wextra -Wpedantic
-Wshadow -Wconversion -Wsign-conversion -Wcast-qual`:

- `pt_json` — UTF-8 JSON DOM, surrogate pairs, depth-bounded, BOM-tolerant
- `pt_jexpr` — the expression language above
- `pt_sigma` — classification and tally
- `pt_ptfile` — `.ptorrent` parse and validation
- `pt_corpus` — the `[TAG] URL` acquisition list
- `pt_core` — ABI version and error strings

The suite loads real files from the repository on every run: all 21
`.ptorrent` files in `../../ptorrents/`, and all 8 corpus lists — 1,181 URLs,
0 unparseable lines, 34 duplicate URLs.

Not yet implemented — deliberately, since none of it is needed to test the
above and all of it is I/O:

- robots.txt and the per-host queue with one delay clock
- the network gate (pause on signal loss, never abort)
- HTTP adapters and `Range:` resume
- the `.peval` writer
- the daemon socket API (`posix` branch, not here)

## Layout

```
include/ptorrent.h   the entire public surface — 69 exported symbols
src/pt_core.c        version, error strings
src/pt_util.c        string and ISO-date helpers
src/pt_json.c        JSON DOM
src/pt_jexpr.c       expression compiler and evaluator
src/pt_sigma.c       σ-face classification
src/pt_ptfile.c      .ptorrent model
src/pt_corpus.c      [TAG] URL acquisition list
tests/               one binary per module
```

`nm -D libptorrent.so` shows exactly 78 `pt_*` symbols and nothing else;
internals are hidden by `-fvisibility=hidden`.
