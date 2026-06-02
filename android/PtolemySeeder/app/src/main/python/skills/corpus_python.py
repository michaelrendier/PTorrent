"""
skills/corpus_python.py — Python language corpus for Holcus.

Trains a dedicated Engine on Python language specification, PEPs,
stdlib docs for modules used in monad.py, and the Python/C API.

Goal: when ptolemy -I ingests monad.py, the field already holds
Python-specific resonance — generator, descriptor, __slots__, MRO,
GIL, refcount — as language-level concepts, not just English words.

Checkpoint: ``~/.ptolemy/monad_python.bin``
"""

import os
from typing import Optional

from monad import Engine
from skills.corpus import GenericCorpus

# Tags that receive weight 2.0 in python_corpus.txt
_PYTHON_PRIMARY_TAGS = {
    'DATAMODEL', 'REFERENCE', 'PEP', 'WHATSNEW', 'API',
}

PYTHON_BIN_PATH = os.path.expanduser('~/.ptolemy/monad_python.bin')
PYTHON_TXT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'code-corpora', 'python_corpus.txt',
)


class PythonCorpus(GenericCorpus):
    """Autonomous Python language corpus.

    Parses ``code-corpora/python_corpus.txt`` dynamically.
    One dedicated Engine — never feeds the primary monad field.

    :param engine: Dedicated Engine instance.
    :param txt_path: Path to ``python_corpus.txt``.
    :param bin_path: Path for ``monad_python.bin`` checkpoint.
    """

    def __init__(
        self,
        engine: Engine,
        txt_path: str = PYTHON_TXT_PATH,
        bin_path: str = PYTHON_BIN_PATH,
    ) -> None:
        super().__init__(
            engine,
            txt_path=txt_path,
            bin_path=bin_path,
            name='python',
            interval=50,
            primary_tags=_PYTHON_PRIMARY_TAGS,
            primary_weight=2.0,
            context_weight=1.0,
        )
