/*
 * pt_test.h — the smallest test harness that still reports usefully.
 *
 * No framework dependency: the core builds with cc and libc alone, and its
 * tests should not be the thing that breaks that promise on a new platform.
 */

#ifndef PT_TEST_H
#define PT_TEST_H

#include <stdio.h>
#include <string.h>
#include <math.h>

static int pt_t_pass = 0;
static int pt_t_fail = 0;
static const char *pt_t_suite = "?";

#define T_SUITE(name) do { pt_t_suite = (name); } while (0)

#define T_OK(cond, ...) do {                                                  \
        if (cond) { pt_t_pass++; }                                            \
        else {                                                                \
            pt_t_fail++;                                                      \
            printf("  \033[31mFAIL\033[0m %s:%d  ", __FILE__, __LINE__);      \
            printf(__VA_ARGS__);                                              \
            printf("\n");                                                     \
        }                                                                     \
    } while (0)

#define T_EQ_INT(a, b, ...) do {                                              \
        long long _a = (long long)(a), _b = (long long)(b);                   \
        if (_a == _b) { pt_t_pass++; }                                        \
        else {                                                                \
            pt_t_fail++;                                                      \
            printf("  \033[31mFAIL\033[0m %s:%d  ", __FILE__, __LINE__);      \
            printf(__VA_ARGS__);                                              \
            printf("  (got %lld, want %lld)\n", _a, _b);                      \
        }                                                                     \
    } while (0)

#define T_EQ_STR(a, b, ...) do {                                              \
        const char *_a = (a), *_b = (b);                                      \
        int _ok = (_a && _b) ? (strcmp(_a, _b) == 0) : (_a == _b);            \
        if (_ok) { pt_t_pass++; }                                             \
        else {                                                                \
            pt_t_fail++;                                                      \
            printf("  \033[31mFAIL\033[0m %s:%d  ", __FILE__, __LINE__);      \
            printf(__VA_ARGS__);                                              \
            printf("  (got \"%s\", want \"%s\")\n",                           \
                   _a ? _a : "(null)", _b ? _b : "(null)");                   \
        }                                                                     \
    } while (0)

/* Doubles compare within a relative tolerance; exact equality is only used
 * where the arithmetic is exactly representable. */
#define T_EQ_DBL(a, b, ...) do {                                              \
        double _a = (a), _b = (b);                                            \
        double _s = fabs(_b) > 1.0 ? fabs(_b) : 1.0;                          \
        if (fabs(_a - _b) <= 1e-12 * _s) { pt_t_pass++; }                     \
        else {                                                                \
            pt_t_fail++;                                                      \
            printf("  \033[31mFAIL\033[0m %s:%d  ", __FILE__, __LINE__);      \
            printf(__VA_ARGS__);                                              \
            printf("  (got %.17g, want %.17g)\n", _a, _b);                    \
        }                                                                     \
    } while (0)

#define T_IS_NAN(a, ...) do {                                                 \
        double _a = (a);                                                      \
        if (_a != _a) { pt_t_pass++; }                                        \
        else {                                                                \
            pt_t_fail++;                                                      \
            printf("  \033[31mFAIL\033[0m %s:%d  ", __FILE__, __LINE__);      \
            printf(__VA_ARGS__);                                              \
            printf("  (got %.17g, want NaN)\n", _a);                          \
        }                                                                     \
    } while (0)

static int pt_t_report(void)
{
    if (pt_t_fail == 0) {
        printf("\033[32mPASS\033[0m %-14s %d checks\n", pt_t_suite, pt_t_pass);
        return 0;
    }
    printf("\033[31mFAIL\033[0m %-14s %d passed, %d failed\n",
           pt_t_suite, pt_t_pass, pt_t_fail);
    return 1;
}

#endif /* PT_TEST_H */
