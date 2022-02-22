from __future__ import annotations

class BaseBot():
    def __init__(self):
        self.reset()

    def reset(self):
        """Executed once at the start of the game"""
        pass

    def play(self, board: Board) -> Turn:
        """Executed on my turn"""
        raise NotImplemented
