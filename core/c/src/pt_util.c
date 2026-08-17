/*
 * pt_util.c — small shared helpers.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pt_internal.h"

char *pt_strndup(const char *s, size_t n)
{
    char *p;
    if (!s) return NULL;
    p = (char *)malloc(n + 1);
    if (!p) return NULL;
    memcpy(p, s, n);
    p[n] = '\0';
    return p;
}

char *pt_strdup(const char *s)
{
    return s ? pt_strndup(s, strlen(s)) : NULL;
}

void pt_seterr(char *buf, size_t len, const char *fmt, ...)
{
    va_list ap;
    if (!buf || len == 0) return;
    va_start(ap, fmt);
    vsnprintf(buf, len, fmt, ap);
    va_end(ap);
    buf[len - 1] = '\0';
}

int pt_stricmp_ascii(const char *a, const char *b)
{
    if (a == b)   return 0;
    if (!a)       return -1;
    if (!b)       return 1;
    for (;;) {
        unsigned char ca = (unsigned char)*a++;
        unsigned char cb = (unsigned char)*b++;
        if (ca >= 'A' && ca <= 'Z') ca = (unsigned char)(ca - 'A' + 'a');
        if (cb >= 'A' && cb <= 'Z') cb = (unsigned char)(cb - 'A' + 'a');
        if (ca != cb) return ca < cb ? -1 : 1;
        if (ca == 0)  return 0;
    }
}

/* "YYYY-MM-DD" — exactly ten bytes, digits and two hyphens. */
static int iso_date_valid(const char *s)
{
    int i;
    if (!s) return 0;
    for (i = 0; i < 10; i++) {
        if (s[i] == '\0') return 0;
        if (i == 4 || i == 7) {
            if (s[i] != '-') return 0;
        } else if (s[i] < '0' || s[i] > '9') {
            return 0;
        }
    }
    return s[10] == '\0';
}

int pt_iso_date_cmp(const char *a, const char *b)
{
    if (!iso_date_valid(a) || !iso_date_valid(b)) return -2;
    {
        int c = memcmp(a, b, 10);
        return c < 0 ? -1 : (c > 0 ? 1 : 0);
    }
}
