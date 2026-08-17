/*
 * ptorrent.h — PTorrent core public API.
 *
 * The whole of PTorrent's functionality is reached through this header.
 * Everything above it is a face; nothing below it knows a face exists.
 *
 * DESIGN CONTRACT — read before adding anything here.
 *
 *   1. C ABI only.  C++ name mangling is not stable across compilers; every
 *      consumer on the target list (C# P/Invoke, Java JNI, Swift, Dart FFI,
 *      Python ctypes) speaks C.  Implementation may use C++ internally, but
 *      it never crosses this boundary.
 *
 *   2. Opaque handles.  Callers hold pointers, never layouts.  Struct layout
 *      changes must not break a compiled face.
 *
 *   3. No struct-by-value across the boundary.  P/Invoke and JNI marshal
 *      by-value aggregates inconsistently.  Flat POD out-parameters only.
 *
 *   4. No callbacks into the caller.  Cross-FFI callbacks require attaching
 *      foreign threads to a managed runtime and are the single largest source
 *      of FFI crashes.  Progress is POLLED.  A curses face wants that anyway.
 *
 *   5. The core never owns the process.  No daemonising, no fork, no signal
 *      handlers, no thread that outlives a call the caller did not make.
 *      iOS forbids background daemons; obeying iOS makes the core embeddable
 *      in an Android Service, a Windows service, a .NET GUI, and a select()
 *      loop without changing a line.
 *
 *   6. No ambient paths.  Every filesystem root is injected by the host.
 *      An iOS app container and an Android scoped-storage sandbox both refuse
 *      hardcoded paths; so does a well-behaved daemon.
 *
 *   7. Cancellation is cooperative and flag-based, never signal-based.
 *
 *   8. UTF-8 everywhere.  Returned strings are NUL-terminated UTF-8 owned by
 *      the handle that produced them and valid until that handle is freed.
 *
 *   9. Threading: handles are not thread-safe and carry no locks.  Distinct
 *      handles may be used concurrently from distinct threads; a single
 *      handle may not.  The core takes no locks of its own because a lock the
 *      caller cannot see is a lock the caller cannot order, and deadlocks
 *      across an FFI boundary are undebuggable from either side.
 *
 *      One exception, stated rather than hidden: pt_corpus_id() draws from a
 *      process-wide counter, so two threads parsing at the same instant must
 *      be serialised by the host.  It is the only mutable global in the core.
 *
 * GENERATION AND LINEAGE — how structure is expressed here.
 *
 * C has no closures and no `nonlocal`.  Where a nested Python scope would
 * capture its parent implicitly, C must name the parent and hold it.  That is
 * a constraint worth leaning into rather than working around, because a
 * relationship you are forced to write down is a relationship you can check.
 *
 *     generation   an index space — one parse, one pt_corpus, one numbering
 *     lineage      which generation an object descends from
 *
 * A pt_cursor holds its corpus: lineage by pointer.  A pt_dedup holds only
 * the corpus *id*: lineage by name, because a modifier outlives traversals
 * and must not keep a parent alive or dangle behind one.  PT_INDEX_MISMATCH
 * is precisely a lineage check — this index descends from a different
 * generation than the one I accumulated in, so I will not resolve it.
 *
 * An implicit closure chain could not have been checked that way; the parent
 * link would have been captured invisibly and the mismatch would have
 * resolved to a confidently wrong record.
 *
 * Licence: see COPYING (GPL-3.0).  This file contains no proprietary
 * mathematics — the sigma-face thresholds published in spec/ptorrent-format-v1.md
 * are the only constants, and they are fixed, published, and not fitted.
 */

#ifndef PTORRENT_H
#define PTORRENT_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ── Export decoration ─────────────────────────────────────────────────────
 * Windows needs explicit export/import; ELF/Mach-O use default visibility
 * with -fvisibility=hidden on the build line.
 */
#if defined(_WIN32) || defined(__CYGWIN__)
#  if defined(PT_BUILDING_SHARED)
#    define PT_API __declspec(dllexport)
#  elif defined(PT_USING_SHARED)
#    define PT_API __declspec(dllimport)
#  else
#    define PT_API
#  endif
#else
#  if defined(PT_BUILDING_SHARED) && (defined(__GNUC__) || defined(__clang__))
#    define PT_API __attribute__((visibility("default")))
#  else
#    define PT_API
#  endif
#endif

/* ── ABI version ───────────────────────────────────────────────────────────
 * MAJOR changes break compiled faces.  MINOR additions do not.
 * A face calls pt_api_version() at load and refuses politely on a MAJOR
 * mismatch rather than crashing — this is what makes "fix the GUI, not the
 * program" true in practice.
 */
#define PT_API_VERSION_MAJOR 0
#define PT_API_VERSION_MINOR 1

/** Packed as (MAJOR << 16) | MINOR. */
PT_API unsigned pt_api_version(void);

/** Human-readable core version, e.g. "0.1.0". Static storage; never freed. */
PT_API const char *pt_version_string(void);

/* ── Errors ────────────────────────────────────────────────────────────────
 * Every fallible entry point returns pt_err.  Values are negative so that
 * functions returning a count can use >= 0 for success where documented.
 */
typedef enum pt_err {
    PT_OK              =  0,
    PT_E_INVAL         = -1,  /* NULL or out-of-range argument              */
    PT_E_NOMEM         = -2,  /* allocation failed                          */
    PT_E_PARSE         = -3,  /* malformed input; see pt_*_error() for text */
    PT_E_IO            = -4,  /* read/write failed                          */
    PT_E_NOTFOUND      = -5,  /* named field / variable absent              */
    PT_E_UNSUPPORTED   = -6,  /* valid but not implemented in this build    */
    PT_E_TYPE          = -7,  /* JSON value present but wrong type          */
    PT_E_TRUNCATED     = -8   /* caller buffer too small; see out length    */
} pt_err;

/** Static English description of a pt_err. Never NULL, never freed. */
PT_API const char *pt_strerror(pt_err e);

/* ══════════════════════════════════════════════════════════════════════════
 * SIGMA-FACE CLASSIFICATION
 *
 * Published in spec/ptorrent-format-v1.md.  The two constants are fixed and
 * are NOT fit parameters:
 *
 *     d*     = 0.246                 (spectral ground state)
 *     Omega  = 0.5671432904097838    (Lambert W(1))
 *
 * Given a dimensionless J-ratio:
 *
 *     J <  d*                     -> INF  (BH interior, compressible limit)
 *     d*   <= J < 1               -> HALF (causality, critical line)
 *     1    <= J < 1/d*            -> ONE  (Yang-Mills, mass assembly)
 *     1/d* <= J < 1/d* + Omega    -> TWO  (gravity, force regime)
 *     J >= 1/d* + Omega           -> INF  (BH interior, force extreme)
 *
 * A non-finite J (NaN or infinity) is UNDEFINED, never INF.  See the note on
 * NaN discipline at pt_jexpr_eval() — conflating "no value" with "extreme
 * value" would silently inflate the INF face, which is the one bucket that
 * has two disjoint physical meanings already.
 * ══════════════════════════════════════════════════════════════════════════ */

#define PT_D_STAR   0.246
#define PT_OMEGA_ZS 0.5671432904097838

typedef enum pt_sigma_face {
    PT_SIGMA_UNDEFINED = 0,  /* J not finite — row contributes to no face */
    PT_SIGMA_HALF      = 1,  /* "½" causality      */
    PT_SIGMA_ONE       = 2,  /* "1" Yang-Mills     */
    PT_SIGMA_TWO       = 3,  /* "2" gravity        */
    PT_SIGMA_INF       = 4   /* "∞" BH interior    */
} pt_sigma_face;

/** Classify a J-ratio. Total function: every double maps to a face. */
PT_API pt_sigma_face pt_sigma_classify(double j);

/** Canonical UTF-8 label: "½", "1", "2", "∞", or "undefined". */
PT_API const char *pt_sigma_label(pt_sigma_face f);

/** Canonical semantic name: "causality", "Yang-Mills", "gravity",
 *  "BH interior", or "undefined". */
PT_API const char *pt_sigma_semantic(pt_sigma_face f);

/* ── Face tally ────────────────────────────────────────────────────────────
 * A flat POD accumulator.  Passed by pointer, never by value.  Callers may
 * allocate it on their own stack in any language that can express five
 * 64-bit integers contiguously.
 */
typedef struct pt_sigma_tally {
    unsigned long long undefined;
    unsigned long long half;
    unsigned long long one;
    unsigned long long two;
    unsigned long long inf;
} pt_sigma_tally;

PT_API void pt_sigma_tally_reset(pt_sigma_tally *t);
PT_API void pt_sigma_tally_add(pt_sigma_tally *t, pt_sigma_face f);
/** Rows with a finite J — the denominator for fractions. */
PT_API unsigned long long pt_sigma_tally_finite(const pt_sigma_tally *t);
/** Every row offered, finite or not. */
PT_API unsigned long long pt_sigma_tally_total(const pt_sigma_tally *t);

/* ══════════════════════════════════════════════════════════════════════════
 * J-EXPRESSION — evaluation as DATA, not as code
 *
 * A researcher's methodology travels as an arithmetic expression over column
 * names, never as a binary.  This is what makes it safe to accept another
 * researcher's evaluation over the network and run it: a whitelisted
 * expression is sandboxable on every platform, a downloaded shared object is
 * sandboxable on none, and iOS forbids the latter outright (App Store 2.5.2).
 *
 * Grammar (spec/ptorrent-format-v1.md, "j_expr Expression Syntax"):
 *
 *     expr    := term (('+' | '-') term)*
 *     term    := unary (('*' | '/') unary)*
 *     unary   := ('-' | '+') unary | power
 *     power   := primary ('**' unary)?          right-associative
 *     primary := NUMBER | IDENT | CALL | '(' expr ')'
 *     CALL    := IDENT '(' expr (',' expr)* ')'
 *
 * Precedence follows Python, because the reference implementation and every
 * published example are Python: -2**2 is -(2**2) = -4, and 2**-1 = 0.5.
 *
 * Functions: sqrt abs log log10 exp (1 argument), max min (2 arguments).
 * Constants: pi e.
 * Anything else is a parse error — there is no escape hatch by design.
 * ══════════════════════════════════════════════════════════════════════════ */

typedef struct pt_jexpr     pt_jexpr;      /* compiled expression   */
typedef struct pt_bindings  pt_bindings;   /* column name -> double */

/**
 * Compile @p src.  On PT_E_PARSE the handle is still returned via @p out set
 * to NULL, and @p errbuf (if non-NULL) receives a NUL-terminated message with
 * a byte offset, e.g. "col 7: unknown function 'sine'".
 */
PT_API pt_err pt_jexpr_compile(const char *src,
                               pt_jexpr **out,
                               char *errbuf, size_t errbuf_len);

PT_API void pt_jexpr_free(pt_jexpr *e);

/** Number of distinct identifiers referenced (excludes pi and e). */
PT_API int pt_jexpr_var_count(const pt_jexpr *e);

/** Name of referenced variable @p i, or NULL. Owned by @p e. */
PT_API const char *pt_jexpr_var_at(const pt_jexpr *e, int i);

/* Bindings — one per row, reused across rows to avoid per-row allocation. */
PT_API pt_bindings *pt_bindings_new(void);
PT_API void         pt_bindings_free(pt_bindings *b);
/** Remove all bindings but keep the allocated capacity. */
PT_API void         pt_bindings_clear(pt_bindings *b);
/** Bind (or rebind) @p name to @p value. */
PT_API pt_err       pt_bindings_set(pt_bindings *b, const char *name, double value);
/** Bind @p name as SQL NULL / missing. Any expression touching it is NaN. */
PT_API pt_err       pt_bindings_set_null(pt_bindings *b, const char *name);

/**
 * Evaluate @p e against @p b, writing the result to @p out.
 *
 * NaN DISCIPLINE — a deliberate decision, not an accident:
 *
 *   Missing/NULL column, division by zero, sqrt of a negative, log of a
 *   non-positive, and overflow to infinity all produce NaN, and NaN
 *   propagates through every operator to the result.
 *
 *   Division by zero yields NaN rather than infinity SPECIFICALLY so that it
 *   cannot be classified.  An infinite J would land in PT_SIGMA_INF and be
 *   indistinguishable from a genuine force-extreme measurement, quietly
 *   inflating one face with rows that carry no measurement at all.  A row
 *   that could not be measured must be counted as unmeasured.
 *
 * Returns PT_OK even when the result is NaN — NaN is a legitimate outcome,
 * not a failure.  PT_E_NOTFOUND is returned only if a referenced variable was
 * never bound at all (as opposed to bound-as-NULL), which is a job
 * configuration error rather than a data condition.
 */
PT_API pt_err pt_jexpr_eval(const pt_jexpr *e, const pt_bindings *b, double *out);

/** Convenience: compile, evaluate, classify, free. For tests and one-shots. */
PT_API pt_err pt_jexpr_eval_once(const char *src, const pt_bindings *b, double *out);

/* ══════════════════════════════════════════════════════════════════════════
 * JSON
 *
 * A minimal, allocation-light, dependency-free DOM parser.  It exists because
 * the core must parse .ptorrent files on a platform where adding a dependency
 * is a port, and because one JSON implementation everywhere is one set of
 * JSON bugs everywhere.
 * ══════════════════════════════════════════════════════════════════════════ */

typedef struct pt_json pt_json;

typedef enum pt_json_type {
    PT_JSON_NULL   = 0,
    PT_JSON_BOOL   = 1,
    PT_JSON_NUMBER = 2,
    PT_JSON_STRING = 3,
    PT_JSON_ARRAY  = 4,
    PT_JSON_OBJECT = 5
} pt_json_type;

/**
 * Parse @p len bytes of UTF-8 JSON.  @p text need not be NUL-terminated and
 * is not retained — the DOM owns copies.
 * On failure @p errbuf receives "line L col C: message".
 */
PT_API pt_err pt_json_parse(const char *text, size_t len,
                            pt_json **out,
                            char *errbuf, size_t errbuf_len);

PT_API void         pt_json_free(pt_json *j);
PT_API pt_json_type pt_json_type_of(const pt_json *j);

/** Object member by key, or NULL. Borrowed. */
PT_API const pt_json *pt_json_get(const pt_json *obj, const char *key);
/** Array/object element count; 0 for scalars. */
PT_API int            pt_json_count(const pt_json *j);
/** Array element by index, or NULL. Borrowed. */
PT_API const pt_json *pt_json_at(const pt_json *arr, int i);
/** Object key by index, or NULL. Borrowed. */
PT_API const char    *pt_json_key_at(const pt_json *obj, int i);

/* Scalar readers. Each returns @p fallback when the node is absent or of the
 * wrong type, so a caller may read an optional field without branching. */
PT_API const char *pt_json_string(const pt_json *j, const char *fallback);
PT_API double      pt_json_number(const pt_json *j, double fallback);
PT_API int         pt_json_bool(const pt_json *j, int fallback);

/* ══════════════════════════════════════════════════════════════════════════
 * .ptorrent FILE
 *
 * spec/ptorrent-format-v1.md is authoritative.  Unknown fields are preserved
 * in the raw JSON (pt_ptfile_json) rather than discarded, so a core built
 * against v1.1 can carry a v1.2 file through a distribution hop intact.
 * ══════════════════════════════════════════════════════════════════════════ */

typedef struct pt_ptfile pt_ptfile;

typedef enum pt_job_type {
    PT_JOB_UNKNOWN    = 0,
    PT_JOB_CORPUS     = 1,
    PT_JOB_DATASET    = 2,
    PT_JOB_TRANSFER   = 3,
    PT_JOB_PHONEBOOK  = 4,
    PT_JOB_EVALUATION = 5
} pt_job_type;

PT_API pt_err pt_ptfile_parse(const char *text, size_t len,
                              pt_ptfile **out,
                              char *errbuf, size_t errbuf_len);

/**
 * Read and parse a file.  @p path is supplied by the host — the core never
 * composes a path from an ambient root (contract rule 6).
 */
PT_API pt_err pt_ptfile_load(const char *path,
                             pt_ptfile **out,
                             char *errbuf, size_t errbuf_len);

PT_API void pt_ptfile_free(pt_ptfile *p);

/** The underlying DOM, including fields this core does not model. Borrowed. */
PT_API const pt_json *pt_ptfile_json(const pt_ptfile *p);

/* Root fields. Strings are borrowed and valid until pt_ptfile_free(). */
PT_API const char  *pt_ptfile_version(const pt_ptfile *p);
PT_API pt_job_type  pt_ptfile_type(const pt_ptfile *p);
PT_API const char  *pt_ptfile_type_string(const pt_ptfile *p);
PT_API const char  *pt_ptfile_name(const pt_ptfile *p);
PT_API const char  *pt_ptfile_bin(const pt_ptfile *p);
PT_API const char  *pt_ptfile_description(const pt_ptfile *p);
PT_API const char  *pt_ptfile_color(const pt_ptfile *p);
PT_API const char  *pt_ptfile_output(const pt_ptfile *p);
PT_API const char  *pt_ptfile_requires_bin(const pt_ptfile *p);
PT_API const char  *pt_ptfile_user_agent(const pt_ptfile *p);
PT_API int          pt_ptfile_checkpoint_every(const pt_ptfile *p);

PT_API int          pt_ptfile_tag_count(const pt_ptfile *p);
PT_API const char  *pt_ptfile_tag_at(const pt_ptfile *p, int i);

PT_API int          pt_ptfile_url_count(const pt_ptfile *p);
PT_API const char  *pt_ptfile_url_at(const pt_ptfile *p, int i);
PT_API const char  *pt_ptfile_url_tag_at(const pt_ptfile *p, int i);

/* ── security block ────────────────────────────────────────────────────────
 * Level 0 public, 1 sensitive, 2 restricted, 3 dual-use.
 *
 * STATUS: parked, and unexercised. No .ptorrent file in the repository
 * carries a `security` block or an `embargo_until`. These accessors exist
 * because the spec defines the fields, and they cost nothing to parse; they
 * are not a disclosure system and should not be built out into one without
 * revisiting the model below.
 *
 * The date model is known to be wrong for the case it was aimed at.
 * Coordinated disclosure does not gate on a calendar date — it gates on a
 * record STATE. A CVE ID that is RESERVED (historically "CAN-", a prefix
 * retired in 2005) is not shareable; the same ID once PUBLISHED is. The
 * transition is an event, not a deadline, and it can arrive earlier or far
 * later than any date written into a file months beforehand.
 *
 * So pt_ptfile_embargoed() answers only the narrow question the spec field
 * asks, and answers it fail-closed. It is not a disclosure gate.
 */
PT_API int         pt_ptfile_security_level(const pt_ptfile *p);
PT_API const char *pt_ptfile_security_classification(const pt_ptfile *p);
PT_API const char *pt_ptfile_security_warning(const pt_ptfile *p);
PT_API const char *pt_ptfile_security_embargo_until(const pt_ptfile *p);
PT_API int         pt_ptfile_security_acknowledge_required(const pt_ptfile *p);

/**
 * Embargo test.  @p today_iso is "YYYY-MM-DD" supplied by the host — the core
 * does not read the clock, because a testable core cannot depend on today and
 * a sandboxed one may not agree with the server about the date anyway.
 * Returns 1 if seeding is blocked, 0 if permitted.
 */
PT_API int pt_ptfile_embargoed(const pt_ptfile *p, const char *today_iso);

/* ── evaluation block ──────────────────────────────────────────────────────
 * The J-ratio extraction order is fixed by the spec:
 *   1. j_col   2. j_num_col/j_den_col   3. j_expr   4. fn   5. adapter value
 */
typedef enum pt_j_method {
    PT_J_NONE       = 0,
    PT_J_COL        = 1,
    PT_J_NUM_DEN    = 2,
    PT_J_EXPR       = 3,
    PT_J_FN         = 4
} pt_j_method;

PT_API int          pt_ptfile_has_evaluation(const pt_ptfile *p);
PT_API pt_j_method  pt_ptfile_j_method(const pt_ptfile *p);
PT_API const char  *pt_ptfile_j_expr(const pt_ptfile *p);
PT_API const char  *pt_ptfile_j_col(const pt_ptfile *p);
PT_API const char  *pt_ptfile_j_num_col(const pt_ptfile *p);
PT_API const char  *pt_ptfile_j_den_col(const pt_ptfile *p);
PT_API const char  *pt_ptfile_j_fn(const pt_ptfile *p);
PT_API const char  *pt_ptfile_methodology(const pt_ptfile *p);
PT_API const char  *pt_ptfile_prediction(const pt_ptfile *p);
PT_API int          pt_ptfile_j_expr_col_count(const pt_ptfile *p);
PT_API const char  *pt_ptfile_j_expr_col_at(const pt_ptfile *p, int i);

/**
 * Columns this job must request from the source.
 *
 * Prefers the declared j_expr_cols; falls back to the identifiers the
 * compiled j_expr actually references when the declaration is absent or
 * disagrees.  Minimum column movement is the entire economic argument for
 * in-situ evaluation, so this is a core concern and not an adapter's.
 *
 * Writes at most @p max pointers into @p out and returns the count, or a
 * negative pt_err.  Strings are borrowed from @p p.
 */
PT_API int pt_ptfile_required_columns(const pt_ptfile *p,
                                      const char **out, int max);

/* ══════════════════════════════════════════════════════════════════════════
 * CORPUS URL LIST
 *
 * The `txt` companion file named by a corpus .ptorrent. Every corpus job in
 * the repository uses this path — none embed a `urls` array — so this is the
 * real shape of an acquisition job, not the documented one.
 *
 * Format is line-oriented:
 *
 *     # comments and section headers are ignored
 *     [TAG] https://example.org/page
 *
 * A tag is [A-Za-z0-9_]+, deliberately wider than the Python reference's
 * [A-Z]+. That regex silently drops any line whose tag carries a digit or an
 * underscore — DARK_MATTER would vanish without a word. No current file trips
 * it, which is exactly why it would go unnoticed when one eventually does.
 *
 * Lines that are neither blank, comment, nor a well-formed entry are counted
 * rather than discarded. A URL lost to a typo is a hole in a corpus that
 * nothing downstream can detect, and the Python's silent skip is why a list
 * can quietly shrink between runs.
 * ══════════════════════════════════════════════════════════════════════════ */

typedef struct pt_corpus pt_corpus;

/* ── Item status — why nothing is ever dropped ─────────────────────────────
 *
 * Traversal does not decide what to keep. Every line of the source becomes a
 * record carrying a status and its original line number, and the caller walks
 * records. There is no code path that discards an input, so a line cannot go
 * missing — not by a regex that failed to match, not by a `continue`, not by
 * an exception swallowed three frames up.
 *
 * Counting skips is not the same as not skipping. A tally tells you that four
 * lines were lost; it does not tell you which, or let you print them. A
 * record does both, and it costs one enum.
 *
 * This is the shape every sequence in the core should take — corpus lines
 * now, dataset rows under in-situ evaluation next, where a row that fails to
 * evaluate is exactly the same problem wearing different clothes.
 */
typedef enum pt_item_status {
    PT_ITEM_OK        = 0,  /* parsed; usable                                */
    PT_ITEM_IGNORED   = 1,  /* comment or blank — not data by construction   */
    PT_ITEM_MALFORMED = 2   /* data-shaped and unparseable — a hole          */
} pt_item_status;

/*
 * Note what is NOT in that enum: "duplicate".
 *
 * Duplication is not a property of a line. It is a relation across the whole
 * set, and it depends on a policy — exact string match today, canonicalised
 * URL or query-stripped match tomorrow. Deciding it during the parse would
 * make the traversal into a modifier, and would weld one dedup policy into
 * the reader forever. It lives in pt_dedup, below, as a separate pass.
 */

/** Static English description of a status. Never NULL. */
PT_API const char *pt_item_status_string(pt_item_status s);

PT_API pt_err pt_corpus_parse(const char *text, size_t len,
                              pt_corpus **out,
                              char *errbuf, size_t errbuf_len);

/**
 * Read a corpus list from @p path, supplied by the host.
 *
 * Unlike the Python reference, an unreadable file is an error rather than an
 * empty list. A corpus job that silently seeds nothing and reports success is
 * the failure this whole layer exists to stop.
 */
PT_API pt_err pt_corpus_load(const char *path,
                             pt_corpus **out,
                             char *errbuf, size_t errbuf_len);

PT_API void pt_corpus_free(pt_corpus *c);

/** Total records — one per line of the source, always. */
PT_API int pt_corpus_count(const pt_corpus *c);

/**
 * Identity of this parsed instance — its index space.
 *
 * Distinct for every successful parse, so re-reading a source that has gained
 * or lost lines produces a new space. A modifier holding indices from the old
 * one can then be told, rather than left pointing confidently at the wrong
 * record. See the invariant note at pt_dedup.
 */
PT_API unsigned long pt_corpus_id(const pt_corpus *c);

PT_API pt_item_status pt_corpus_status_at(const pt_corpus *c, int i);
/** 1-based line number in the source file. */
PT_API long           pt_corpus_line_at(const pt_corpus *c, int i);
/** The original line, always present — including for malformed records. */
PT_API const char    *pt_corpus_raw_at(const pt_corpus *c, int i);
/** NULL unless the record parsed. */
PT_API const char    *pt_corpus_url_at(const pt_corpus *c, int i);
PT_API const char    *pt_corpus_tag_at(const pt_corpus *c, int i);

/** How many records carry @p s. */
PT_API int pt_corpus_count_status(const pt_corpus *c, pt_item_status s);

/* ── Cursor ────────────────────────────────────────────────────────────────
 * Traversal is its own object, not a loop inside the parser. The container
 * holds records; the cursor holds a position and reports what it is standing
 * on. Nothing is filtered on the way past — a caller that wants only usable
 * records tests the status itself, in the open, where the decision is visible.
 */
typedef struct pt_cursor pt_cursor;

/*
 * LIFETIME — a pointer carries access, never ownership.
 *
 * A cursor holds a pointer to its corpus. That pointer reaches the parent
 * from anywhere the cursor travels, but it does NOT keep the parent alive:
 * scope and lifetime are separate axes in C, and only the first is what a
 * pointer crosses.
 *
 *     pt_corpus_free(c);
 *     pt_cursor_next(cur);      // use-after-free. Nothing here can catch it.
 *
 * So: A CURSOR MUST NOT OUTLIVE ITS CORPUS. Free cursors first.
 *
 * A pt_dedup deliberately does not hold that pointer. It keeps the corpus id
 * instead, which is a value — it cannot dangle, it can be compared long after
 * the corpus is gone, and the comparison simply stops matching. That is the
 * whole reason lineage is by name there and by pointer here: a modifier
 * outlives traversals, and anything that outlives its parent must refer to it
 * by something that survives the parent's death.
 */

PT_API pt_cursor *pt_corpus_cursor(const pt_corpus *c);
PT_API void       pt_cursor_free(pt_cursor *cur);

/** Advance. Returns 1 while positioned on a record, 0 at the end. */
PT_API int pt_cursor_next(pt_cursor *cur);
/** Return to before the first record. */
PT_API void pt_cursor_reset(pt_cursor *cur);

PT_API int             pt_cursor_index(const pt_cursor *cur);
/** The index space this cursor walks — pt_corpus_id() of its corpus. */
PT_API unsigned long   pt_cursor_corpus_id(const pt_cursor *cur);
PT_API pt_item_status  pt_cursor_status(const pt_cursor *cur);
PT_API long            pt_cursor_line(const pt_cursor *cur);
PT_API const char     *pt_cursor_raw(const pt_cursor *cur);
PT_API const char     *pt_cursor_url(const pt_cursor *cur);
PT_API const char     *pt_cursor_tag(const pt_cursor *cur);

/* ── Dedup — a modifier, deliberately not the cursor ───────────────────────
 *
 * Iterating a sequence and analysing it are different jobs and must be
 * different objects. The cursor reports what it is standing on and changes
 * nothing; pt_dedup accumulates state across a traversal and answers a
 * question no individual record can.
 *
 * Separating them does not isolate them — it is what lets them SHARE ONE
 * INDEX SPACE AND AGREE ON IT. Because neither renumbers unilaterally, the
 * modifier can speak in the same indices the cursor hands out, and both mean
 * the same record by the same number. So pt_dedup_observe() does not answer
 * "yes, a repeat"; it answers "a repeat of record 12", and the caller can go
 * straight back to record 12 through the cursor or the corpus and find the
 * line it means.
 *
 * THE INVARIANT, stated precisely, because it is easy to overstate:
 *
 *     For every index i, the cursor and the modifier denote the same record.
 *
 * It is a relation BETWEEN THE TWO OBJECTS, and it holds across every state
 * of a traversal. It is not a claim that the list is fixed — the list is
 * variable, sources change, and a re-read legitimately renumbers everything.
 * The invariant is scoped to one index space, identified by pt_corpus_id().
 *
 * And an invariant that is only written down is a hope, so it is checked:
 * a modifier records the space it was first used with, and reports
 * PT_INDEX_MISMATCH rather than resolving an index against a list that has
 * been re-read underneath it.
 *
 *     pt_cursor *cur = pt_corpus_cursor(c);
 *     pt_dedup  *d   = pt_dedup_new();
 *     while (pt_cursor_next(cur)) {
 *         if (pt_cursor_status(cur) != PT_ITEM_OK) continue;
 *         int first = pt_dedup_observe(d, pt_cursor_url(cur),
 *                                         pt_cursor_index(cur));
 *         if (first >= 0) {
 *             report("line %ld repeats line %ld",
 *                    pt_cursor_line(cur), pt_corpus_line_at(c, first));
 *             continue;
 *         }
 *         fetch(pt_cursor_url(cur));
 *     }
 *
 * Both `continue`s are in the caller's code, in the open, where a reader can
 * see what is being passed over and why. Keeping the policy out here is also
 * what lets it change — key on the raw URL now, on a canonicalised one later
 * — without touching the reader.
 */
typedef struct pt_dedup pt_dedup;

PT_API pt_dedup *pt_dedup_new(void);
PT_API void      pt_dedup_free(pt_dedup *d);
PT_API void      pt_dedup_reset(pt_dedup *d);

/** Returned by the observe calls when @p key has not been seen before. */
#define PT_INDEX_NONE     (-1)
/**
 * Returned when the modifier is handed an index from a different space than
 * the one it has been accumulating — the list was re-read underneath it, and
 * its stored indices no longer denote what they did. A silent answer here
 * would be a confidently wrong record number.
 */
#define PT_INDEX_MISMATCH (-2)

/**
 * Observe @p key at the cursor's current position.
 *
 * This is the form to prefer: index and index-space both come from the
 * cursor, so the two objects cannot disagree about what an index means —
 * the invariant is structural rather than remembered.
 *
 * Returns the index at which @p key was first observed, PT_INDEX_NONE if this
 * is its first observation, or PT_INDEX_MISMATCH. A returned index is in the
 * cursor's space and can go straight to pt_corpus_line_at().
 */
PT_API int pt_dedup_observe_at(pt_dedup *d, const pt_cursor *cur, const char *key);

/**
 * Observe @p key at @p index in index space @p space_id.
 *
 * The open-coded form, for sequences that are not a corpus — dataset rows
 * under in-situ evaluation will use it. Pass the space id that identifies the
 * sequence being walked; pass 0 only when there is genuinely one unnamed
 * space, which disables the mismatch check.
 */
PT_API int pt_dedup_observe(pt_dedup *d, unsigned long space_id,
                            const char *key, int index);

/** The index space this modifier has been accumulating in, or 0 if unused. */
PT_API unsigned long pt_dedup_space(const pt_dedup *d);

/** Distinct keys recorded so far. */
PT_API int pt_dedup_unique(const pt_dedup *d);
/** Observations that repeated an earlier key. */
PT_API int pt_dedup_repeats(const pt_dedup *d);

/**
 * Ingestion weight for @p tag per the spec: primary_weight when the tag
 * appears in the job's primary_tags, context_weight otherwise.
 *
 * Kept separate from parsing on purpose. Weighting is what a consumer does
 * with a corpus; acquisition only needs the tag recorded as provenance.
 */
PT_API double pt_corpus_weight_for_tag(const pt_ptfile *p, const char *tag);

#ifdef __cplusplus
}  /* extern "C" */
#endif

#endif /* PTORRENT_H */
