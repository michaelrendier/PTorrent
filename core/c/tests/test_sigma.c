/*
 * test_sigma.c — sigma-face classification.
 *
 * The published bands, pinned at their boundaries. The INF band is entered
 * from both ends, which is exactly why UNDEFINED must exist separately.
 */

#include "ptorrent.h"
#include "pt_test.h"

int main(void)
{
    const double inv_d = 1.0 / PT_D_STAR;              /* 4.06504065... */
    const double upper = inv_d + PT_OMEGA_ZS;          /* 4.63218394... */

    T_SUITE("sigma");

    /* ── the published constants ───────────────────────────────────────── */
    T_EQ_DBL(PT_D_STAR,   0.246,               "d* is exactly as published");
    T_EQ_DBL(PT_OMEGA_ZS, 0.5671432904097838,  "Omega_ZS is exactly as published");

    /* ── band interiors ────────────────────────────────────────────────── */
    T_EQ_INT(pt_sigma_classify(0.0),   PT_SIGMA_INF,  "J=0 is the compressible limit");
    T_EQ_INT(pt_sigma_classify(0.1),   PT_SIGMA_INF,  "below d*");
    T_EQ_INT(pt_sigma_classify(0.5),   PT_SIGMA_HALF, "between d* and 1");
    T_EQ_INT(pt_sigma_classify(2.0),   PT_SIGMA_ONE,  "between 1 and 1/d*");
    T_EQ_INT(pt_sigma_classify(4.3),   PT_SIGMA_TWO,  "between 1/d* and 1/d*+Omega");
    T_EQ_INT(pt_sigma_classify(100.0), PT_SIGMA_INF,  "above the upper bound");

    /* ── boundaries are half-open: lower bound inclusive ───────────────── */
    T_EQ_INT(pt_sigma_classify(PT_D_STAR), PT_SIGMA_HALF, "J = d* is HALF");
    T_EQ_INT(pt_sigma_classify(1.0),       PT_SIGMA_ONE,  "J = 1 is ONE");
    T_EQ_INT(pt_sigma_classify(inv_d),     PT_SIGMA_TWO,  "J = 1/d* is TWO");
    T_EQ_INT(pt_sigma_classify(upper),     PT_SIGMA_INF,  "J = 1/d*+Omega is INF");

    /* Just below each boundary belongs to the band underneath. */
    T_EQ_INT(pt_sigma_classify(PT_D_STAR - 1e-9), PT_SIGMA_INF,  "just below d*");
    T_EQ_INT(pt_sigma_classify(1.0 - 1e-9),       PT_SIGMA_HALF, "just below 1");
    T_EQ_INT(pt_sigma_classify(inv_d - 1e-9),     PT_SIGMA_ONE,  "just below 1/d*");
    T_EQ_INT(pt_sigma_classify(upper - 1e-9),     PT_SIGMA_TWO,  "just below the top");

    /* ── negative J ────────────────────────────────────────────────────── */
    T_EQ_INT(pt_sigma_classify(-1.0), PT_SIGMA_INF,
             "negative J is below d* and lands in INF, per the published table");

    /* ── non-finite is UNDEFINED, never INF ────────────────────────────── */
    {
        double nan = 0.0 / 0.0;
        double inf = 1e308 * 10.0;
        T_EQ_INT(pt_sigma_classify(nan),  PT_SIGMA_UNDEFINED, "NaN is UNDEFINED");
        T_EQ_INT(pt_sigma_classify(inf),  PT_SIGMA_UNDEFINED, "+inf is UNDEFINED");
        T_EQ_INT(pt_sigma_classify(-inf), PT_SIGMA_UNDEFINED, "-inf is UNDEFINED");
    }

    /* ── labels ────────────────────────────────────────────────────────── */
    T_EQ_STR(pt_sigma_label(PT_SIGMA_HALF), "\xC2\xBD",     "the label is U+00BD");
    T_EQ_STR(pt_sigma_label(PT_SIGMA_ONE),  "1",            "label 1");
    T_EQ_STR(pt_sigma_label(PT_SIGMA_TWO),  "2",            "label 2");
    T_EQ_STR(pt_sigma_label(PT_SIGMA_INF),  "\xE2\x88\x9E", "the label is U+221E");
    T_EQ_STR(pt_sigma_semantic(PT_SIGMA_HALF), "causality",   "semantic half");
    T_EQ_STR(pt_sigma_semantic(PT_SIGMA_ONE),  "Yang-Mills",  "semantic one");
    T_EQ_STR(pt_sigma_semantic(PT_SIGMA_TWO),  "gravity",     "semantic two");
    T_EQ_STR(pt_sigma_semantic(PT_SIGMA_INF),  "BH interior", "semantic inf");

    /* ── tally ─────────────────────────────────────────────────────────── */
    {
        pt_sigma_tally t;
        pt_sigma_tally_reset(&t);

        pt_sigma_tally_add(&t, pt_sigma_classify(0.5));   /* half */
        pt_sigma_tally_add(&t, pt_sigma_classify(0.6));   /* half */
        pt_sigma_tally_add(&t, pt_sigma_classify(2.0));   /* one  */
        pt_sigma_tally_add(&t, pt_sigma_classify(4.3));   /* two  */
        pt_sigma_tally_add(&t, pt_sigma_classify(0.0));   /* inf  */
        pt_sigma_tally_add(&t, pt_sigma_classify(0.0 / 0.0));

        T_EQ_INT(t.half, 2, "half tally");
        T_EQ_INT(t.one,  1, "one tally");
        T_EQ_INT(t.two,  1, "two tally");
        T_EQ_INT(t.inf,  1, "inf tally");
        T_EQ_INT(t.undefined, 1, "undefined tally");

        /* Fractions must divide by measured rows, not offered rows — a
         * dataset that is half NULL would otherwise report every face at half
         * its true share. */
        T_EQ_INT(pt_sigma_tally_finite(&t), 5, "finite excludes undefined");
        T_EQ_INT(pt_sigma_tally_total(&t),  6, "total includes undefined");
    }

    return pt_t_report();
}
