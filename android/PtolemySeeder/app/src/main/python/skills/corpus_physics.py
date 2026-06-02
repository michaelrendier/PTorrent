"""
skills/corpus_physics.py — Physics corpus for Holcus TDI engine.

Trains a dedicated Engine on wave mechanics, resonant cavities,
quantum mechanics, general relativity, cosmology, dark matter, and
the physics vocabulary underlying SMMIP and H_hat_RB.

Goal: Holcus can articulate Schumann resonances, BAO, spectral
theory, NFW profiles, and Yang-Mills mass gap as lived concepts,
not approximate synonyms of English words.

Checkpoint: ``~/.ptolemy/monad_physics.bin``
"""

import os
from typing import Optional

from monad import Engine
from skills.corpus import GenericCorpus

# Tags that receive weight 2.0 in physics_corpus.txt
_PHYSICS_PRIMARY_TAGS = {
    'FOUNDATIONS', 'WAVES', 'RESONANCE', 'QM', 'GR',
    'COSMOLOGY', 'DARKMATTER', 'YANGMILLS', 'SPECTRAL',
}

PHYSICS_BIN_PATH = os.path.expanduser('~/.ptolemy/monad_physics.bin')
PHYSICS_TXT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'code-corpora', 'physics_corpus.txt',
)


class PhysicsCorpus(GenericCorpus):
    """Autonomous Physics corpus.

    Parses ``code-corpora/physics_corpus.txt`` dynamically.
    One dedicated Engine — never feeds the primary monad field.

    :param engine: Dedicated Engine instance.
    :param txt_path: Path to ``physics_corpus.txt``.
    :param bin_path: Path for ``monad_physics.bin`` checkpoint.
    """

    def __init__(
        self,
        engine: Engine,
        txt_path: str = PHYSICS_TXT_PATH,
        bin_path: str = PHYSICS_BIN_PATH,
    ) -> None:
        super().__init__(
            engine,
            txt_path=txt_path,
            bin_path=bin_path,
            name='physics',
            interval=50,
            primary_tags=_PHYSICS_PRIMARY_TAGS,
            primary_weight=2.0,
            context_weight=1.0,
        )
