/*
 * pt_sigma.c — sigma-face classification.
 *
 * The thresholds are published in spec/ptorrent-format-v1.md and are fixed
 * constants, not fit parameters. Nothing here is derived, fitted, or tuned:
 * this file maps a dimensionless ratio onto four published bands and counts
 * them. That is the whole of it.
 *
 *     J <  d*                     -> INF   BH interior, compressible limit
 *     d*   <= J < 1               -> HALF  causality, critical line
 *     1    <= J < 1/d*            -> ONE   Yang-Mills, mass assembly
 *     1/d* <= J < 1/d* + Omega    -> TWO   gravity, force regime
 *     J >= 1/d* + Omega           -> INF   BH interior, force extreme
 *
 * Note that INF is entered from both ends. That is by design in the spec, and
 * it is precisely why a non-finite J must classify as UNDEFINED instead: an
 * unmeasurable row landing in INF would be indistinguishable from a real
 * force-extreme measurement, and INF is already the ambiguous bucket.
 */

#include <math.h>

#include "pt_internal.h"

pt_sigma_face pt_sigma_classify(double j)
{
    const double inv_d   = 1.0 / PT_D_STAR;            /* 4.0650406504065... */
    const double upper   = inv_d + PT_OMEGA_ZS;        /* 4.6321839408163... */

    /* NaN fails every comparison, so test it explicitly and first. */
    if (j != j)                       return PT_SIGMA_UNDEFINED;
    if (j <= -HUGE_VAL || j >= HUGE_VAL) return PT_SIGMA_UNDEFINED;

    if (j <  PT_D_STAR) return PT_SIGMA_INF;
    if (j <  1.0)       return PT_SIGMA_HALF;
    if (j <  inv_d)     return PT_SIGMA_ONE;
    if (j <  upper)     return PT_SIGMA_TWO;
    return PT_SIGMA_INF;
}

const char *pt_sigma_label(pt_sigma_face f)
{
    switch (f) {
    case PT_SIGMA_HALF: return "\xC2\xBD";              /* ½ U+00BD */
    case PT_SIGMA_ONE:  return "1";
    case PT_SIGMA_TWO:  return "2";
    case PT_SIGMA_INF:  return "\xE2\x88\x9E";          /* ∞ U+221E */
    case PT_SIGMA_UNDEFINED:
    default:            return "undefined";
    }
}

const char *pt_sigma_semantic(pt_sigma_face f)
{
    switch (f) {
    case PT_SIGMA_HALF: return "causality";
    case PT_SIGMA_ONE:  return "Yang-Mills";
    case PT_SIGMA_TWO:  return "gravity";
    case PT_SIGMA_INF:  return "BH interior";
    case PT_SIGMA_UNDEFINED:
    default:            return "undefined";
    }
}

void pt_sigma_tally_reset(pt_sigma_tally *t)
{
    if (!t) return;
    t->undefined = t->half = t->one = t->two = t->inf = 0;
}

void pt_sigma_tally_add(pt_sigma_tally *t, pt_sigma_face f)
{
    if (!t) return;
    switch (f) {
    case PT_SIGMA_HALF: t->half++;      break;
    case PT_SIGMA_ONE:  t->one++;       break;
    case PT_SIGMA_TWO:  t->two++;       break;
    case PT_SIGMA_INF:  t->inf++;       break;
    case PT_SIGMA_UNDEFINED:
    default:            t->undefined++; break;
    }
}

unsigned long long pt_sigma_tally_finite(const pt_sigma_tally *t)
{
    if (!t) return 0;
    return t->half + t->one + t->two + t->inf;
}

unsigned long long pt_sigma_tally_total(const pt_sigma_tally *t)
{
    if (!t) return 0;
    return pt_sigma_tally_finite(t) + t->undefined;
}
