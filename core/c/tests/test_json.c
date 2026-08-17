/*
 * test_json.c — the JSON parser.
 *
 * The hostile-input cases are not hypothetical: .ptorrent files travel over a
 * distribution network and arrive from people you have never met.
 */

#include <stdlib.h>
#include <string.h>
#include "ptorrent.h"
#include "pt_test.h"

static pt_json *ok(const char *s)
{
    pt_json *j  = NULL;
    char     eb[128];
    pt_err   rc = pt_json_parse(s, strlen(s), &j, eb, sizeof eb);
    if (rc != PT_OK) {
        printf("  (parse failed unexpectedly: %s -- %s)\n", s, eb);
        return NULL;
    }
    return j;
}

static int rejects(const char *s)
{
    pt_json *j  = NULL;
    pt_err   rc = pt_json_parse(s, strlen(s), &j, NULL, 0);
    if (rc == PT_OK) { pt_json_free(j); return 0; }
    return 1;
}

int main(void)
{
    T_SUITE("json");

    /* ── scalars ───────────────────────────────────────────────────────── */
    {
        pt_json *j = ok("42");
        T_EQ_INT(pt_json_type_of(j), PT_JSON_NUMBER, "number");
        T_EQ_DBL(pt_json_number(j, 0), 42.0, "number value");
        pt_json_free(j);
    }
    {
        pt_json *j = ok("-1.5e2");
        T_EQ_DBL(pt_json_number(j, 0), -150.0, "signed exponent");
        pt_json_free(j);
    }
    {
        pt_json *j = ok("true");
        T_EQ_INT(pt_json_bool(j, 0), 1, "true");
        pt_json_free(j);
    }
    {
        pt_json *j = ok("null");
        T_EQ_INT(pt_json_type_of(j), PT_JSON_NULL, "null");
        pt_json_free(j);
    }

    /* ── strings and escapes ───────────────────────────────────────────── */
    {
        pt_json *j = ok("\"a\\nb\\t\\\"c\\\"\"");
        T_EQ_STR(pt_json_string(j, NULL), "a\nb\t\"c\"", "escapes");
        pt_json_free(j);
    }
    {
        /* U+00BD ½ and U+221E ∞ — the sigma-face labels themselves. */
        pt_json *j = ok("\"\\u00bd and \\u221e\"");
        T_EQ_STR(pt_json_string(j, NULL), "\xC2\xBD and \xE2\x88\x9E",
                 "\\u escapes decode to UTF-8");
        pt_json_free(j);
    }
    {
        /* Surrogate pair for U+1D11E. */
        pt_json *j = ok("\"\\ud834\\udd1e\"");
        T_EQ_STR(pt_json_string(j, NULL), "\xF0\x9D\x84\x9E", "surrogate pair");
        pt_json_free(j);
    }
    {
        /* Raw UTF-8 passes through untouched — the repo's own filenames use it. */
        pt_json *j = ok("\"gaia_dr3_\xCF\x83""face\"");
        T_EQ_STR(pt_json_string(j, NULL), "gaia_dr3_\xCF\x83""face",
                 "raw UTF-8 is preserved");
        pt_json_free(j);
    }

    /* ── containers ────────────────────────────────────────────────────── */
    {
        pt_json *j = ok("[1, 2, 3]");
        T_EQ_INT(pt_json_count(j), 3, "array count");
        T_EQ_DBL(pt_json_number(pt_json_at(j, 1), 0), 2.0, "array index");
        T_OK(pt_json_at(j, 3) == NULL, "out-of-range index is NULL");
        T_OK(pt_json_at(j, -1) == NULL, "negative index is NULL");
        pt_json_free(j);
    }
    {
        pt_json *j = ok("{\"a\": 1, \"b\": {\"c\": \"d\"}}");
        T_EQ_INT(pt_json_count(j), 2, "object count");
        T_EQ_DBL(pt_json_number(pt_json_get(j, "a"), 0), 1.0, "object get");
        T_EQ_STR(pt_json_string(pt_json_get(pt_json_get(j, "b"), "c"), NULL),
                 "d", "nested get");
        T_OK(pt_json_get(j, "missing") == NULL, "missing key is NULL");
        T_EQ_STR(pt_json_key_at(j, 0), "a", "key by index");
        pt_json_free(j);
    }
    {
        pt_json *j = ok("{}");
        T_EQ_INT(pt_json_count(j), 0, "empty object");
        pt_json_free(j);
    }
    {
        pt_json *j = ok("[]");
        T_EQ_INT(pt_json_count(j), 0, "empty array");
        pt_json_free(j);
    }

    /* ── fallbacks let optional fields be read without branching ───────── */
    {
        pt_json *j = ok("{\"n\": \"not a number\"}");
        T_EQ_DBL(pt_json_number(pt_json_get(j, "n"), 7.0), 7.0,
                 "wrong type yields the fallback");
        T_EQ_DBL(pt_json_number(pt_json_get(j, "absent"), 7.0), 7.0,
                 "absent yields the fallback");
        T_EQ_STR(pt_json_string(NULL, "dflt"), "dflt", "NULL yields the fallback");
        pt_json_free(j);
    }

    /* ── whitespace and BOM ────────────────────────────────────────────── */
    {
        pt_json *j = ok("  \n\t {\n  \"k\" : \t 1 \n } \n ");
        T_EQ_DBL(pt_json_number(pt_json_get(j, "k"), 0), 1.0, "whitespace");
        pt_json_free(j);
    }
    {
        /* A researcher hand-editing a .ptorrent on Windows should not meet an
         * unexplained parse failure. */
        pt_json *j = ok("\xEF\xBB\xBF{\"k\":1}");
        T_EQ_DBL(pt_json_number(pt_json_get(j, "k"), 0), 1.0, "UTF-8 BOM tolerated");
        pt_json_free(j);
    }

    /* ── rejection ─────────────────────────────────────────────────────── */
    T_OK(rejects("{"),                  "unterminated object");
    T_OK(rejects("[1, 2"),              "unterminated array");
    T_OK(rejects("{\"a\" 1}"),          "missing colon");
    T_OK(rejects("{\"a\": 1,}"),        "trailing comma in object");
    T_OK(rejects("[1,]"),               "trailing comma in array");
    T_OK(rejects("{a: 1}"),             "unquoted key");
    T_OK(rejects("'single'"),           "single quotes");
    T_OK(rejects("01"),                 "leading zero");
    T_OK(rejects("1."),                 "trailing decimal point");
    T_OK(rejects(".5"),                 "bare leading dot");
    T_OK(rejects("1e"),                 "truncated exponent");
    T_OK(rejects("\"unterminated"),     "unterminated string");
    T_OK(rejects("\"\\ud834\""),        "lone high surrogate");
    T_OK(rejects("\"\\udd1e\""),        "lone low surrogate");
    T_OK(rejects("\"\\q\""),            "unknown escape");
    T_OK(rejects("{} {}"),              "trailing content");
    T_OK(rejects("nul"),                "truncated literal");
    T_OK(rejects(""),                   "empty input");

    /* A raw control character inside a string is invalid JSON. */
    T_OK(rejects("\"a\nb\""),           "raw newline in string");

    /* ── depth bomb ────────────────────────────────────────────────────── */
    {
        size_t n = 5000;
        char  *s = (char *)malloc(2 * n + 1);
        size_t i;
        for (i = 0; i < n; i++)     s[i] = '[';
        for (i = 0; i < n; i++)     s[n + i] = ']';
        s[2 * n] = '\0';
        T_OK(rejects(s), "5000-deep nesting is refused, not fatal");
        free(s);
    }

    /* ── error messages carry a location ───────────────────────────────── */
    {
        pt_json *j = NULL;
        char     eb[128];
        const char *src = "{\n  \"a\": 1,\n  \"b\" 2\n}";
        pt_json_parse(src, strlen(src), &j, eb, sizeof eb);
        T_OK(strstr(eb, "line 3") != NULL, "error reports the line (got: %s)", eb);
    }

    return pt_t_report();
}
