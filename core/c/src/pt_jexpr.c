/*
 * pt_jexpr.c — the J-expression compiler and evaluator.
 *
 * A researcher's methodology travels as an arithmetic expression over column
 * names. This file is the reason that is safe: there is no escape hatch, no
 * dynamic loading, no host callback, and no operation outside the published
 * whitelist. An expression received from a stranger over the distribution
 * network can be run without trusting the stranger.
 *
 * Grammar (Python precedence — the reference implementation and every
 * published example are Python):
 *
 *     expr    := term (('+' | '-') term)*
 *     term    := unary (('*' | '/') unary)*
 *     unary   := ('-' | '+') unary | power
 *     power   := primary ('**' unary)?        right-associative
 *     primary := NUMBER | IDENT | CALL | '(' expr ')'
 *     CALL    := IDENT '(' expr (',' expr)* ')'
 *
 *   -2**2 parses as -(2**2) = -4, and 2**-1 = 0.5, matching Python exactly.
 *
 * NaN discipline is documented at pt_jexpr_eval() in ptorrent.h and enforced
 * here by fin(): every arithmetic result that is not finite becomes NaN. A
 * division by zero must NOT become infinity, because infinity classifies as
 * PT_SIGMA_INF and would silently fill the one sigma-face bucket that already
 * carries two disjoint physical meanings with rows that hold no measurement.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "pt_internal.h"

#ifndef NAN
#  define NAN (0.0 / 0.0)
#endif

/* ── AST ───────────────────────────────────────────────────────────────── */

typedef enum {
    N_NUM, N_VAR, N_NEG,
    N_ADD, N_SUB, N_MUL, N_DIV, N_POW,
    N_CALL
} ntype;

typedef enum {
    FN_SQRT, FN_ABS, FN_LOG, FN_LOG10, FN_EXP, FN_MAX, FN_MIN
} fnid;

static const struct { const char *name; fnid id; int argc; } FUNCS[] = {
    { "sqrt",  FN_SQRT,  1 },
    { "abs",   FN_ABS,   1 },
    { "log",   FN_LOG,   1 },
    { "log10", FN_LOG10, 1 },
    { "exp",   FN_EXP,   1 },
    { "max",   FN_MAX,   2 },
    { "min",   FN_MIN,   2 }
};
static const int N_FUNCS = (int)(sizeof(FUNCS) / sizeof(FUNCS[0]));

typedef struct node {
    ntype        t;
    double       num;    /* N_NUM             */
    int          var;    /* N_VAR: var index  */
    fnid         fn;     /* N_CALL            */
    struct node *a, *b;
} node;

struct pt_jexpr {
    node  *root;
    char **vars;         /* distinct referenced identifiers */
    int    nvars, capvars;
    char  *src;
};

/* ── parser state ──────────────────────────────────────────────────────── */

typedef struct {
    const char        *p;
    const char        *start;
    int                depth;
    char              *errbuf;
    size_t             errlen;
    struct pt_jexpr   *e;
    pt_err             rc;
} X;

static pt_err xfail(X *x, const char *msg)
{
    pt_seterr(x->errbuf, x->errlen, "col %ld: %s",
              (long)(x->p - x->start) + 1, msg);
    x->rc = PT_E_PARSE;
    return PT_E_PARSE;
}

static void node_free(node *n)
{
    if (!n) return;
    node_free(n->a);
    node_free(n->b);
    free(n);
}

static node *node_new(X *x, ntype t)
{
    node *n = (node *)calloc(1, sizeof(*n));
    if (!n) x->rc = PT_E_NOMEM;
    else    n->t  = t;
    return n;
}

/* Intern an identifier, returning its index in e->vars. -1 on OOM. */
static int var_intern(struct pt_jexpr *e, const char *name, size_t len)
{
    int i;
    for (i = 0; i < e->nvars; i++)
        if (strlen(e->vars[i]) == len && memcmp(e->vars[i], name, len) == 0)
            return i;

    if (e->nvars == e->capvars) {
        int    ncap = e->capvars ? e->capvars * 2 : 8;
        char **nv   = (char **)realloc(e->vars, (size_t)ncap * sizeof(*nv));
        if (!nv) return -1;
        e->vars    = nv;
        e->capvars = ncap;
    }
    e->vars[e->nvars] = pt_strndup(name, len);
    if (!e->vars[e->nvars]) return -1;
    return e->nvars++;
}

/* ── lexical helpers ───────────────────────────────────────────────────── */

static void xws(X *x)
{
    while (*x->p == ' ' || *x->p == '\t' || *x->p == '\n' || *x->p == '\r')
        x->p++;
}

static int is_ident_start(char c)
{
    return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || c == '_';
}

static int is_ident_char(char c)
{
    return is_ident_start(c) || (c >= '0' && c <= '9');
}

static node *parse_expr(X *x);

/*
 * Number literal: digits with optional fraction and exponent.
 *
 * Hand-validated rather than handed straight to strtod, because strtod also
 * accepts "0x10", "inf", and "nan" — none of which belong in a methodology
 * that another researcher is expected to read and audit.
 */
static node *parse_number(X *x)
{
    const char *s = x->p;
    char       *tmp;
    node       *n;
    int         digits = 0;

    while (*x->p >= '0' && *x->p <= '9') { x->p++; digits++; }

    if (*x->p == '.') {
        x->p++;
        while (*x->p >= '0' && *x->p <= '9') { x->p++; digits++; }
    }
    if (!digits) { xfail(x, "expected a number"); return NULL; }

    if (*x->p == 'e' || *x->p == 'E') {
        const char *save = x->p;
        x->p++;
        if (*x->p == '+' || *x->p == '-') x->p++;
        if (*x->p >= '0' && *x->p <= '9') {
            while (*x->p >= '0' && *x->p <= '9') x->p++;
        } else {
            x->p = save;              /* not an exponent after all */
        }
    }

    tmp = pt_strndup(s, (size_t)(x->p - s));
    if (!tmp) { x->rc = PT_E_NOMEM; return NULL; }

    n = node_new(x, N_NUM);
    if (!n) { free(tmp); return NULL; }
    n->num = strtod(tmp, NULL);
    free(tmp);
    return n;
}

static node *parse_primary(X *x)
{
    xws(x);

    if (*x->p == '(') {
        node *n;
        x->p++;
        n = parse_expr(x);
        if (!n) return NULL;
        xws(x);
        if (*x->p != ')') { node_free(n); xfail(x, "expected ')'"); return NULL; }
        x->p++;
        return n;
    }

    if (is_ident_start(*x->p)) {
        const char *s = x->p;
        size_t      len;
        int         i;

        while (is_ident_char(*x->p)) x->p++;
        len = (size_t)(x->p - s);

        /* Constants. Note deliberately: `e` is a published constant, so a
         * dataset column literally named "e" (orbital eccentricity, common in
         * astronomy) is shadowed. Declaring it in j_expr_cols will not help.
         * Rename the column in the source query — SELECT e AS ecc — or use
         * j_num_col / j_den_col instead. */
        if (len == 2 && memcmp(s, "pi", 2) == 0) {
            node *n = node_new(x, N_NUM);
            if (n) n->num = 3.14159265358979323846;
            return n;
        }
        if (len == 1 && s[0] == 'e') {
            node *n = node_new(x, N_NUM);
            if (n) n->num = 2.71828182845904523536;
            return n;
        }

        xws(x);
        if (*x->p == '(') {                       /* function call */
            for (i = 0; i < N_FUNCS; i++) {
                if (strlen(FUNCS[i].name) == len &&
                    memcmp(FUNCS[i].name, s, len) == 0) break;
            }
            if (i == N_FUNCS) {
                pt_seterr(x->errbuf, x->errlen,
                          "col %ld: unknown function '%.*s'",
                          (long)(s - x->start) + 1, (int)len, s);
                x->rc = PT_E_PARSE;
                return NULL;
            }
            {
                node *n = node_new(x, N_CALL);
                if (!n) return NULL;
                n->fn = FUNCS[i].id;

                x->p++;                            /* '(' */
                n->a = parse_expr(x);
                if (!n->a) { node_free(n); return NULL; }

                xws(x);
                if (FUNCS[i].argc == 2) {
                    if (*x->p != ',') {
                        node_free(n);
                        pt_seterr(x->errbuf, x->errlen,
                                  "col %ld: %s() takes 2 arguments",
                                  (long)(x->p - x->start) + 1, FUNCS[i].name);
                        x->rc = PT_E_PARSE;
                        return NULL;
                    }
                    x->p++;
                    n->b = parse_expr(x);
                    if (!n->b) { node_free(n); return NULL; }
                    xws(x);
                } else if (*x->p == ',') {
                    node_free(n);
                    pt_seterr(x->errbuf, x->errlen,
                              "col %ld: %s() takes 1 argument",
                              (long)(x->p - x->start) + 1, FUNCS[i].name);
                    x->rc = PT_E_PARSE;
                    return NULL;
                }

                if (*x->p != ')') { node_free(n); xfail(x, "expected ')'"); return NULL; }
                x->p++;
                return n;
            }
        }

        /* Plain column reference. */
        {
            int   idx = var_intern(x->e, s, len);
            node *n;
            if (idx < 0) { x->rc = PT_E_NOMEM; return NULL; }
            n = node_new(x, N_VAR);
            if (n) n->var = idx;
            return n;
        }
    }

    if ((*x->p >= '0' && *x->p <= '9') || *x->p == '.')
        return parse_number(x);

    if (*x->p == '\0') { xfail(x, "unexpected end of expression"); return NULL; }
    xfail(x, "unexpected character");
    return NULL;
}

static node *parse_unary(X *x);

/* power := primary ('**' unary)?   — right-associative */
static node *parse_power(X *x)
{
    node *base = parse_primary(x);
    if (!base) return NULL;

    xws(x);
    if (x->p[0] == '*' && x->p[1] == '*') {
        node *n;
        x->p += 2;
        n = node_new(x, N_POW);
        if (!n) { node_free(base); return NULL; }
        n->a = base;
        n->b = parse_unary(x);           /* right-assoc, and 2**-1 is legal */
        if (!n->b) { node_free(n); return NULL; }
        return n;
    }
    return base;
}

/* unary := ('-' | '+') unary | power */
static node *parse_unary(X *x)
{
    xws(x);

    if (++x->depth > PT_MAX_DEPTH) { x->depth--; xfail(x, "expression too deep"); return NULL; }

    /* '**' must not be mistaken for two unary '*'; only - and + are unary. */
    if (*x->p == '-') {
        node *n;
        x->p++;
        n = node_new(x, N_NEG);
        if (!n) { x->depth--; return NULL; }
        n->a = parse_unary(x);
        if (!n->a) { node_free(n); x->depth--; return NULL; }
        x->depth--;
        return n;
    }
    if (*x->p == '+') {
        node *n;
        x->p++;
        n = parse_unary(x);
        x->depth--;
        return n;
    }

    {
        node *n = parse_power(x);
        x->depth--;
        return n;
    }
}

/* term := unary (('*' | '/') unary)* */
static node *parse_term(X *x)
{
    node *lhs = parse_unary(x);
    if (!lhs) return NULL;

    for (;;) {
        node *n;
        ntype t;

        xws(x);
        if (x->p[0] == '*' && x->p[1] == '*') break;   /* belongs to power */
        if      (*x->p == '*') t = N_MUL;
        else if (*x->p == '/') t = N_DIV;
        else break;

        x->p++;
        n = node_new(x, t);
        if (!n) { node_free(lhs); return NULL; }
        n->a = lhs;
        n->b = parse_unary(x);
        if (!n->b) { node_free(n); return NULL; }
        lhs = n;
    }
    return lhs;
}

/* expr := term (('+' | '-') term)* */
static node *parse_expr(X *x)
{
    node *lhs;

    if (++x->depth > PT_MAX_DEPTH) { x->depth--; xfail(x, "expression too deep"); return NULL; }

    lhs = parse_term(x);
    if (!lhs) { x->depth--; return NULL; }

    for (;;) {
        node *n;
        ntype t;

        xws(x);
        if      (*x->p == '+') t = N_ADD;
        else if (*x->p == '-') t = N_SUB;
        else break;

        x->p++;
        n = node_new(x, t);
        if (!n) { node_free(lhs); x->depth--; return NULL; }
        n->a = lhs;
        n->b = parse_term(x);
        if (!n->b) { node_free(n); x->depth--; return NULL; }
        lhs = n;
    }

    x->depth--;
    return lhs;
}

/* ── public: compile / free ────────────────────────────────────────────── */

pt_err pt_jexpr_compile(const char *src, pt_jexpr **out,
                        char *errbuf, size_t errbuf_len)
{
    X                x;
    struct pt_jexpr *e;

    if (errbuf && errbuf_len) errbuf[0] = '\0';
    if (!src || !out) return PT_E_INVAL;
    *out = NULL;

    e = (struct pt_jexpr *)calloc(1, sizeof(*e));
    if (!e) return PT_E_NOMEM;

    e->src = pt_strdup(src);
    if (!e->src) { free(e); return PT_E_NOMEM; }

    x.p      = e->src;
    x.start  = e->src;
    x.depth  = 0;
    x.errbuf = errbuf;
    x.errlen = errbuf_len;
    x.e      = e;
    x.rc     = PT_OK;

    e->root = parse_expr(&x);
    if (!e->root) {
        pt_err rc = x.rc == PT_OK ? PT_E_PARSE : x.rc;
        if (rc == PT_E_NOMEM) pt_seterr(errbuf, errbuf_len, "out of memory");
        pt_jexpr_free(e);
        return rc;
    }

    xws(&x);
    if (*x.p != '\0') {
        xfail(&x, "trailing characters after expression");
        pt_jexpr_free(e);
        return PT_E_PARSE;
    }

    *out = e;
    return PT_OK;
}

void pt_jexpr_free(pt_jexpr *e)
{
    int i;
    if (!e) return;
    node_free(e->root);
    for (i = 0; i < e->nvars; i++) free(e->vars[i]);
    free(e->vars);
    free(e->src);
    free(e);
}

int pt_jexpr_var_count(const pt_jexpr *e)
{
    return e ? e->nvars : 0;
}

const char *pt_jexpr_var_at(const pt_jexpr *e, int i)
{
    if (!e || i < 0 || i >= e->nvars) return NULL;
    return e->vars[i];
}

/* ── bindings ──────────────────────────────────────────────────────────── */

typedef struct {
    char  *name;
    double v;
    int    isnull;
} binding;

struct pt_bindings {
    binding *items;
    int      count, cap;
};

pt_bindings *pt_bindings_new(void)
{
    return (pt_bindings *)calloc(1, sizeof(struct pt_bindings));
}

void pt_bindings_free(pt_bindings *b)
{
    int i;
    if (!b) return;
    for (i = 0; i < b->count; i++) free(b->items[i].name);
    free(b->items);
    free(b);
}

void pt_bindings_clear(pt_bindings *b)
{
    int i;
    if (!b) return;
    for (i = 0; i < b->count; i++) free(b->items[i].name);
    b->count = 0;                    /* capacity retained — reused per row */
}

static pt_err bind(pt_bindings *b, const char *name, double v, int isnull)
{
    int i;
    if (!b || !name) return PT_E_INVAL;

    for (i = 0; i < b->count; i++) {
        if (strcmp(b->items[i].name, name) == 0) {
            b->items[i].v      = v;
            b->items[i].isnull = isnull;
            return PT_OK;
        }
    }

    if (b->count == b->cap) {
        int      ncap = b->cap ? b->cap * 2 : 8;
        binding *n    = (binding *)realloc(b->items, (size_t)ncap * sizeof(*n));
        if (!n) return PT_E_NOMEM;
        b->items = n;
        b->cap   = ncap;
    }

    b->items[b->count].name = pt_strdup(name);
    if (!b->items[b->count].name) return PT_E_NOMEM;
    b->items[b->count].v      = v;
    b->items[b->count].isnull = isnull;
    b->count++;
    return PT_OK;
}

pt_err pt_bindings_set(pt_bindings *b, const char *name, double value)
{
    return bind(b, name, value, 0);
}

pt_err pt_bindings_set_null(pt_bindings *b, const char *name)
{
    return bind(b, name, NAN, 1);
}

/* Returns 1 if found; writes NaN for a NULL binding. */
static int binding_lookup(const pt_bindings *b, const char *name, double *out)
{
    int i;
    if (!b) return 0;
    for (i = 0; i < b->count; i++) {
        if (strcmp(b->items[i].name, name) == 0) {
            *out = b->items[i].isnull ? NAN : b->items[i].v;
            return 1;
        }
    }
    return 0;
}

/* ── evaluation ────────────────────────────────────────────────────────── */

/*
 * Every arithmetic result passes through here. Non-finite becomes NaN:
 * an unmeasurable row must be counted as unmeasured, never as extreme.
 */
static double fin(double x)
{
    return (x == x && x > -HUGE_VAL && x < HUGE_VAL) ? x : NAN;
}

static double ev(const node *n, const double *vals)
{
    switch (n->t) {
    case N_NUM: return n->num;
    case N_VAR: return vals[n->var];
    case N_NEG: return fin(-ev(n->a, vals));
    case N_ADD: return fin(ev(n->a, vals) + ev(n->b, vals));
    case N_SUB: return fin(ev(n->a, vals) - ev(n->b, vals));
    case N_MUL: return fin(ev(n->a, vals) * ev(n->b, vals));
    case N_DIV: return fin(ev(n->a, vals) / ev(n->b, vals));
    case N_POW: return fin(pow(ev(n->a, vals), ev(n->b, vals)));
    case N_CALL: {
        double a = ev(n->a, vals);
        switch (n->fn) {
        case FN_SQRT:  return fin(a < 0.0 ? NAN : sqrt(a));
        case FN_ABS:   return fin(fabs(a));
        case FN_LOG:   return fin(a <= 0.0 ? NAN : log(a));
        case FN_LOG10: return fin(a <= 0.0 ? NAN : log10(a));
        case FN_EXP:   return fin(exp(a));
        case FN_MAX: {
            double b = ev(n->b, vals);
            if (a != a || b != b) return NAN;      /* NaN is not an extremum */
            return fin(a > b ? a : b);
        }
        case FN_MIN: {
            double b = ev(n->b, vals);
            if (a != a || b != b) return NAN;
            return fin(a < b ? a : b);
        }
        }
        return NAN;
    }
    }
    return NAN;
}

pt_err pt_jexpr_eval(const pt_jexpr *e, const pt_bindings *b, double *out)
{
    double  stackvals[32];
    double *vals = stackvals;
    int     i;
    pt_err  rc = PT_OK;

    if (!e || !out) return PT_E_INVAL;

    if (e->nvars > (int)(sizeof(stackvals) / sizeof(stackvals[0]))) {
        vals = (double *)malloc((size_t)e->nvars * sizeof(double));
        if (!vals) return PT_E_NOMEM;
    }

    /*
     * Resolve every referenced column up front. This keeps ev() total — it
     * cannot fail partway through a row — and separates the two conditions
     * that are easy to conflate:
     *
     *   bound to NULL  -> a data condition. NaN. The row is unmeasured.
     *   never bound    -> a job configuration error. PT_E_NOTFOUND.
     *
     * The second means j_expr names a column the source was never asked for,
     * which is worth failing loudly on the first row rather than silently
     * returning an empty evaluation after traversing 128 GB.
     */
    for (i = 0; i < e->nvars; i++) {
        if (!binding_lookup(b, e->vars[i], &vals[i])) { rc = PT_E_NOTFOUND; break; }
    }

    if (rc == PT_OK) *out = ev(e->root, vals);

    if (vals != stackvals) free(vals);
    return rc;
}

pt_err pt_jexpr_eval_once(const char *src, const pt_bindings *b, double *out)
{
    pt_jexpr *e  = NULL;
    pt_err    rc = pt_jexpr_compile(src, &e, NULL, 0);
    if (rc != PT_OK) return rc;
    rc = pt_jexpr_eval(e, b, out);
    pt_jexpr_free(e);
    return rc;
}
