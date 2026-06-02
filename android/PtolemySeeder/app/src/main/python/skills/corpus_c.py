"""
skills/corpus_c.py — C language / POSIX corpus for Holcus.

Trains a dedicated Engine on C language specification (cppreference),
POSIX pthread/socket/file API, Linux man pages, GCC extensions,
and the Python/C API bridge.

Goal: when ptolemy -I ingests monad.c and PtolC/*.c, the field
already holds C-specific resonance — undefined behavior, struct layout,
pointer semantics, pthread_mutex, fread, PTOL binary format — as
language-level concepts at the C implementation depth.

Checkpoint: ``~/.ptolemy/monad_c.bin``
"""

import os

from monad import Engine
from skills.corpus import GenericCorpus

# Tags that receive weight 2.0 in c_corpus.txt
_C_PRIMARY_TAGS = {
    'SPEC', 'POSIX', 'CAPI',
}

C_BIN_PATH = os.path.expanduser('~/.ptolemy/monad_c.bin')
C_TXT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'code-corpora', 'c_corpus.txt',
)


class CCorpus(GenericCorpus):
    """Autonomous C language / POSIX corpus.

    Parses ``code-corpora/c_corpus.txt`` dynamically.
    One dedicated Engine — never feeds the primary monad field.

    Kept strictly C — no C++ vocabulary.
    The Python/C API section covers the bridge between this corpus
    and the Python corpus without conflating the two languages.

    :param engine: Dedicated Engine instance.
    :param txt_path: Path to ``c_corpus.txt``.
    :param bin_path: Path for ``monad_c.bin`` checkpoint.
    """

    def __init__(
        self,
        engine: Engine,
        txt_path: str = C_TXT_PATH,
        bin_path: str = C_BIN_PATH,
    ) -> None:
        super().__init__(
            engine,
            txt_path=txt_path,
            bin_path=bin_path,
            name='c',
            interval=55,
            primary_tags=_C_PRIMARY_TAGS,
            primary_weight=2.0,
            context_weight=1.0,
        )
