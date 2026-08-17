/*
 * pt_ptfile.c — .ptorrent parsing.
 *
 * spec/ptorrent-format-v1.md is authoritative. Two decisions worth stating,
 * because both differ from the Python reference implementation:
 *
 *   1. The full JSON DOM is retained, not just the fields this core models.
 *      A v1.1 core carrying a v1.2 file through a distribution hop must not
 *      silently strip the fields it did not understand.
 *
 *   2. A malformed .ptorrent fails loudly. The Python notes that a corpus job
 *      with neither `txt` nor `urls` "fails silently" — that is how a phone
 *      seeds nothing overnight and reports success in the morning.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pt_internal.h"

/* A hard ceiling on file size. .ptorrent files are job descriptions measured
 * in kilobytes; the largest in the repository is 28 KB. Anything at this
 * bound is not a job description and should not be loaded into memory to
 * find that out. */
#define PT_PTFILE_MAX_BYTES (8u * 1024u * 1024u)

struct pt_ptfile {
    pt_json       *dom;
    const pt_json *evaluation;    /* borrowed from dom, may be NULL */
    const pt_json *security;      /* borrowed from dom, may be NULL */
    const pt_json *urls;          /* borrowed from dom, may be NULL */
    pt_job_type    type;
    pt_j_method    jmethod;
};

/* ── helpers ───────────────────────────────────────────────────────────── */

static const char *root_str(const pt_ptfile *p, const char *key, const char *dflt)
{
    if (!p) return dflt;
    return pt_json_string(pt_json_get(p->dom, key), dflt);
}

static const char *sub_str(const pt_json *obj, const char *key, const char *dflt)
{
    return pt_json_string(pt_json_get(obj, key), dflt);
}

static pt_job_type type_from_string(const char *s)
{
    if (!s) return PT_JOB_UNKNOWN;
    if (strcmp(s, "corpus")     == 0) return PT_JOB_CORPUS;
    if (strcmp(s, "dataset")    == 0) return PT_JOB_DATASET;
    if (strcmp(s, "transfer")   == 0) return PT_JOB_TRANSFER;
    if (strcmp(s, "phonebook")  == 0) return PT_JOB_PHONEBOOK;
    if (strcmp(s, "evaluation") == 0) return PT_JOB_EVALUATION;
    return PT_JOB_UNKNOWN;
}

/*
 * J-ratio extraction order, fixed by the spec:
 *   1 j_col   2 j_num_col/j_den_col   3 j_expr   4 fn   5 adapter fallback
 */
static pt_j_method j_method_of(const pt_json *ev)
{
    const char *s;

    if (!ev) return PT_J_NONE;

    s = sub_str(ev, "j_col", NULL);
    if (s && s[0]) return PT_J_COL;

    {
        const char *num = sub_str(ev, "j_num_col", NULL);
        const char *den = sub_str(ev, "j_den_col", NULL);
        if (num && num[0] && den && den[0]) return PT_J_NUM_DEN;
    }

    s = sub_str(ev, "j_expr", NULL);
    if (s && s[0]) return PT_J_EXPR;

    s = sub_str(ev, "fn", NULL);
    if (s && s[0]) return PT_J_FN;

    return PT_J_NONE;
}

/* ── parse / load / free ───────────────────────────────────────────────── */

pt_err pt_ptfile_parse(const char *text, size_t len, pt_ptfile **out,
                       char *errbuf, size_t errbuf_len)
{
    pt_json    *dom = NULL;
    pt_ptfile  *p;
    pt_err      rc;
    const char *ts;

    if (errbuf && errbuf_len) errbuf[0] = '\0';
    if (!text || !out) return PT_E_INVAL;
    *out = NULL;

    rc = pt_json_parse(text, len, &dom, errbuf, errbuf_len);
    if (rc != PT_OK) return rc;

    if (pt_json_type_of(dom) != PT_JSON_OBJECT) {
        pt_json_free(dom);
        pt_seterr(errbuf, errbuf_len, "top-level value is not an object");
        return PT_E_TYPE;
    }

    p = (pt_ptfile *)calloc(1, sizeof(*p));
    if (!p) { pt_json_free(dom); return PT_E_NOMEM; }
    p->dom = dom;

    /* Required by the spec: ptorrent_version, type, name, primary_tags,
     * color, description. Only the first three are load-bearing; refusing a
     * file for a missing `color` would reject otherwise valid jobs, so those
     * are left to a future validator with a warning level. */
    if (!pt_json_get(dom, "ptorrent_version")) {
        pt_ptfile_free(p);
        pt_seterr(errbuf, errbuf_len, "missing required field 'ptorrent_version'");
        return PT_E_PARSE;
    }

    ts = root_str(p, "type", NULL);
    if (!ts) {
        pt_ptfile_free(p);
        pt_seterr(errbuf, errbuf_len, "missing required field 'type'");
        return PT_E_PARSE;
    }
    p->type = type_from_string(ts);
    if (p->type == PT_JOB_UNKNOWN) {
        pt_ptfile_free(p);
        pt_seterr(errbuf, errbuf_len,
                  "unknown type '%s' (expected corpus, dataset, transfer, "
                  "phonebook, or evaluation)", ts);
        return PT_E_PARSE;
    }

    if (!root_str(p, "name", NULL)) {
        pt_ptfile_free(p);
        pt_seterr(errbuf, errbuf_len, "missing required field 'name'");
        return PT_E_PARSE;
    }

    p->evaluation = pt_json_get(dom, "evaluation");
    p->security   = pt_json_get(dom, "security");
    p->urls       = pt_json_get(dom, "urls");
    p->jmethod    = j_method_of(p->evaluation);

    /*
     * A corpus job with no source is the silent-failure case called out in
     * the spec's implementation notes. Refuse it here: a job that cannot do
     * anything must not be queueable.
     */
    if (p->type == PT_JOB_CORPUS) {
        const char *txt = root_str(p, "txt", NULL);
        int         nu  = (pt_json_type_of(p->urls) == PT_JSON_ARRAY)
                              ? pt_json_count(p->urls) : 0;
        if (!(txt && txt[0]) && nu == 0) {
            pt_ptfile_free(p);
            pt_seterr(errbuf, errbuf_len,
                      "corpus job has neither 'txt' nor a non-empty 'urls' array");
            return PT_E_PARSE;
        }
        if (!root_str(p, "bin", NULL)) {
            pt_ptfile_free(p);
            pt_seterr(errbuf, errbuf_len, "corpus job is missing 'bin'");
            return PT_E_PARSE;
        }
    }

    if (p->type == PT_JOB_EVALUATION && p->jmethod == PT_J_NONE) {
        pt_ptfile_free(p);
        pt_seterr(errbuf, errbuf_len,
                  "evaluation job declares no J-ratio method "
                  "(need one of j_col, j_num_col+j_den_col, j_expr, or fn)");
        return PT_E_PARSE;
    }

    *out = p;
    return PT_OK;
}

pt_err pt_ptfile_load(const char *path, pt_ptfile **out,
                      char *errbuf, size_t errbuf_len)
{
    FILE   *f;
    char   *buf;
    size_t  cap = 0, n = 0;
    long    sz;
    pt_err  rc;

    if (errbuf && errbuf_len) errbuf[0] = '\0';
    if (!path || !out) return PT_E_INVAL;
    *out = NULL;

    f = fopen(path, "rb");
    if (!f) { pt_seterr(errbuf, errbuf_len, "cannot open '%s'", path); return PT_E_IO; }

    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return PT_E_IO; }
    sz = ftell(f);
    if (sz < 0) { fclose(f); return PT_E_IO; }
    if (fseek(f, 0, SEEK_SET) != 0) { fclose(f); return PT_E_IO; }

    if ((unsigned long)sz > PT_PTFILE_MAX_BYTES) {
        fclose(f);
        pt_seterr(errbuf, errbuf_len,
                  "'%s' is %ld bytes; .ptorrent files are job descriptions, "
                  "limit is %u", path, sz, PT_PTFILE_MAX_BYTES);
        return PT_E_IO;
    }

    cap = (size_t)sz + 1;
    buf = (char *)malloc(cap);
    if (!buf) { fclose(f); return PT_E_NOMEM; }

    n = fread(buf, 1, (size_t)sz, f);
    fclose(f);
    buf[n] = '\0';

    rc = pt_ptfile_parse(buf, n, out, errbuf, errbuf_len);
    free(buf);
    return rc;
}

void pt_ptfile_free(pt_ptfile *p)
{
    if (!p) return;
    pt_json_free(p->dom);
    free(p);
}

/* ── root accessors ────────────────────────────────────────────────────── */

const pt_json *pt_ptfile_json(const pt_ptfile *p) { return p ? p->dom : NULL; }

const char *pt_ptfile_version(const pt_ptfile *p)      { return root_str(p, "ptorrent_version", NULL); }
const char *pt_ptfile_type_string(const pt_ptfile *p)  { return root_str(p, "type", NULL); }
const char *pt_ptfile_name(const pt_ptfile *p)         { return root_str(p, "name", NULL); }
const char *pt_ptfile_bin(const pt_ptfile *p)          { return root_str(p, "bin", NULL); }
const char *pt_ptfile_description(const pt_ptfile *p)  { return root_str(p, "description", NULL); }
const char *pt_ptfile_color(const pt_ptfile *p)        { return root_str(p, "color", NULL); }
const char *pt_ptfile_output(const pt_ptfile *p)       { return root_str(p, "output", NULL); }
const char *pt_ptfile_requires_bin(const pt_ptfile *p) { return root_str(p, "requires_bin", NULL); }

pt_job_type pt_ptfile_type(const pt_ptfile *p) { return p ? p->type : PT_JOB_UNKNOWN; }

/*
 * The spec's default UA hint is "ptolemy". A crawler that cannot be
 * identified or asked to stop is the kind that gets an address range banned,
 * and a fleet of phones burns many addresses. The transport layer is
 * responsible for expanding this into a full User-Agent with contact info.
 */
const char *pt_ptfile_user_agent(const pt_ptfile *p)
{
    return root_str(p, "ua", "ptolemy");
}

int pt_ptfile_checkpoint_every(const pt_ptfile *p)
{
    double d;
    if (!p) return 10;
    d = pt_json_number(pt_json_get(p->dom, "checkpoint_every"), 10.0);
    if (d < 1.0)      return 1;
    if (d > 100000.0) return 100000;
    return (int)d;
}

int pt_ptfile_tag_count(const pt_ptfile *p)
{
    const pt_json *a;
    if (!p) return 0;
    a = pt_json_get(p->dom, "primary_tags");
    return pt_json_type_of(a) == PT_JSON_ARRAY ? pt_json_count(a) : 0;
}

const char *pt_ptfile_tag_at(const pt_ptfile *p, int i)
{
    const pt_json *a;
    if (!p) return NULL;
    a = pt_json_get(p->dom, "primary_tags");
    return pt_json_string(pt_json_at(a, i), NULL);
}

int pt_ptfile_url_count(const pt_ptfile *p)
{
    if (!p || pt_json_type_of(p->urls) != PT_JSON_ARRAY) return 0;
    return pt_json_count(p->urls);
}

const char *pt_ptfile_url_at(const pt_ptfile *p, int i)
{
    if (!p) return NULL;
    return sub_str(pt_json_at(p->urls, i), "url", NULL);
}

const char *pt_ptfile_url_tag_at(const pt_ptfile *p, int i)
{
    if (!p) return NULL;
    return sub_str(pt_json_at(p->urls, i), "tag", NULL);
}

/* ── security ──────────────────────────────────────────────────────────── */

int pt_ptfile_security_level(const pt_ptfile *p)
{
    double d;
    if (!p || !p->security) return 0;
    d = pt_json_number(pt_json_get(p->security, "level"), 0.0);
    if (d < 0.0) return 0;
    if (d > 3.0) return 3;
    return (int)d;
}

const char *pt_ptfile_security_classification(const pt_ptfile *p)
{
    return p ? sub_str(p->security, "classification", "public") : "public";
}

const char *pt_ptfile_security_warning(const pt_ptfile *p)
{
    return p ? sub_str(p->security, "warning", NULL) : NULL;
}

const char *pt_ptfile_security_embargo_until(const pt_ptfile *p)
{
    return p ? sub_str(p->security, "embargo_until", NULL) : NULL;
}

int pt_ptfile_security_acknowledge_required(const pt_ptfile *p)
{
    if (!p || !p->security) return 0;
    return pt_json_bool(pt_json_get(p->security, "acknowledge_required"), 0);
}

/*
 * Embargo — a date comparison, and nothing more. See the status note in
 * ptorrent.h: no file in the repository uses this field, and a calendar date
 * is the wrong primitive for the coordinated-disclosure case it was aimed at,
 * which gates on a record state (RESERVED vs PUBLISHED) rather than a
 * deadline. Kept because the spec defines the field; not built upon.
 *
 * Within that narrow question, two fail-closed choices, both deliberate:
 *   - a malformed embargo_until blocks rather than passes. A date the core
 *     cannot read is not permission.
 *   - a malformed today_iso also blocks. The host failing to supply a date is
 *     not permission either.
 */
int pt_ptfile_embargoed(const pt_ptfile *p, const char *today_iso)
{
    const char *until;
    int         c;

    if (!p) return 0;

    until = pt_ptfile_security_embargo_until(p);
    if (!until || !until[0]) return 0;          /* no embargo declared */

    c = pt_iso_date_cmp(today_iso, until);
    if (c == -2) return 1;                      /* unreadable date -> blocked */
    return c < 0 ? 1 : 0;                       /* before the date -> blocked */
}

/* ── evaluation ────────────────────────────────────────────────────────── */

int pt_ptfile_has_evaluation(const pt_ptfile *p)
{
    return (p && p->evaluation && pt_json_type_of(p->evaluation) == PT_JSON_OBJECT)
           ? 1 : 0;
}

pt_j_method pt_ptfile_j_method(const pt_ptfile *p) { return p ? p->jmethod : PT_J_NONE; }

const char *pt_ptfile_j_expr(const pt_ptfile *p)     { return p ? sub_str(p->evaluation, "j_expr", NULL)      : NULL; }
const char *pt_ptfile_j_col(const pt_ptfile *p)      { return p ? sub_str(p->evaluation, "j_col", NULL)       : NULL; }
const char *pt_ptfile_j_num_col(const pt_ptfile *p)  { return p ? sub_str(p->evaluation, "j_num_col", NULL)   : NULL; }
const char *pt_ptfile_j_den_col(const pt_ptfile *p)  { return p ? sub_str(p->evaluation, "j_den_col", NULL)   : NULL; }
const char *pt_ptfile_j_fn(const pt_ptfile *p)       { return p ? sub_str(p->evaluation, "fn", NULL)          : NULL; }
const char *pt_ptfile_methodology(const pt_ptfile *p){ return p ? sub_str(p->evaluation, "methodology", NULL) : NULL; }
const char *pt_ptfile_prediction(const pt_ptfile *p) { return p ? sub_str(p->evaluation, "prediction", NULL)  : NULL; }

int pt_ptfile_j_expr_col_count(const pt_ptfile *p)
{
    const pt_json *a;
    if (!p) return 0;
    a = pt_json_get(p->evaluation, "j_expr_cols");
    return pt_json_type_of(a) == PT_JSON_ARRAY ? pt_json_count(a) : 0;
}

const char *pt_ptfile_j_expr_col_at(const pt_ptfile *p, int i)
{
    if (!p) return NULL;
    return pt_json_string(pt_json_at(pt_json_get(p->evaluation, "j_expr_cols"), i),
                          NULL);
}

/*
 * Columns the source must be asked for.
 *
 * Minimum column movement is the entire economic argument for in-situ
 * evaluation — 128 GB stays where it is and a few kilobytes come back — so
 * getting this list right is a core concern, never an adapter's.
 *
 * The declared j_expr_cols is a researcher's hand-written list and drifts
 * from the expression it is supposed to describe. Rather than trust it, the
 * expression is compiled and its actual identifiers are unioned in. A column
 * declared but unused costs one column of transfer; a column used but
 * undeclared costs the entire traversal, discovered on the first row.
 */
int pt_ptfile_required_columns(const pt_ptfile *p, const char **out, int max)
{
    int n = 0, i, k;

    if (!p || !out || max <= 0) return PT_E_INVAL;

    for (i = 0; i < pt_ptfile_j_expr_col_count(p) && n < max; i++) {
        const char *c = pt_ptfile_j_expr_col_at(p, i);
        if (c && c[0]) out[n++] = c;
    }

    switch (p->jmethod) {
    case PT_J_COL: {
        const char *c = pt_ptfile_j_col(p);
        if (c && c[0] && n < max) out[n++] = c;
        break;
    }
    case PT_J_NUM_DEN: {
        const char *a = pt_ptfile_j_num_col(p);
        const char *b = pt_ptfile_j_den_col(p);
        if (a && a[0] && n < max) out[n++] = a;
        if (b && b[0] && n < max) out[n++] = b;
        break;
    }
    case PT_J_EXPR: {
        pt_jexpr   *e   = NULL;
        const char *src = pt_ptfile_j_expr(p);
        if (src && pt_jexpr_compile(src, &e, NULL, 0) == PT_OK) {
            for (i = 0; i < pt_jexpr_var_count(e) && n < max; i++) {
                const char *v   = pt_jexpr_var_at(e, i);
                int         dup = 0;
                for (k = 0; k < n; k++)
                    if (out[k] && strcmp(out[k], v) == 0) { dup = 1; break; }
                /* The borrowed pointer must outlive the compiled expression,
                 * so return the declared string when one matches, and skip
                 * the column otherwise — an undeclared identifier is a
                 * configuration error surfaced by pt_jexpr_eval(). */
                if (!dup) {
                    int j;
                    for (j = 0; j < pt_ptfile_j_expr_col_count(p); j++) {
                        const char *d = pt_ptfile_j_expr_col_at(p, j);
                        if (d && strcmp(d, v) == 0) { out[n++] = d; break; }
                    }
                }
            }
            pt_jexpr_free(e);
        }
        break;
    }
    default:
        break;
    }

    return n;
}
