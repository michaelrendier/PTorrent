/*
 * pt_json.c — dependency-free UTF-8 JSON DOM parser.
 *
 * Why hand-rolled rather than vendored: the core must build on five platforms
 * where adding a dependency is a port, and one JSON implementation everywhere
 * means one set of JSON bugs everywhere. It is small enough to be read.
 *
 * Hardening notes — .ptorrent files arrive from strangers:
 *   - recursion is bounded by PT_MAX_DEPTH
 *   - input is a (ptr, len) slice, never assumed NUL-terminated
 *   - every allocation is checked
 *   - lone surrogates are rejected rather than silently producing bad UTF-8
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "pt_internal.h"

struct pt_json {
    pt_json_type type;
    union {
        double  num;
        int     boolean;
        struct { char *s; }                                    str;
        struct { pt_json **items; int count, cap; }             arr;
        struct { char **keys; pt_json **vals; int count, cap; } obj;
    } u;
};

typedef struct {
    const char *p;      /* cursor            */
    const char *end;    /* one past last     */
    const char *start;  /* for line/col calc */
    int         depth;
    char       *errbuf;
    size_t      errlen;
} P;

/* ── error reporting ───────────────────────────────────────────────────── */

static pt_err fail(P *ps, const char *msg)
{
    long line = 1, col = 1;
    const char *q;
    for (q = ps->start; q < ps->p && q < ps->end; q++) {
        if (*q == '\n') { line++; col = 1; } else { col++; }
    }
    pt_seterr(ps->errbuf, ps->errlen, "line %ld col %ld: %s", line, col, msg);
    return PT_E_PARSE;
}

/* ── node lifecycle ────────────────────────────────────────────────────── */

static pt_json *node_new(pt_json_type t)
{
    pt_json *j = (pt_json *)calloc(1, sizeof(*j));
    if (j) j->type = t;
    return j;
}

void pt_json_free(pt_json *j)
{
    int i;
    if (!j) return;
    switch (j->type) {
    case PT_JSON_STRING:
        free(j->u.str.s);
        break;
    case PT_JSON_ARRAY:
        for (i = 0; i < j->u.arr.count; i++) pt_json_free(j->u.arr.items[i]);
        free(j->u.arr.items);
        break;
    case PT_JSON_OBJECT:
        for (i = 0; i < j->u.obj.count; i++) {
            free(j->u.obj.keys[i]);
            pt_json_free(j->u.obj.vals[i]);
        }
        free(j->u.obj.keys);
        free(j->u.obj.vals);
        break;
    default:
        break;
    }
    free(j);
}

static int arr_push(pt_json *a, pt_json *v)
{
    if (a->u.arr.count == a->u.arr.cap) {
        int ncap = a->u.arr.cap ? a->u.arr.cap * 2 : 8;
        pt_json **n = (pt_json **)realloc(a->u.arr.items,
                                          (size_t)ncap * sizeof(*n));
        if (!n) return 0;
        a->u.arr.items = n;
        a->u.arr.cap   = ncap;
    }
    a->u.arr.items[a->u.arr.count++] = v;
    return 1;
}

static int obj_push(pt_json *o, char *k, pt_json *v)
{
    if (o->u.obj.count == o->u.obj.cap) {
        int ncap = o->u.obj.cap ? o->u.obj.cap * 2 : 8;
        char    **nk = (char **)realloc(o->u.obj.keys,
                                        (size_t)ncap * sizeof(*nk));
        pt_json **nv;
        if (!nk) return 0;
        o->u.obj.keys = nk;
        nv = (pt_json **)realloc(o->u.obj.vals, (size_t)ncap * sizeof(*nv));
        if (!nv) return 0;
        o->u.obj.vals = nv;
        o->u.obj.cap  = ncap;
    }
    o->u.obj.keys[o->u.obj.count] = k;
    o->u.obj.vals[o->u.obj.count] = v;
    o->u.obj.count++;
    return 1;
}

/* ── lexical ───────────────────────────────────────────────────────────── */

static void skip_ws(P *ps)
{
    while (ps->p < ps->end) {
        char c = *ps->p;
        if (c == ' ' || c == '\t' || c == '\n' || c == '\r') ps->p++;
        else break;
    }
}

static int at(P *ps, char c) { return ps->p < ps->end && *ps->p == c; }

/* Encode one code point as UTF-8. Returns bytes written (1..4). */
static int utf8_put(char *dst, unsigned long cp)
{
    if (cp < 0x80UL) {
        dst[0] = (char)cp;
        return 1;
    } else if (cp < 0x800UL) {
        dst[0] = (char)(0xC0 | (cp >> 6));
        dst[1] = (char)(0x80 | (cp & 0x3F));
        return 2;
    } else if (cp < 0x10000UL) {
        dst[0] = (char)(0xE0 | (cp >> 12));
        dst[1] = (char)(0x80 | ((cp >> 6) & 0x3F));
        dst[2] = (char)(0x80 | (cp & 0x3F));
        return 3;
    }
    dst[0] = (char)(0xF0 | (cp >> 18));
    dst[1] = (char)(0x80 | ((cp >> 12) & 0x3F));
    dst[2] = (char)(0x80 | ((cp >> 6) & 0x3F));
    dst[3] = (char)(0x80 | (cp & 0x3F));
    return 4;
}

static int hex4(const char *s, unsigned *out)
{
    unsigned v = 0;
    int i;
    for (i = 0; i < 4; i++) {
        char c = s[i];
        v <<= 4;
        if      (c >= '0' && c <= '9') v |= (unsigned)(c - '0');
        else if (c >= 'a' && c <= 'f') v |= (unsigned)(c - 'a' + 10);
        else if (c >= 'A' && c <= 'F') v |= (unsigned)(c - 'A' + 10);
        else return 0;
    }
    *out = v;
    return 1;
}

/*
 * Parse a JSON string literal into a freshly allocated NUL-terminated buffer.
 * The cursor must be on the opening quote.
 */
static pt_err parse_string_raw(P *ps, char **out)
{
    const char *q;
    size_t cap, n = 0;
    char *buf;

    if (!at(ps, '"')) return fail(ps, "expected string");
    ps->p++;

    /* Unescaped output is never longer than the escaped input. */
    cap = (size_t)(ps->end - ps->p) + 1;
    buf = (char *)malloc(cap);
    if (!buf) return PT_E_NOMEM;

    q = ps->p;
    while (q < ps->end && *q != '"') {
        unsigned char c = (unsigned char)*q;

        if (c < 0x20) {
            free(buf);
            ps->p = q;
            return fail(ps, "control character in string");
        }

        if (c != '\\') { buf[n++] = (char)c; q++; continue; }

        q++;
        if (q >= ps->end) { free(buf); ps->p = q; return fail(ps, "unterminated escape"); }

        switch (*q) {
        case '"':  buf[n++] = '"';  q++; break;
        case '\\': buf[n++] = '\\'; q++; break;
        case '/':  buf[n++] = '/';  q++; break;
        case 'b':  buf[n++] = '\b'; q++; break;
        case 'f':  buf[n++] = '\f'; q++; break;
        case 'n':  buf[n++] = '\n'; q++; break;
        case 'r':  buf[n++] = '\r'; q++; break;
        case 't':  buf[n++] = '\t'; q++; break;
        case 'u': {
            unsigned      hi;
            unsigned long cp;
            q++;
            if (ps->end - q < 4 || !hex4(q, &hi)) {
                free(buf); ps->p = q; return fail(ps, "bad \\u escape");
            }
            q += 4;
            cp = hi;
            if (hi >= 0xD800u && hi <= 0xDBFFu) {           /* high surrogate */
                unsigned lo;
                if (ps->end - q < 6 || q[0] != '\\' || q[1] != 'u' ||
                    !hex4(q + 2, &lo) || lo < 0xDC00u || lo > 0xDFFFu) {
                    free(buf); ps->p = q;
                    return fail(ps, "unpaired high surrogate");
                }
                q += 6;
                cp = 0x10000UL + (((unsigned long)hi - 0xD800UL) << 10)
                               + ((unsigned long)lo - 0xDC00UL);
            } else if (hi >= 0xDC00u && hi <= 0xDFFFu) {
                free(buf); ps->p = q;
                return fail(ps, "unpaired low surrogate");
            }
            n += (size_t)utf8_put(buf + n, cp);
            break;
        }
        default:
            free(buf); ps->p = q;
            return fail(ps, "unknown escape");
        }
    }

    if (q >= ps->end) { free(buf); ps->p = q; return fail(ps, "unterminated string"); }

    buf[n] = '\0';
    ps->p  = q + 1;              /* consume closing quote */
    *out   = buf;
    return PT_OK;
}

/* JSON number grammar: -?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)? */
static pt_err parse_number(P *ps, pt_json **out)
{
    const char *s = ps->p;
    const char *q = s;
    char       *tmp;
    pt_json    *j;

    if (q < ps->end && *q == '-') q++;

    if (q >= ps->end || *q < '0' || *q > '9') return fail(ps, "bad number");
    if (*q == '0') {
        q++;
    } else {
        while (q < ps->end && *q >= '0' && *q <= '9') q++;
    }

    if (q < ps->end && *q == '.') {
        q++;
        if (q >= ps->end || *q < '0' || *q > '9') return fail(ps, "bad fraction");
        while (q < ps->end && *q >= '0' && *q <= '9') q++;
    }

    if (q < ps->end && (*q == 'e' || *q == 'E')) {
        q++;
        if (q < ps->end && (*q == '+' || *q == '-')) q++;
        if (q >= ps->end || *q < '0' || *q > '9') return fail(ps, "bad exponent");
        while (q < ps->end && *q >= '0' && *q <= '9') q++;
    }

    tmp = pt_strndup(s, (size_t)(q - s));
    if (!tmp) return PT_E_NOMEM;

    j = node_new(PT_JSON_NUMBER);
    if (!j) { free(tmp); return PT_E_NOMEM; }

    j->u.num = strtod(tmp, NULL);
    free(tmp);

    ps->p = q;
    *out  = j;
    return PT_OK;
}

static pt_err parse_value(P *ps, pt_json **out);

static pt_err parse_array(P *ps, pt_json **out)
{
    pt_json *a = node_new(PT_JSON_ARRAY);
    if (!a) return PT_E_NOMEM;

    ps->p++;                       /* '[' */
    skip_ws(ps);

    if (at(ps, ']')) { ps->p++; *out = a; return PT_OK; }

    for (;;) {
        pt_json *v  = NULL;
        pt_err   rc = parse_value(ps, &v);
        if (rc != PT_OK) { pt_json_free(a); return rc; }
        if (!arr_push(a, v)) { pt_json_free(v); pt_json_free(a); return PT_E_NOMEM; }

        skip_ws(ps);
        if (at(ps, ',')) { ps->p++; skip_ws(ps); continue; }
        if (at(ps, ']')) { ps->p++; break; }

        pt_json_free(a);
        return fail(ps, "expected ',' or ']'");
    }

    *out = a;
    return PT_OK;
}

static pt_err parse_object(P *ps, pt_json **out)
{
    pt_json *o = node_new(PT_JSON_OBJECT);
    if (!o) return PT_E_NOMEM;

    ps->p++;                       /* '{' */
    skip_ws(ps);

    if (at(ps, '}')) { ps->p++; *out = o; return PT_OK; }

    for (;;) {
        char    *k  = NULL;
        pt_json *v  = NULL;
        pt_err   rc;

        skip_ws(ps);
        rc = parse_string_raw(ps, &k);
        if (rc != PT_OK) { pt_json_free(o); return rc; }

        skip_ws(ps);
        if (!at(ps, ':')) { free(k); pt_json_free(o); return fail(ps, "expected ':'"); }
        ps->p++;
        skip_ws(ps);

        rc = parse_value(ps, &v);
        if (rc != PT_OK) { free(k); pt_json_free(o); return rc; }

        if (!obj_push(o, k, v)) {
            free(k); pt_json_free(v); pt_json_free(o);
            return PT_E_NOMEM;
        }

        skip_ws(ps);
        if (at(ps, ',')) { ps->p++; continue; }
        if (at(ps, '}')) { ps->p++; break; }

        pt_json_free(o);
        return fail(ps, "expected ',' or '}'");
    }

    *out = o;
    return PT_OK;
}

static pt_err lit(P *ps, const char *word, pt_json_type t, int bval,
                  pt_json **out)
{
    size_t n = strlen(word);
    pt_json *j;
    if ((size_t)(ps->end - ps->p) < n || memcmp(ps->p, word, n) != 0)
        return fail(ps, "unexpected token");
    j = node_new(t);
    if (!j) return PT_E_NOMEM;
    j->u.boolean = bval;
    ps->p += n;
    *out = j;
    return PT_OK;
}

static pt_err parse_value(P *ps, pt_json **out)
{
    pt_err rc;

    if (++ps->depth > PT_MAX_DEPTH) { ps->depth--; return fail(ps, "nesting too deep"); }
    skip_ws(ps);

    if (ps->p >= ps->end) { ps->depth--; return fail(ps, "unexpected end of input"); }

    switch (*ps->p) {
    case '{': rc = parse_object(ps, out); break;
    case '[': rc = parse_array(ps, out);  break;
    case '"': {
        char *s = NULL;
        rc = parse_string_raw(ps, &s);
        if (rc == PT_OK) {
            pt_json *j = node_new(PT_JSON_STRING);
            if (!j) { free(s); rc = PT_E_NOMEM; }
            else    { j->u.str.s = s; *out = j; }
        }
        break;
    }
    case 't': rc = lit(ps, "true",  PT_JSON_BOOL, 1, out); break;
    case 'f': rc = lit(ps, "false", PT_JSON_BOOL, 0, out); break;
    case 'n': rc = lit(ps, "null",  PT_JSON_NULL, 0, out); break;
    default:  rc = parse_number(ps, out);                  break;
    }

    ps->depth--;
    return rc;
}

pt_err pt_json_parse(const char *text, size_t len, pt_json **out,
                     char *errbuf, size_t errbuf_len)
{
    P       ps;
    pt_json *root = NULL;
    pt_err   rc;

    if (errbuf && errbuf_len) errbuf[0] = '\0';
    if (!text || !out) return PT_E_INVAL;
    *out = NULL;

    ps.p      = text;
    ps.end    = text + len;
    ps.start  = text;
    ps.depth  = 0;
    ps.errbuf = errbuf;
    ps.errlen = errbuf_len;

    /* UTF-8 BOM: tolerated. Some editors add it and a researcher hand-editing
     * a .ptorrent on Windows should not get an unexplained parse failure. */
    if (len >= 3 && (unsigned char)text[0] == 0xEF
                 && (unsigned char)text[1] == 0xBB
                 && (unsigned char)text[2] == 0xBF) {
        ps.p += 3;
    }

    rc = parse_value(&ps, &root);
    if (rc != PT_OK) return rc;

    skip_ws(&ps);
    if (ps.p != ps.end) {
        pt_json_free(root);
        return fail(&ps, "trailing content after top-level value");
    }

    *out = root;
    return PT_OK;
}

/* ── accessors ─────────────────────────────────────────────────────────── */

pt_json_type pt_json_type_of(const pt_json *j)
{
    return j ? j->type : PT_JSON_NULL;
}

const pt_json *pt_json_get(const pt_json *obj, const char *key)
{
    int i;
    if (!obj || obj->type != PT_JSON_OBJECT || !key) return NULL;
    for (i = 0; i < obj->u.obj.count; i++)
        if (strcmp(obj->u.obj.keys[i], key) == 0) return obj->u.obj.vals[i];
    return NULL;
}

int pt_json_count(const pt_json *j)
{
    if (!j) return 0;
    if (j->type == PT_JSON_ARRAY)  return j->u.arr.count;
    if (j->type == PT_JSON_OBJECT) return j->u.obj.count;
    return 0;
}

const pt_json *pt_json_at(const pt_json *arr, int i)
{
    if (!arr || arr->type != PT_JSON_ARRAY) return NULL;
    if (i < 0 || i >= arr->u.arr.count)     return NULL;
    return arr->u.arr.items[i];
}

const char *pt_json_key_at(const pt_json *obj, int i)
{
    if (!obj || obj->type != PT_JSON_OBJECT) return NULL;
    if (i < 0 || i >= obj->u.obj.count)      return NULL;
    return obj->u.obj.keys[i];
}

const char *pt_json_string(const pt_json *j, const char *fallback)
{
    return (j && j->type == PT_JSON_STRING) ? j->u.str.s : fallback;
}

double pt_json_number(const pt_json *j, double fallback)
{
    return (j && j->type == PT_JSON_NUMBER) ? j->u.num : fallback;
}

int pt_json_bool(const pt_json *j, int fallback)
{
    return (j && j->type == PT_JSON_BOOL) ? j->u.boolean : fallback;
}
