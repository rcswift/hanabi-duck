from __future__ import annotations

from hanabi import Board, Clue, Discard, Play

class BaseBot():
    def __init__(self):
        pass

    def play(self, board: Board) -> Turn:
        raise NotImplemented

    def reset(self):
        pass

    # Common helper functions
    @staticmethod
    def is_playable(card: Card, board: Board):
        return board.played_cards[card.color] == card.number - 1

class DumbBot(BaseBot):
    """Dumb bot always plays the first card"""
    def play(self, board: Board) -> Turn:
        return Play(0)

class BasicCheatingBot(BaseBot):
    """
    Cheating bot looks at its hand and plays the last playable cards.
    Otherwise clues or discards unnecessarily depending on the number of available clues.

    Its main problem is discarding 5s from the initial deal
    """
    def play(self, board: Board) -> Turn:
        hand = board._hands[board.current_player()]
        for i, card in zip(range(board.my_hand_size() - 1, -1, -1), reversed(hand)):

            if self.is_playable(card, board):
                return Play(i)
        if board.clues == 0:
            return Discard(board.my_hand_size() - 1)
        else:
            return Clue(target=1, color="r") # Clue the next player red
