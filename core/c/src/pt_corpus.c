/*
 * pt_corpus.c — the [TAG] URL list, and the traversal discipline for it.
 *
 * This is the acquisition job as it actually exists. Every corpus file in the
 * repository names a `txt` companion; not one embeds a `urls` array.
 *
 * THREE OBJECTS, THREE JOBS — the reason this file is shaped the way it is:
 *
 *   pt_corpus   holds one record per line of the source. It never drops one.
 *   pt_cursor   walks records and reports. It modifies nothing and filters
 *               nothing.
 *   pt_dedup    accumulates state across a traversal and answers a question
 *               no single record can. It is a modifier, so it is not the
 *               cursor.
 *
 * The payoff of keeping the reader and the modifier apart is that THE INDEX
 * IS TRUSTABLE. Nothing renumbers it, because nothing compacts, because the
 * traversal is not permitted to remove anything. A reference to record 47
 * denotes record 47 — in a second pass, in a status report, in a provenance
 * record, before and after a modifier has run. A modifier that wants
 * per-item results keys them by that index instead of building a filtered
 * copy with an index of its own.
 *
 * Trustable is not the same as invariant, and the difference matters. The
 * index is not a permanent name for a line: re-read a source that has gained
 * or lost lines and index 47 legitimately means something new. That is
 * honest change, and corpus sources change constantly. What is guaranteed is
 * that no traversal and no modifier will shift the numbering underneath a
 * caller who is holding one — the index means what it says for the life of
 * the object it came from.
 *
 * Cross-time identity is a different problem and needs a different key: the
 * URL, or a hash of the content. Do not use an index for it.
 *
 * A filtering iterator forfeits all of this: index 47 means one thing on the
 * first pass and another on the second within a single unchanged file, and
 * no report can be trusted to refer to the same line twice.
 *
 * Three differences from the Python reference, each a silent failure made
 * loud:
 *
 *   1. An unreadable list is an error, not an empty list. `except OSError:
 *      pass` is how a job seeds nothing overnight and reports success in the
 *      morning.
 *
 *   2. Tags may contain digits and underscores. The reference regex is
 *      ^\[([A-Z]+)\]\s+(https?://\S+) — DARK_MATTER does not match it and the
 *      line vanishes without a word.
 *
 *   3. A line that fails to parse becomes a MALFORMED record holding its
 *      original text and line number, not a `continue`. It can be printed.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pt_internal.h"

/* Real corpus lists top out at 32 KB. This ceiling is generous and still
 * refuses to load something that is not a URL list. */
#define PT_CORPUS_MAX_BYTES (64u * 1024u * 1024u)

typedef struct {
    char          *raw;     /* the original line, always present */
    char          *tag;     /* NULL unless OK */
    char          *url;     /* NULL unless OK */
    long           line;    /* 1-based */
    pt_item_status status;
} record;

struct pt_corpus {
    record       *items;
    int           count, cap;
    unsigned long id;        /* this instance's index space */
};

/*
 * Index-space identity — the generation counter.
 *
 * A monotonic counter rather than the object address: addresses are reused
 * after free, so a modifier holding indices into a freed corpus would match a
 * fresh one at the same address and answer confidently about the wrong list.
 * Counting up never collides within a process lifetime.
 *
 * THIS IS THE ONLY MUTABLE GLOBAL IN THE CORE, and it is declared as such in
 * ptorrent.h rather than left for someone to discover. Identity that must be
 * unique across every object in a process is genuinely process-scoped, so
 * threading it through every call would move the state without removing it.
 * Not atomic: a host parsing from several threads at once serialises these
 * calls, per contract rule 9.
 */
static unsigned long g_next_corpus_id = 1;

const char *pt_item_status_string(pt_item_status s)
{
    switch (s) {
    case PT_ITEM_OK:        return "ok";
    case PT_ITEM_IGNORED:   return "ignored";
    case PT_ITEM_MALFORMED: return "malformed";
    }
    return "unknown";
}

/* ── records ───────────────────────────────────────────────────────────── */

static int push(struct pt_corpus *c, char *raw, char *tag, char *url,
                long line, pt_item_status st)
{
    if (c->count == c->cap) {
        int     ncap = c->cap ? c->cap * 2 : 64;
        record *n    = (record *)realloc(c->items, (size_t)ncap * sizeof(*n));
        if (!n) return 0;
        c->items = n;
        c->cap   = ncap;
    }
    c->items[c->count].raw    = raw;
    c->items[c->count].tag    = tag;
    c->items[c->count].url    = url;
    c->items[c->count].line   = line;
    c->items[c->count].status = st;
    c->count++;
    return 1;
}

static int is_tag_char(char ch)
{
    return (ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z')
        || (ch >= '0' && ch <= '9') || ch == '_';
}

/*
 * Classify one line. Only intrinsic properties are decided here — what the
 * line *is*, judged from the line alone. Anything relational (duplication,
 * reachability, whether a fetch later succeeded) belongs to a modifier.
 */
static pt_item_status classify(const char *s, const char *e,
                               const char **tag_s, const char **tag_e,
                               const char **url_s, const char **url_e)
{
    while (s < e && (*s == ' ' || *s == '\t')) s++;
    while (e > s && (e[-1] == ' ' || e[-1] == '\t' || e[-1] == '\r')) e--;

    if (s == e)    return PT_ITEM_IGNORED;   /* blank   */
    if (*s == '#') return PT_ITEM_IGNORED;   /* comment */

    if (*s != '[') return PT_ITEM_MALFORMED;

    *tag_s = ++s;
    while (s < e && is_tag_char(*s)) s++;
    *tag_e = s;

    if (*tag_e == *tag_s || s >= e || *s != ']') return PT_ITEM_MALFORMED;
    s++;

    if (s >= e || (*s != ' ' && *s != '\t')) return PT_ITEM_MALFORMED;
    while (s < e && (*s == ' ' || *s == '\t')) s++;

    /* A corpus list is fetched over HTTP. Any other scheme is a mistake worth
     * surfacing rather than a source worth attempting. */
    if (!((e - s) > 7 && memcmp(s, "http://", 7) == 0) &&
        !((e - s) > 8 && memcmp(s, "https://", 8) == 0)) {
        return PT_ITEM_MALFORMED;
    }

    *url_s = s;
    while (s < e && *s != ' ' && *s != '\t') s++;
    *url_e = s;
    return PT_ITEM_OK;
}

/* ── parse / load / free ───────────────────────────────────────────────── */

pt_err pt_corpus_parse(const char *text, size_t len, pt_corpus **out,
                       char *errbuf, size_t errbuf_len)
{
    struct pt_corpus *c;
    const char       *p, *end;
    long              lineno = 0;
    int               n_ok   = 0;

    if (errbuf && errbuf_len) errbuf[0] = '\0';
    if (!text || !out) return PT_E_INVAL;
    *out = NULL;

    c = (struct pt_corpus *)calloc(1, sizeof(*c));
    if (!c) return PT_E_NOMEM;

    p   = text;
    end = text + len;

    if (len >= 3 && (unsigned char)p[0] == 0xEF
                 && (unsigned char)p[1] == 0xBB
                 && (unsigned char)p[2] == 0xBF) {
        p += 3;
    }

    while (p < end) {
        const char    *nl = (const char *)memchr(p, '\n', (size_t)(end - p));
        const char    *le = nl ? nl : end;
        const char    *ts = NULL, *te = NULL, *us = NULL, *ue = NULL;
        pt_item_status st;
        char          *raw, *tag = NULL, *url = NULL;
        const char    *rawe = le;

        lineno++;
        st = classify(p, le, &ts, &te, &us, &ue);

        if (rawe > p && rawe[-1] == '\r') rawe--;
        raw = pt_strndup(p, (size_t)(rawe - p));
        if (!raw) { pt_corpus_free(c); return PT_E_NOMEM; }

        if (st == PT_ITEM_OK) {
            tag = pt_strndup(ts, (size_t)(te - ts));
            url = pt_strndup(us, (size_t)(ue - us));
            if (!tag || !url) {
                free(raw); free(tag); free(url);
                pt_corpus_free(c);
                return PT_E_NOMEM;
            }
            n_ok++;
        }

        if (!push(c, raw, tag, url, lineno, st)) {
            free(raw); free(tag); free(url);
            pt_corpus_free(c);
            return PT_E_NOMEM;
        }

        if (!nl) break;
        p = nl + 1;
    }

    if (n_ok == 0) {
        pt_corpus_free(c);
        pt_seterr(errbuf, errbuf_len,
                  "corpus list contains no [TAG] URL entries");
        return PT_E_PARSE;
    }

    c->id = g_next_corpus_id++;
    *out  = c;
    return PT_OK;
}

pt_err pt_corpus_load(const char *path, pt_corpus **out,
                      char *errbuf, size_t errbuf_len)
{
    FILE   *f;
    char   *buf;
    long    sz;
    size_t  n;
    pt_err  rc;

    if (errbuf && errbuf_len) errbuf[0] = '\0';
    if (!path || !out) return PT_E_INVAL;
    *out = NULL;

    f = fopen(path, "rb");
    if (!f) {
        pt_seterr(errbuf, errbuf_len, "cannot open corpus list '%s'", path);
        return PT_E_IO;
    }

    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return PT_E_IO; }
    sz = ftell(f);
    if (sz < 0) { fclose(f); return PT_E_IO; }
    if (fseek(f, 0, SEEK_SET) != 0) { fclose(f); return PT_E_IO; }

    if ((unsigned long)sz > PT_CORPUS_MAX_BYTES) {
        fclose(f);
        pt_seterr(errbuf, errbuf_len, "'%s' is %ld bytes; limit is %u",
                  path, sz, PT_CORPUS_MAX_BYTES);
        return PT_E_IO;
    }

    buf = (char *)malloc((size_t)sz + 1);
    if (!buf) { fclose(f); return PT_E_NOMEM; }

    n = fread(buf, 1, (size_t)sz, f);
    fclose(f);
    buf[n] = '\0';

    rc = pt_corpus_parse(buf, n, out, errbuf, errbuf_len);
    free(buf);
    return rc;
}

void pt_corpus_free(pt_corpus *c)
{
    int i;
    if (!c) return;
    for (i = 0; i < c->count; i++) {
        free(c->items[i].raw);
        free(c->items[i].tag);
        free(c->items[i].url);
    }
    free(c->items);
    free(c);
}

/* ── record accessors ──────────────────────────────────────────────────── */

int           pt_corpus_count(const pt_corpus *c) { return c ? c->count : 0; }
unsigned long pt_corpus_id(const pt_corpus *c)    { return c ? c->id    : 0; }

static const record *rec(const pt_corpus *c, int i)
{
    if (!c || i < 0 || i >= c->count) return NULL;
    return &c->items[i];
}

pt_item_status pt_corpus_status_at(const pt_corpus *c, int i)
{
    const record *r = rec(c, i);
    return r ? r->status : PT_ITEM_MALFORMED;
}

long pt_corpus_line_at(const pt_corpus *c, int i)
{
    const record *r = rec(c, i);
    return r ? r->line : 0;
}

const char *pt_corpus_raw_at(const pt_corpus *c, int i)
{
    const record *r = rec(c, i);
    return r ? r->raw : NULL;
}

const char *pt_corpus_url_at(const pt_corpus *c, int i)
{
    const record *r = rec(c, i);
    return r ? r->url : NULL;
}

const char *pt_corpus_tag_at(const pt_corpus *c, int i)
{
    const record *r = rec(c, i);
    return r ? r->tag : NULL;
}

int pt_corpus_count_status(const pt_corpus *c, pt_item_status s)
{
    int i, n = 0;
    if (!c) return 0;
    for (i = 0; i < c->count; i++) if (c->items[i].status == s) n++;
    return n;
}

/* ── cursor: position only, no opinion ─────────────────────────────────── */

struct pt_cursor {
    const pt_corpus *c;
    int              i;      /* -1 before the first record */
};

pt_cursor *pt_corpus_cursor(const pt_corpus *c)
{
    struct pt_cursor *cur;
    if (!c) return NULL;
    cur = (struct pt_cursor *)calloc(1, sizeof(*cur));
    if (!cur) return NULL;
    cur->c = c;
    cur->i = -1;
    return cur;
}

void pt_cursor_free(pt_cursor *cur) { free(cur); }

/* Advances by exactly one record. It does not skip IGNORED or MALFORMED
 * records: a traversal that decides what the caller may see is a traversal
 * that can lose things, and the index would stop meaning a line. */
int pt_cursor_next(pt_cursor *cur)
{
    if (!cur || !cur->c) return 0;
    if (cur->i + 1 >= cur->c->count) { cur->i = cur->c->count; return 0; }
    cur->i++;
    return 1;
}

void pt_cursor_reset(pt_cursor *cur) { if (cur) cur->i = -1; }

int pt_cursor_index(const pt_cursor *cur) { return cur ? cur->i : -1; }

unsigned long pt_cursor_corpus_id(const pt_cursor *cur)
{
    return cur ? pt_corpus_id(cur->c) : 0;
}

pt_item_status pt_cursor_status(const pt_cursor *cur)
{
    return cur ? pt_corpus_status_at(cur->c, cur->i) : PT_ITEM_MALFORMED;
}

long        pt_cursor_line(const pt_cursor *cur) { return cur ? pt_corpus_line_at(cur->c, cur->i) : 0; }
const char *pt_cursor_raw (const pt_cursor *cur) { return cur ? pt_corpus_raw_at (cur->c, cur->i) : NULL; }
const char *pt_cursor_url (const pt_cursor *cur) { return cur ? pt_corpus_url_at (cur->c, cur->i) : NULL; }
const char *pt_cursor_tag (const pt_cursor *cur) { return cur ? pt_corpus_tag_at (cur->c, cur->i) : NULL; }

/* ── dedup: a modifier, deliberately not the cursor ────────────────────── */

/*
 * Each bucket carries the key AND the index at which it was first observed,
 * so the modifier answers in the same index space the cursor hands out. That
 * shared space is only safe because neither object renumbers: the cursor
 * cannot, since it filters nothing, and the modifier does not, since it owns
 * no records.
 */
struct pt_dedup {
    char        **keys;      /* open-addressed; NULL is empty */
    int          *first;     /* index of first observation, parallel to keys */
    int           nbuckets;
    int           unique;
    int           repeats;
    unsigned long space;     /* index space these indices belong to */
};

static unsigned long fnv1a(const char *s)
{
    unsigned long h = 2166136261UL;
    while (*s) {
        h ^= (unsigned long)(unsigned char)*s++;
        h *= 16777619UL;
    }
    return h;
}

pt_dedup *pt_dedup_new(void)
{
    return (pt_dedup *)calloc(1, sizeof(struct pt_dedup));
}

void pt_dedup_reset(pt_dedup *d)
{
    int i;
    if (!d) return;
    for (i = 0; i < d->nbuckets; i++) {
        free(d->keys[i]);
        d->keys[i]  = NULL;
        d->first[i] = -1;
    }
    d->unique  = 0;
    d->repeats = 0;
    d->space   = 0;      /* free to be bound to a new index space */
}

void pt_dedup_free(pt_dedup *d)
{
    if (!d) return;
    pt_dedup_reset(d);
    free(d->keys);
    free(d->first);
    free(d);
}

static int dedup_grow(struct pt_dedup *d)
{
    int    nb = d->nbuckets ? d->nbuckets * 2 : 256;
    char **nk = (char **)calloc((size_t)nb, sizeof(*nk));
    int   *nf = (int *)malloc((size_t)nb * sizeof(*nf));
    int    i;

    if (!nk || !nf) { free(nk); free(nf); return 0; }
    for (i = 0; i < nb; i++) nf[i] = -1;

    for (i = 0; i < d->nbuckets; i++) {
        unsigned long h;
        int           b;
        if (!d->keys[i]) continue;
        h = fnv1a(d->keys[i]);
        b = (int)(h & (unsigned long)(nb - 1));
        while (nk[b]) b = (b + 1) & (nb - 1);
        nk[b] = d->keys[i];
        nf[b] = d->first[i];
    }

    free(d->keys);
    free(d->first);
    d->keys     = nk;
    d->first    = nf;
    d->nbuckets = nb;
    return 1;
}

int pt_dedup_observe(pt_dedup *d, unsigned long space_id,
                     const char *key, int index)
{
    unsigned long h;
    int           b;

    if (!d || !key) return PT_INDEX_NONE;

    /*
     * The invariant check. The modifier's stored indices only mean anything
     * inside the space they were taken from; answering across spaces would
     * return a confidently wrong record number, which is worse than an error
     * because it looks like an answer.
     */
    if (space_id != 0) {
        if (d->space == 0)            d->space = space_id;
        else if (d->space != space_id) return PT_INDEX_MISMATCH;
    }

    if (d->nbuckets == 0 || d->unique * 2 >= d->nbuckets) {
        if (!dedup_grow(d)) return PT_INDEX_NONE;
    }

    h = fnv1a(key);
    b = (int)(h & (unsigned long)(d->nbuckets - 1));
    while (d->keys[b]) {
        if (strcmp(d->keys[b], key) == 0) {
            d->repeats++;
            return d->first[b];      /* in the caller's own index space */
        }
        b = (b + 1) & (d->nbuckets - 1);
    }

    d->keys[b] = pt_strdup(key);
    if (!d->keys[b]) return PT_INDEX_NONE;
    d->first[b] = index;
    d->unique++;
    return PT_INDEX_NONE;
}

int pt_dedup_observe_at(pt_dedup *d, const pt_cursor *cur, const char *key)
{
    if (!cur) return PT_INDEX_NONE;
    return pt_dedup_observe(d, pt_cursor_corpus_id(cur), key,
                            pt_cursor_index(cur));
}

int           pt_dedup_unique(const pt_dedup *d)  { return d ? d->unique  : 0; }
int           pt_dedup_repeats(const pt_dedup *d) { return d ? d->repeats : 0; }
unsigned long pt_dedup_space(const pt_dedup *d)   { return d ? d->space   : 0; }

/* ── weighting: also a consumer's concern, not the reader's ────────────── */

double pt_corpus_weight_for_tag(const pt_ptfile *p, const char *tag)
{
    const pt_json *root;
    double         primary, context;
    int            i, n;

    if (!p) return 1.0;

    root    = pt_ptfile_json(p);
    primary = pt_json_number(pt_json_get(root, "primary_weight"), 2.0);
    context = pt_json_number(pt_json_get(root, "context_weight"), 1.0);

    if (!tag) return context;

    n = pt_ptfile_tag_count(p);
    for (i = 0; i < n; i++) {
        const char *t = pt_ptfile_tag_at(p, i);
        if (t && strcmp(t, tag) == 0) return primary;
    }
    return context;
}
