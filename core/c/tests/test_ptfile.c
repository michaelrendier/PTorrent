/*
 * test_ptfile.c — .ptorrent parsing and validation.
 *
 * The last section parses every real .ptorrent in the repository. Unit tests
 * prove the parser handles what was imagined; that section proves it handles
 * what was actually written.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ptorrent.h"
#include "pt_test.h"

static pt_ptfile *parse(const char *s)
{
    pt_ptfile *p  = NULL;
    char       eb[256];
    pt_err     rc = pt_ptfile_parse(s, strlen(s), &p, eb, sizeof eb);
    if (rc != PT_OK) printf("  (unexpected reject: %s)\n", eb);
    return p;
}

static int rejects(const char *s, const char *why)
{
    pt_ptfile *p  = NULL;
    pt_err     rc = pt_ptfile_parse(s, strlen(s), &p, NULL, 0);
    (void)why;
    if (rc == PT_OK) { pt_ptfile_free(p); return 0; }
    return 1;
}

static const char *CORPUS =
    "{\"ptorrent_version\":\"1.0\",\"type\":\"corpus\",\"name\":\"Quantum Field Theory\","
    "\"bin\":\"monad_qft.bin\",\"primary_tags\":[\"QFT\",\"YANGMILLS\"],"
    "\"color\":\"cyan\",\"description\":\"QFT vocabulary.\","
    "\"urls\":[{\"tag\":\"QFT\",\"url\":\"https://a.example/1\"},"
              "{\"tag\":\"YANGMILLS\",\"url\":\"https://a.example/2\"}]}";

static const char *EVAL =
    "{\"ptorrent_version\":\"1.1\",\"type\":\"evaluation\",\"name\":\"DESI BAO\","
    "\"primary_tags\":[\"DESI\"],\"color\":\"orange\",\"description\":\"BAO.\","
    "\"output\":\"desi_dr1_bao_face.peval\","
    "\"evaluation\":{\"j_expr\":\"D_M / r_drag\","
    "\"j_expr_cols\":[\"D_M\",\"r_drag\"],"
    "\"methodology\":\"Angular diameter distance over the sound horizon.\","
    "\"prediction\":\"Residual clusters at d*.\"}}";

int main(void)
{
    T_SUITE("ptfile");

    /* ── corpus ────────────────────────────────────────────────────────── */
    {
        pt_ptfile *p = parse(CORPUS);
        T_OK(p != NULL, "corpus parses");
        if (p) {
            T_EQ_INT(pt_ptfile_type(p), PT_JOB_CORPUS,          "type");
            T_EQ_STR(pt_ptfile_version(p), "1.0",               "version");
            T_EQ_STR(pt_ptfile_name(p), "Quantum Field Theory", "name");
            T_EQ_STR(pt_ptfile_bin(p), "monad_qft.bin",         "bin");
            T_EQ_STR(pt_ptfile_color(p), "cyan",                "color");
            T_EQ_INT(pt_ptfile_tag_count(p), 2,                 "tag count");
            T_EQ_STR(pt_ptfile_tag_at(p, 0), "QFT",             "first tag");
            T_EQ_INT(pt_ptfile_url_count(p), 2,                 "url count");
            T_EQ_STR(pt_ptfile_url_at(p, 0), "https://a.example/1", "first url");
            T_EQ_STR(pt_ptfile_url_tag_at(p, 1), "YANGMILLS",   "second url tag");
            T_EQ_INT(pt_ptfile_checkpoint_every(p), 10,         "checkpoint default is 10");
            T_EQ_STR(pt_ptfile_user_agent(p), "ptolemy",        "ua default");
            T_EQ_INT(pt_ptfile_has_evaluation(p), 0,            "no evaluation block");
            T_OK(pt_ptfile_url_at(p, 99) == NULL,               "out-of-range url is NULL");
            pt_ptfile_free(p);
        }
    }

    /* ── evaluation ────────────────────────────────────────────────────── */
    {
        pt_ptfile *p = parse(EVAL);
        T_OK(p != NULL, "evaluation parses");
        if (p) {
            T_EQ_INT(pt_ptfile_type(p), PT_JOB_EVALUATION, "type");
            T_EQ_INT(pt_ptfile_has_evaluation(p), 1,       "has evaluation");
            T_EQ_INT(pt_ptfile_j_method(p), PT_J_EXPR,     "method is j_expr");
            T_EQ_STR(pt_ptfile_j_expr(p), "D_M / r_drag",  "j_expr");
            T_EQ_INT(pt_ptfile_j_expr_col_count(p), 2,     "declared column count");

            /* The declared columns and the compiled expression agree here. */
            {
                const char *cols[8];
                int n = pt_ptfile_required_columns(p, cols, 8);
                T_EQ_INT(n, 2, "required columns");
                T_EQ_STR(cols[0], "D_M",    "column 0");
                T_EQ_STR(cols[1], "r_drag", "column 1");
            }

            /* End to end: the file's own expression against a row. */
            {
                pt_bindings *b = pt_bindings_new();
                pt_jexpr    *e = NULL;
                double       j = 0.0;
                /* 600/147.09 = 4.079, which sits between 1/d* and 1/d*+Omega. */
                pt_bindings_set(b, "D_M",     600.0);
                pt_bindings_set(b, "r_drag",  147.09);
                T_EQ_INT(pt_jexpr_compile(pt_ptfile_j_expr(p), &e, NULL, 0), PT_OK,
                         "the file's j_expr compiles");
                T_EQ_INT(pt_jexpr_eval(e, b, &j), PT_OK, "evaluates");
                T_EQ_DBL(j, 600.0 / 147.09, "J value");
                T_EQ_INT(pt_sigma_classify(j), PT_SIGMA_TWO, "classifies as gravity");

                /* A larger distance ratio leaves the band entirely. */
                pt_bindings_set(b, "D_M", 1500.0);
                pt_jexpr_eval(e, b, &j);
                T_EQ_INT(pt_sigma_classify(j), PT_SIGMA_INF, "10.2 is above the top band");
                pt_jexpr_free(e);
                pt_bindings_free(b);
            }
            pt_ptfile_free(p);
        }
    }

    /* ── J-method priority order ───────────────────────────────────────── */
    {
        /* j_col outranks j_expr even when both are present (spec order). */
        const char *both =
            "{\"ptorrent_version\":\"1.1\",\"type\":\"evaluation\",\"name\":\"x\","
            "\"evaluation\":{\"j_col\":\"ratio\",\"j_expr\":\"a / b\"}}";
        pt_ptfile *p = parse(both);
        if (p) {
            T_EQ_INT(pt_ptfile_j_method(p), PT_J_COL, "j_col outranks j_expr");
            pt_ptfile_free(p);
        }
    }
    {
        const char *nd =
            "{\"ptorrent_version\":\"1.1\",\"type\":\"evaluation\",\"name\":\"x\","
            "\"evaluation\":{\"j_num_col\":\"n\",\"j_den_col\":\"d\",\"fn\":\"z\"}}";
        pt_ptfile *p = parse(nd);
        if (p) {
            T_EQ_INT(pt_ptfile_j_method(p), PT_J_NUM_DEN, "num/den outranks fn");
            {
                const char *cols[8];
                int n = pt_ptfile_required_columns(p, cols, 8);
                T_EQ_INT(n, 2, "num/den contributes two columns");
            }
            pt_ptfile_free(p);
        }
    }
    {
        const char *fnonly =
            "{\"ptorrent_version\":\"1.1\",\"type\":\"evaluation\",\"name\":\"x\","
            "\"evaluation\":{\"fn\":\"sigma_face_bao_residual\"}}";
        pt_ptfile *p = parse(fnonly);
        if (p) {
            T_EQ_INT(pt_ptfile_j_method(p), PT_J_FN, "fn is last but valid");
            pt_ptfile_free(p);
        }
    }

    /* ── security and embargo ──────────────────────────────────────────── */
    {
        const char *sec =
            "{\"ptorrent_version\":\"1.0\",\"type\":\"dataset\",\"name\":\"s\","
            "\"security\":{\"classification\":\"dual-use\",\"level\":3,"
            "\"embargo_until\":\"2027-06-03\",\"acknowledge_required\":true,"
            "\"warning\":\"Handle with care.\"}}";
        pt_ptfile *p = parse(sec);
        T_OK(p != NULL, "security block parses");
        if (p) {
            T_EQ_INT(pt_ptfile_security_level(p), 3, "level");
            T_EQ_STR(pt_ptfile_security_classification(p), "dual-use", "classification");
            T_EQ_INT(pt_ptfile_security_acknowledge_required(p), 1, "acknowledge");
            T_EQ_STR(pt_ptfile_security_embargo_until(p), "2027-06-03", "embargo date");

            T_EQ_INT(pt_ptfile_embargoed(p, "2026-08-17"), 1, "before the date: blocked");
            T_EQ_INT(pt_ptfile_embargoed(p, "2027-06-02"), 1, "day before: blocked");
            T_EQ_INT(pt_ptfile_embargoed(p, "2027-06-03"), 0, "on the date: permitted");
            T_EQ_INT(pt_ptfile_embargoed(p, "2027-06-04"), 0, "after: permitted");

            /* Fail closed: an unreadable date is not permission. */
            T_EQ_INT(pt_ptfile_embargoed(p, "not-a-date"), 1, "malformed today: blocked");
            T_EQ_INT(pt_ptfile_embargoed(p, NULL),         1, "missing today: blocked");
            T_EQ_INT(pt_ptfile_embargoed(p, "2027-6-3"),   1, "non-ISO today: blocked");
            pt_ptfile_free(p);
        }
    }
    {
        /* No security block at all means level 0 and no embargo. */
        pt_ptfile *p = parse(CORPUS);
        if (p) {
            T_EQ_INT(pt_ptfile_security_level(p), 0, "absent security is level 0");
            T_EQ_INT(pt_ptfile_embargoed(p, "2020-01-01"), 0, "no embargo declared");
            pt_ptfile_free(p);
        }
    }

    /* ── unknown fields survive ────────────────────────────────────────── */
    {
        const char *future =
            "{\"ptorrent_version\":\"1.2\",\"type\":\"dataset\",\"name\":\"f\","
            "\"a_field_from_the_future\":{\"nested\":[1,2,3]}}";
        pt_ptfile *p = parse(future);
        T_OK(p != NULL, "a newer file still parses");
        if (p) {
            const pt_json *x = pt_json_get(pt_ptfile_json(p), "a_field_from_the_future");
            T_OK(x != NULL, "unmodelled fields are retained, not stripped");
            pt_ptfile_free(p);
        }
    }

    /* ── rejection ─────────────────────────────────────────────────────── */
    T_OK(rejects("{\"type\":\"corpus\",\"name\":\"x\",\"bin\":\"b\"}", ""),
         "missing ptorrent_version is rejected");
    T_OK(rejects("{\"ptorrent_version\":\"1.0\",\"name\":\"x\"}", ""),
         "missing type is rejected");
    T_OK(rejects("{\"ptorrent_version\":\"1.0\",\"type\":\"corpus\"}", ""),
         "missing name is rejected");
    T_OK(rejects("{\"ptorrent_version\":\"1.0\",\"type\":\"wat\",\"name\":\"x\"}", ""),
         "unknown type is rejected");
    T_OK(rejects("[1,2,3]", ""), "a non-object top level is rejected");

    /* The spec's own silent-failure case, made loud. */
    T_OK(rejects("{\"ptorrent_version\":\"1.0\",\"type\":\"corpus\",\"name\":\"x\","
                 "\"bin\":\"b.bin\"}", ""),
         "a corpus with neither txt nor urls is rejected, not silently empty");
    T_OK(rejects("{\"ptorrent_version\":\"1.0\",\"type\":\"corpus\",\"name\":\"x\","
                 "\"bin\":\"b.bin\",\"urls\":[]}", ""),
         "a corpus with an empty urls array is rejected");
    T_OK(rejects("{\"ptorrent_version\":\"1.0\",\"type\":\"corpus\",\"name\":\"x\","
                 "\"txt\":\"list.txt\"}", ""),
         "a corpus without bin is rejected");
    T_OK(rejects("{\"ptorrent_version\":\"1.1\",\"type\":\"evaluation\",\"name\":\"x\","
                 "\"evaluation\":{\"methodology\":\"prose only\"}}", ""),
         "an evaluation with no J method is rejected");
    T_OK(rejects("{\"ptorrent_version\":\"1.1\",\"type\":\"evaluation\",\"name\":\"x\"}", ""),
         "an evaluation with no evaluation block is rejected");

    /* A corpus declaring txt (rather than urls) is valid. */
    {
        pt_ptfile *p = parse("{\"ptorrent_version\":\"1.0\",\"type\":\"corpus\","
                             "\"name\":\"x\",\"bin\":\"b.bin\",\"txt\":\"list.txt\"}");
        T_OK(p != NULL, "a corpus with txt and no urls is valid");
        pt_ptfile_free(p);
    }

    /* ── every real .ptorrent in the repository ────────────────────────── */
    {
        static const char *names[] = {
            "allsky_2mass_\317\203face", "bullet_cluster_alldata",
            "bullet_cluster_bec", "c_posix", "desi_dr1_bao_\317\203face",
            "eht_m87_\317\203face", "english_complete", "fermat",
            "foundations", "framenet", "gaia_dr3_\317\203face",
            "jwst_nirspec_\317\203face", "mathematics", "meaning",
            "physics", "planck_cmb_\317\203face", "python", "riemann_zeros",
            "seti_breakthrough_\317\203face", "vera_rubin_\317\203face",
            "wmap_cmb_\317\203face"
        };
        int i, found = 0, ok = 0, evals = 0, exprs = 0;

        for (i = 0; i < (int)(sizeof(names) / sizeof(names[0])); i++) {
            char       path[512];
            char       eb[256];
            pt_ptfile *p  = NULL;
            pt_err     rc;

            snprintf(path, sizeof path, "../../ptorrents/%s.ptorrent", names[i]);
            rc = pt_ptfile_load(path, &p, eb, sizeof eb);

            if (rc == PT_E_IO) continue;      /* run from elsewhere; skip */
            found++;

            if (rc != PT_OK) {
                printf("  \033[31mREJECT\033[0m %s.ptorrent: %s\n", names[i], eb);
                continue;
            }
            ok++;

            if (pt_ptfile_has_evaluation(p)) {
                evals++;
                /* Every real j_expr in the repository must compile. */
                if (pt_ptfile_j_method(p) == PT_J_EXPR) {
                    pt_jexpr *e = NULL;
                    char      xb[256];
                    exprs++;
                    if (pt_jexpr_compile(pt_ptfile_j_expr(p), &e, xb, sizeof xb) != PT_OK) {
                        printf("  \033[31mBAD j_expr\033[0m %s: \"%s\" -- %s\n",
                               names[i], pt_ptfile_j_expr(p), xb);
                        pt_t_fail++;
                    } else {
                        pt_t_pass++;
                        pt_jexpr_free(e);
                    }
                }
            }
            pt_ptfile_free(p);
        }

        if (found == 0) {
            printf("  (repository .ptorrent files not reachable from here; skipped)\n");
        } else {
            T_EQ_INT(ok, found, "every repository .ptorrent parses");
            printf("  parsed %d files: %d evaluations, %d with a j_expr\n",
                   ok, evals, exprs);
        }
    }

    return pt_t_report();
}
