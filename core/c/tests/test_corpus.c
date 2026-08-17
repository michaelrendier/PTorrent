/*
 * test_corpus.c — the [TAG] URL list, and the traversal discipline.
 *
 * Two load-bearing properties under test.
 *
 * NOTHING IS DROPPED. Every source line becomes a record, whatever its state.
 *
 * THE INDEX INVARIANT: for every index i, the cursor and the modifier denote
 * the same record. It is a relation between the two objects and it holds
 * across every state of a traversal — which is what makes an index worth
 * passing between them.
 *
 * The invariant is scoped to one index space, not to all time. The list is
 * variable; re-reading a changed source renumbers it, legitimately. So the
 * space is identified, the modifier binds to the one it accumulated in, and
 * a cross-space index is refused instead of resolved. An invariant that is
 * only written down is a hope.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ptorrent.h"
#include "pt_test.h"

static pt_corpus *parse(const char *s)
{
    pt_corpus *c  = NULL;
    char       eb[256];
    pt_err     rc = pt_corpus_parse(s, strlen(s), &c, eb, sizeof eb);
    if (rc != PT_OK) printf("  (unexpected reject: %s)\n", eb);
    return c;
}

static const char *MIXED =
    "# HOLCUS PHYSICS CORPUS\n"          /* 1 ignored   */
    "\n"                                 /* 2 ignored   */
    "[WAVES] https://a.example/wave\n"   /* 3 ok        */
    "https://a.example/no-tag\n"         /* 4 malformed */
    "[QM]    https://a.example/qm\n"     /* 5 ok        */
    "[UNCLOSED https://a.example/x\n"    /* 6 malformed */
    "[GR]\thttps://a.example/gr\n";      /* 7 ok        */

int main(void)
{
    T_SUITE("corpus");

    /* ── one record per line, always ───────────────────────────────────── */
    {
        pt_corpus *c = parse(MIXED);
        T_OK(c != NULL, "parses");
        if (c) {
            T_EQ_INT(pt_corpus_count(c), 7, "seven lines in, seven records out");
            T_EQ_INT(pt_corpus_count_status(c, PT_ITEM_OK),        3, "three usable");
            T_EQ_INT(pt_corpus_count_status(c, PT_ITEM_IGNORED),   2, "two ignored");
            T_EQ_INT(pt_corpus_count_status(c, PT_ITEM_MALFORMED), 2, "two malformed");

            /* Index resolves to a line, and no pass moves it. */
            T_EQ_INT(pt_corpus_line_at(c, 0), 1, "record 0 is line 1");
            T_EQ_INT(pt_corpus_line_at(c, 3), 4, "record 3 is line 4");
            T_EQ_INT(pt_corpus_line_at(c, 6), 7, "record 6 is line 7");

            T_EQ_INT(pt_corpus_status_at(c, 2), PT_ITEM_OK,        "line 3 is ok");
            T_EQ_STR(pt_corpus_url_at(c, 2), "https://a.example/wave", "its url");
            T_EQ_STR(pt_corpus_tag_at(c, 2), "WAVES",                  "its tag");

            /* A malformed line is a record you can print, not a tally. */
            T_EQ_INT(pt_corpus_status_at(c, 3), PT_ITEM_MALFORMED, "line 4 malformed");
            T_EQ_STR(pt_corpus_raw_at(c, 3), "https://a.example/no-tag",
                     "the original text is retained and printable");
            T_OK(pt_corpus_url_at(c, 3) == NULL, "malformed carries no url");

            /* Even ignored lines keep their text. */
            T_EQ_STR(pt_corpus_raw_at(c, 0), "# HOLCUS PHYSICS CORPUS",
                     "comments are retained too");
            pt_corpus_free(c);
        }
    }

    /* ── the cursor reports; it does not filter ────────────────────────── */
    {
        pt_corpus *c   = parse(MIXED);
        pt_cursor *cur = pt_corpus_cursor(c);
        int seen = 0, ok = 0;

        while (pt_cursor_next(cur)) {
            /* index and line stay locked together during traversal */
            T_EQ_INT(pt_cursor_index(cur), seen, "cursor index advances by one");
            T_EQ_INT(pt_cursor_line(cur), seen + 1, "and tracks the source line");
            if (pt_cursor_status(cur) == PT_ITEM_OK) ok++;
            seen++;
        }

        T_EQ_INT(seen, 7, "the cursor visits every record, not just usable ones");
        T_EQ_INT(ok,   3, "three were usable");

        pt_cursor_reset(cur);
        T_EQ_INT(pt_cursor_index(cur), -1, "reset returns to before the first");
        T_OK(pt_cursor_next(cur) == 1, "and can walk again");
        T_EQ_INT(pt_cursor_index(cur), 0, "from record 0");

        pt_cursor_free(cur);
        pt_corpus_free(c);
    }

    /* ── dedup is a separate object, and leaves the index alone ────────── */
    {
        pt_corpus *c = parse(
            "[A] https://a.example/x\n"
            "[B] https://a.example/y\n"
            "[C] https://a.example/x\n"
            "[D] https://a.example/x\n");
        pt_cursor *cur = pt_corpus_cursor(c);
        pt_dedup  *d   = pt_dedup_new();
        int fetched = 0;

        while (pt_cursor_next(cur)) {
            int first;
            if (pt_cursor_status(cur) != PT_ITEM_OK) continue;

            first = pt_dedup_observe_at(d, cur, pt_cursor_url(cur));
            if (first >= 0) {
                /* The two objects agree on what an index means: the modifier
                 * hands back a number the corpus can resolve directly. */
                T_EQ_STR(pt_corpus_url_at(c, first), pt_cursor_url(cur),
                         "record %d resolves to the same url the modifier matched",
                         first);
                T_EQ_INT(first, 0, "both repeats point back at record 0");
                continue;
            }
            fetched++;
        }

        T_EQ_INT(fetched, 2,             "two distinct urls would be fetched");
        T_EQ_INT(pt_dedup_unique(d),  2, "two unique keys");
        T_EQ_INT(pt_dedup_repeats(d), 2, "two repeats");

        /* The corpus is untouched by the modifier — this is the whole point. */
        T_EQ_INT(pt_corpus_count(c), 4, "the list is still reported as written");
        T_EQ_INT(pt_corpus_line_at(c, 3), 4, "record 3 is still line 4");
        T_EQ_STR(pt_corpus_url_at(c, 3), "https://a.example/x",
                 "and still holds its url");

        /* Second pass over the same corpus yields identical indices. */
        {
            pt_cursor *c2 = pt_corpus_cursor(c);
            int i = 0;
            while (pt_cursor_next(c2)) {
                T_EQ_INT(pt_cursor_line(c2), pt_corpus_line_at(c, i),
                         "pass two sees the same line at index %d", i);
                i++;
            }
            pt_cursor_free(c2);
        }

        pt_dedup_free(d);
        pt_cursor_free(cur);
        pt_corpus_free(c);
    }

    /* ── the invariant, checked rather than assumed ────────────────────── */
    {
        /* Two parses of identical text are two index spaces. The text being
         * the same is not the point — the list is variable, and the modifier
         * cannot know whether this read matches the one it accumulated. */
        const char *src = "[A] https://a.example/x\n[B] https://a.example/y\n";
        pt_corpus  *c1  = parse(src);
        pt_corpus  *c2  = parse(src);
        pt_cursor  *k1  = pt_corpus_cursor(c1);
        pt_cursor  *k2  = pt_corpus_cursor(c2);
        pt_dedup   *d   = pt_dedup_new();

        T_OK(pt_corpus_id(c1) != pt_corpus_id(c2),
             "two parses are two distinct index spaces");
        T_OK(pt_corpus_id(c1) != 0, "a parsed corpus has a non-zero space id");
        T_EQ_INT(pt_dedup_space(d), 0, "a fresh modifier is bound to nothing");

        pt_cursor_next(k1);
        T_EQ_INT(pt_dedup_observe_at(d, k1, "https://a.example/x"),
                 PT_INDEX_NONE, "first observation in space 1");
        T_OK(pt_dedup_space(d) == pt_corpus_id(c1),
             "the modifier bound itself to the space it was used with");

        /* Same key, same index number, different list. Answering would hand
         * back a record number that means something else. */
        pt_cursor_next(k2);
        T_EQ_INT(pt_dedup_observe_at(d, k2, "https://a.example/x"),
                 PT_INDEX_MISMATCH,
                 "an index from another space is refused, not resolved");

        /* Still usable in its own space. */
        pt_cursor_next(k1);
        T_EQ_INT(pt_dedup_observe_at(d, k1, "https://a.example/x"), 0,
                 "and the original space still resolves to record 0");

        /* Reset unbinds, so the object can be reused for the next list. */
        pt_dedup_reset(d);
        T_EQ_INT(pt_dedup_space(d), 0, "reset releases the binding");
        T_EQ_INT(pt_dedup_observe_at(d, k2, "https://a.example/x"),
                 PT_INDEX_NONE, "and it rebinds to the new space");
        T_OK(pt_dedup_space(d) == pt_corpus_id(c2), "now bound to space 2");

        /* Space 0 means "one unnamed space" and disables the check — for
         * sequences that are not a corpus. */
        {
            pt_dedup *raw = pt_dedup_new();
            T_EQ_INT(pt_dedup_observe(raw, 0, "row-7", 7), PT_INDEX_NONE, "raw new");
            T_EQ_INT(pt_dedup_observe(raw, 0, "row-7", 9), 7,
                     "raw repeat resolves to the first index");
            pt_dedup_free(raw);
        }

        pt_dedup_free(d);
        pt_cursor_free(k1);
        pt_cursor_free(k2);
        pt_corpus_free(c1);
        pt_corpus_free(c2);
    }

    /* ── tags the Python reference silently drops ──────────────────────── */
    {
        pt_corpus *c = parse(
            "[DARK_MATTER] https://a.example/1\n"
            "[H2O] https://a.example/2\n"
            "[lowercase] https://a.example/3\n");
        if (c) {
            T_EQ_INT(pt_corpus_count_status(c, PT_ITEM_OK), 3,
                     "underscored, numeric and lowercase tags all parse");
            T_EQ_STR(pt_corpus_tag_at(c, 0), "DARK_MATTER", "underscore kept");
            T_EQ_STR(pt_corpus_tag_at(c, 1), "H2O",         "digit kept");
            pt_corpus_free(c);
        }
    }

    /* ── edge cases ────────────────────────────────────────────────────── */
    {
        pt_corpus *c = parse("\xEF\xBB\xBF[A] https://a.example/1\n");
        T_OK(c && pt_corpus_count_status(c, PT_ITEM_OK) == 1, "UTF-8 BOM tolerated");
        pt_corpus_free(c);
    }
    {
        pt_corpus *c = parse("[A] https://a.example/1");
        T_OK(c && pt_corpus_count(c) == 1, "final line without newline");
        pt_corpus_free(c);
    }
    {
        pt_corpus *c = parse("[A] https://a.example/1\r\n[B] https://a.example/2\r\n");
        if (c) {
            T_EQ_INT(pt_corpus_count(c), 2, "CRLF line endings");
            T_EQ_STR(pt_corpus_url_at(c, 0), "https://a.example/1", "CR stripped from url");
            T_EQ_STR(pt_corpus_raw_at(c, 0), "[A] https://a.example/1", "and from raw");
            pt_corpus_free(c);
        }
    }
    {
        pt_corpus *c = parse("[FTP] ftp://a.example/1\n[A] https://a.example/2\n");
        if (c) {
            T_EQ_INT(pt_corpus_status_at(c, 0), PT_ITEM_MALFORMED,
                     "a non-HTTP scheme is malformed, not silently tried");
            pt_corpus_free(c);
        }
    }
    {
        pt_corpus *c  = NULL;
        pt_err rc = pt_corpus_parse("# only comments\n\n", 17, &c, NULL, 0);
        T_EQ_INT(rc, PT_E_PARSE, "a list with no usable entries is an error");
        T_OK(c == NULL, "and yields no handle");
    }
    {
        pt_corpus *c  = NULL;
        pt_err     rc = pt_corpus_load("/nonexistent/corpus.txt", &c, NULL, 0);
        T_EQ_INT(rc, PT_E_IO, "a missing list is an error, not an empty list");
        T_OK(c == NULL, "and yields no handle");
    }

    /* ── weighting comes from the .ptorrent, not the list ──────────────── */
    {
        const char *pj =
            "{\"ptorrent_version\":\"1.0\",\"type\":\"corpus\",\"name\":\"p\","
            "\"bin\":\"monad_physics.bin\",\"txt\":\"physics_corpus.txt\","
            "\"primary_tags\":[\"WAVES\",\"QM\"],\"primary_weight\":2.0,"
            "\"context_weight\":1.0}";
        pt_ptfile *p = NULL;
        pt_ptfile_parse(pj, strlen(pj), &p, NULL, 0);
        T_OK(p != NULL, "corpus ptorrent with txt parses");
        if (p) {
            T_EQ_DBL(pt_corpus_weight_for_tag(p, "WAVES"),   2.0, "primary tag");
            T_EQ_DBL(pt_corpus_weight_for_tag(p, "CONTEXT"), 1.0, "context tag");
            T_EQ_DBL(pt_corpus_weight_for_tag(p, NULL),      1.0, "no tag");
            pt_ptfile_free(p);
        }
    }

    /* ── every real corpus list in the repository ──────────────────────── */
    {
        static const char *lists[] = {
            "c_corpus.txt", "english_corpus.txt", "mathematics_corpus.txt",
            "physics_corpus.txt", "python_corpus.txt", "war_corpus.txt",
            "meaning.txt", "foundations.txt"
        };
        const char *dir = "../../android/PtolemySeeder/app/src/main/assets/";
        int i, found = 0, lines = 0, urls = 0, bad = 0, dups = 0;

        for (i = 0; i < (int)(sizeof(lists) / sizeof(lists[0])); i++) {
            char        path[512];
            char        eb[256];
            pt_corpus  *c = NULL;
            pt_cursor  *cur;
            pt_dedup   *d;
            pt_err      rc;
            int         fdup = 0, fbad = 0;

            snprintf(path, sizeof path, "%s%s", dir, lists[i]);
            rc = pt_corpus_load(path, &c, eb, sizeof eb);
            if (rc == PT_E_IO) continue;
            found++;

            if (rc != PT_OK) {
                printf("  \033[31mREJECT\033[0m %s: %s\n", lists[i], eb);
                pt_t_fail++;
                continue;
            }
            pt_t_pass++;

            cur = pt_corpus_cursor(c);
            d   = pt_dedup_new();
            while (pt_cursor_next(cur)) {
                switch (pt_cursor_status(cur)) {
                case PT_ITEM_OK:
                    if (pt_dedup_observe_at(d, cur, pt_cursor_url(cur)) >= 0) fdup++;
                    break;
                case PT_ITEM_MALFORMED:
                    fbad++;
                    printf("  \033[33mMALFORMED\033[0m %s:%ld  %s\n",
                           lists[i], pt_cursor_line(cur), pt_cursor_raw(cur));
                    break;
                case PT_ITEM_IGNORED:
                    break;
                }
            }

            /* Every record is accounted for — nothing fell out. */
            T_EQ_INT(pt_corpus_count_status(c, PT_ITEM_OK)
                   + pt_corpus_count_status(c, PT_ITEM_IGNORED)
                   + pt_corpus_count_status(c, PT_ITEM_MALFORMED),
                     pt_corpus_count(c),
                     "%s: statuses account for every record", lists[i]);

            lines += pt_corpus_count(c);
            urls  += pt_corpus_count_status(c, PT_ITEM_OK);
            bad   += fbad;
            dups  += fdup;

            pt_dedup_free(d);
            pt_cursor_free(cur);
            pt_corpus_free(c);
        }

        if (found == 0) {
            printf("  (repository corpus lists not reachable from here; skipped)\n");
        } else {
            printf("  %d lists: %d lines, %d urls, %d malformed, %d duplicate\n",
                   found, lines, urls, bad, dups);
        }
    }

    return pt_t_report();
}
