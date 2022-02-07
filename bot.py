from __future__ import annotations

from hanabi import Board, Play

class BaseBot():
    def __init__(self):
        pass

    def play(self, board: Board) -> Turn:
        raise NotImplemented

    def reset(self):
        pass


class DumbBot(BaseBot):
    def play(self, board: Board) -> Turn:
        return Play(0)
