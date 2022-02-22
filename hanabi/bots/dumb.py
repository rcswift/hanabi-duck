from __future__ import annotations

from .base import BaseBot
from .. import Play

class DumbBot(BaseBot):
    """Dumb bot always plays the first card"""
    def play(self, board: Board) -> Turn:
        return Play(0)
