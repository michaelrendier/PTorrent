"""
skills/corpus_mathematics.py — Mathematics corpus for Holcus TDI engine.

Trains a dedicated Engine on number theory, the Riemann zeta function,
spectral theory, modular forms, harmonic analysis, and the mathematical
vocabulary underlying H_hat_RB and the Clay Millennium Problems.

Goal: Holcus can articulate Euler products, GUE eigenvalue statistics,
Lambert W fixed points, Selberg class, and Leech lattice as lived
concepts — not just English approximations.

Checkpoint: ``~/.ptolemy/monad_mathematics.bin``
"""

import os
from typing import Optional

from monad import Engine
from skills.corpus import GenericCorpus

# Tags that receive weight 2.0 in mathematics_corpus.txt
_MATHEMATICS_PRIMARY_TAGS = {
    'NUMBERTHEORY', 'RIEMANN', 'SPECTRAL', 'MODULAR',
    'PRIMES', 'CLAY', 'HARMONIC',
}

MATHEMATICS_BIN_PATH = os.path.expanduser('~/.ptolemy/monad_mathematics.bin')
MATHEMATICS_TXT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'code-corpora', 'mathematics_corpus.txt',
)


class MathematicsCorpus(GenericCorpus):
    """Autonomous Mathematics corpus.

    Parses ``code-corpora/mathematics_corpus.txt`` dynamically.
    One dedicated Engine — never feeds the primary monad field.

    :param engine: Dedicated Engine instance.
    :param txt_path: Path to ``mathematics_corpus.txt``.
    :param bin_path: Path for ``monad_mathematics.bin`` checkpoint.
    """

    def __init__(
        self,
        engine: Engine,
        txt_path: str = MATHEMATICS_TXT_PATH,
        bin_path: str = MATHEMATICS_BIN_PATH,
    ) -> None:
        super().__init__(
            engine,
            txt_path=txt_path,
            bin_path=bin_path,
            name='mathematics',
            interval=50,
            primary_tags=_MATHEMATICS_PRIMARY_TAGS,
            primary_weight=2.0,
            context_weight=1.0,
        )
