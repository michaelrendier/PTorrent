/*
 * test_jexpr.c — the expression language.
 *
 * Two things are being defended here. First, that precedence matches Python
 * exactly, because every published j_expr was written by someone thinking in
 * Python and a silent -4 vs 4 would corrupt a result rather than fail it.
 * Second, the NaN discipline: an unmeasurable row must never become an
 * extreme one.
 */

#include <stdlib.h>
#include "ptorrent.h"
#include "pt_test.h"

static double evs(const char *src, pt_bindings *b)
{
    double d = 0.0;
    pt_err rc = pt_jexpr_eval_once(src, b, &d);
    if (rc != PT_OK) return (double)(0.0 / 0.0);
    return d;
}

static int bad(const char *src)
{
    pt_jexpr *e  = NULL;
    char      eb[128];
    pt_err    rc = pt_jexpr_compile(src, &e, eb, sizeof eb);
    if (rc == PT_OK) { pt_jexpr_free(e); return 0; }
    return 1;
}

int main(void)
{
    pt_bindings *b = pt_bindings_new();
    T_SUITE("jexpr");

    /* ── arithmetic and precedence ─────────────────────────────────────── */
    T_EQ_DBL(evs("1 + 2 * 3", b),        7.0,  "mul binds tighter than add");
    T_EQ_DBL(evs("(1 + 2) * 3", b),      9.0,  "parens");
    T_EQ_DBL(evs("10 - 2 - 3", b),       5.0,  "subtraction is left-assoc");
    T_EQ_DBL(evs("100 / 10 / 2", b),     5.0,  "division is left-assoc");

    /* Python semantics, and the reason this suite exists. */
    T_EQ_DBL(evs("-2 ** 2", b),         -4.0,  "-2**2 is -(2**2), as in Python");
    T_EQ_DBL(evs("2 ** -1", b),          0.5,  "2**-1 is legal and is 0.5");
    T_EQ_DBL(evs("2 ** 3 ** 2", b),    512.0,  "** is right-associative");
    T_EQ_DBL(evs("2 * -3", b),          -6.0,  "unary minus after an operator");
    T_EQ_DBL(evs("--3", b),              3.0,  "double negation");

    /* ── numbers ───────────────────────────────────────────────────────── */
    T_EQ_DBL(evs("1e3", b),           1000.0,  "exponent literal");
    T_EQ_DBL(evs("1.5e-2", b),          0.015, "negative exponent literal");
    T_EQ_DBL(evs(".5", b),               0.5,  "leading-dot literal");
    T_EQ_DBL(evs("2.50", b),             2.5,  "trailing zeros");

    /* ── constants ─────────────────────────────────────────────────────── */
    T_EQ_DBL(evs("pi", b),  3.14159265358979323846, "pi");
    T_EQ_DBL(evs("e", b),   2.71828182845904523536, "e");

    /* ── functions ─────────────────────────────────────────────────────── */
    T_EQ_DBL(evs("sqrt(16)", b),         4.0,  "sqrt");
    T_EQ_DBL(evs("abs(-7)", b),          7.0,  "abs");
    T_EQ_DBL(evs("log10(1000)", b),      3.0,  "log10");
    T_EQ_DBL(evs("exp(0)", b),           1.0,  "exp");
    T_EQ_DBL(evs("max(3, 9)", b),        9.0,  "max");
    T_EQ_DBL(evs("min(3, 9)", b),        3.0,  "min");
    T_EQ_DBL(evs("log(e)", b),           1.0,  "log of e is 1");

    /* ── variables ─────────────────────────────────────────────────────── */
    pt_bindings_clear(b);
    pt_bindings_set(b, "D_M",    1500.0);
    pt_bindings_set(b, "r_drag",  147.09);
    T_EQ_DBL(evs("D_M / r_drag", b), 1500.0 / 147.09, "the published BAO expression");

    pt_bindings_clear(b);
    pt_bindings_set(b, "pmra",     3.0);
    pt_bindings_set(b, "pmdec",    4.0);
    pt_bindings_set(b, "parallax", 0.5);
    T_EQ_DBL(evs("sqrt(pmra ** 2 + pmdec ** 2) / max(parallax, 0.001)", b),
             10.0, "the published Gaia expression");

    /* ── NaN discipline ────────────────────────────────────────────────── */
    pt_bindings_clear(b);
    pt_bindings_set(b, "x", 1.0);
    pt_bindings_set(b, "zero", 0.0);

    T_IS_NAN(evs("x / zero", b),      "division by zero is NaN, never infinity");
    T_IS_NAN(evs("sqrt(-1)", b),      "sqrt of a negative is NaN");
    T_IS_NAN(evs("log(0)", b),        "log of zero is NaN");
    T_IS_NAN(evs("log(-1)", b),       "log of a negative is NaN");
    T_IS_NAN(evs("log10(0)", b),      "log10 of zero is NaN");
    T_IS_NAN(evs("exp(100000)", b),   "overflow to infinity becomes NaN");
    T_IS_NAN(evs("1 / 0", b),         "literal division by zero is NaN");

    /* This is the load-bearing one: an infinite J would classify as INF and be
     * indistinguishable from a genuine force-extreme measurement. */
    T_EQ_INT(pt_sigma_classify(evs("x / zero", b)), PT_SIGMA_UNDEFINED,
             "an unmeasurable row classifies as UNDEFINED, not INF");

    /* NULL propagates; never-bound is an error. */
    pt_bindings_clear(b);
    pt_bindings_set_null(b, "flux");
    T_IS_NAN(evs("flux * 2", b), "a NULL column propagates NaN");
    {
        double d  = 0.0;
        pt_err rc = pt_jexpr_eval_once("flux * 2", b, &d);
        T_EQ_INT(rc, PT_OK, "NULL is a data condition, not a failure");
    }
    {
        double d  = 0.0;
        pt_err rc = pt_jexpr_eval_once("never_bound + 1", b, &d);
        T_EQ_INT(rc, PT_E_NOTFOUND,
                 "an unbound column is a job configuration error");
    }

    /* NaN is not an extremum — max() must not launder it away. */
    pt_bindings_clear(b);
    pt_bindings_set_null(b, "n");
    T_IS_NAN(evs("max(n, 5)", b), "max(NaN, 5) is NaN, not 5");
    T_IS_NAN(evs("min(n, 5)", b), "min(NaN, 5) is NaN, not 5");

    /* ── declared variables ────────────────────────────────────────────── */
    {
        pt_jexpr *e = NULL;
        T_EQ_INT(pt_jexpr_compile("a / b + a", &e, NULL, 0), PT_OK, "compiles");
        T_EQ_INT(pt_jexpr_var_count(e), 2, "repeated identifiers intern once");
        T_EQ_STR(pt_jexpr_var_at(e, 0), "a", "first variable");
        T_EQ_STR(pt_jexpr_var_at(e, 1), "b", "second variable");
        pt_jexpr_free(e);
    }
    {
        /* pi and e are constants, not columns. */
        pt_jexpr *e = NULL;
        pt_jexpr_compile("pi * r ** 2 / e", &e, NULL, 0);
        T_EQ_INT(pt_jexpr_var_count(e), 1, "pi and e are not counted as columns");
        T_EQ_STR(pt_jexpr_var_at(e, 0), "r", "only r is a column");
        pt_jexpr_free(e);
    }

    /* ── rejection: there is no escape hatch ───────────────────────────── */
    T_OK(bad("sine(x)"),        "unknown function is rejected");
    T_OK(bad("x %% 2"),         "modulo is not in the whitelist");
    T_OK(bad("x & 1"),          "bitwise operators are rejected");
    T_OK(bad("1 +"),            "truncated expression is rejected");
    T_OK(bad("(1 + 2"),         "unbalanced parens are rejected");
    T_OK(bad(""),               "empty expression is rejected");
    T_OK(bad("0x10"),           "hex literals are rejected");
    T_OK(bad("sqrt(1, 2)"),     "arity is checked: sqrt takes 1");
    T_OK(bad("max(1)"),         "arity is checked: max takes 2");
    T_OK(bad("1 2"),            "trailing tokens are rejected");
    T_OK(bad("x; drop table"),  "no statement separator exists");

    /* 'inf' compiles as an identifier but must not silently be infinity. */
    {
        pt_jexpr *e = NULL;
        if (pt_jexpr_compile("inf", &e, NULL, 0) == PT_OK) {
            double d  = 0.0;
            pt_err rc = pt_jexpr_eval(e, b, &d);
            T_EQ_INT(rc, PT_E_NOTFOUND, "'inf' is an unbound column, not infinity");
            pt_jexpr_free(e);
        }
    }

    /* A deeply nested expression must fail cleanly rather than smash the
     * stack — .ptorrent files arrive from strangers. */
    {
        char   *deep = (char *)malloc(4096);
        int     i;
        for (i = 0; i < 2000; i++) deep[i] = '(';
        deep[2000] = '1';
        for (i = 0; i < 2000; i++) deep[2001 + i] = ')';
        deep[4001] = '\0';
        T_OK(bad(deep), "2000-deep nesting is refused, not fatal");
        free(deep);
    }

    pt_bindings_free(b);
    return pt_t_report();
}
