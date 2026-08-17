/*
 * pt_internal.h — helpers shared inside the core. Never installed.
 *
 * Nothing here appears in ptorrent.h and nothing here may be referenced by a
 * face. If a face needs it, it becomes API.
 */

#ifndef PT_INTERNAL_H
#define PT_INTERNAL_H

#include <stddef.h>
#include <stdarg.h>
#include "ptorrent.h"

/* Recursion ceiling for the JSON parser and the expression parser.
 * .ptorrent files arrive from strangers over a distribution network; an
 * unbounded recursive-descent parser is a stack-smash waiting for a file of
 * ten thousand open brackets. */
#define PT_MAX_DEPTH 200

/** strdup for a possibly non-NUL-terminated slice. Returns NULL on OOM. */
char *pt_strndup(const char *s, size_t n);

/** strdup. Returns NULL on OOM or if @p s is NULL. */
char *pt_strdup(const char *s);

/** snprintf into a caller error buffer, tolerating buf == NULL or len == 0. */
void pt_seterr(char *buf, size_t len, const char *fmt, ...);

/** ASCII case-insensitive compare; locale-independent by construction. */
int pt_stricmp_ascii(const char *a, const char *b);

/**
 * Validate and compare two "YYYY-MM-DD" strings lexicographically.
 * Returns -2 if either is malformed, else -1 / 0 / 1 like strcmp.
 * ISO-8601 dates in this form sort lexicographically, which is the whole
 * reason the spec mandates that form.
 */
int pt_iso_date_cmp(const char *a, const char *b);

#endif /* PT_INTERNAL_H */
