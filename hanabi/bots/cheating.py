from __future__ import annotations
import logging

from .base import BaseBot
from .. import Clue, Discard, Play

class BasicCheatingBot(BaseBot):
    """
    Cheating bot looks at its hand and plays the last playable cards.
    Otherwise clues or discards unnecessarily depending on the number of available clues.

    Its main problem is discarding 5s from the initial deal
    """
    def play(self, board: Board) -> Turn:
        hand = board._hands[board.current_player]
        for i, card in zip(range(board.current_hand_size - 1, -1, -1), reversed(hand)):

            if board.is_playable(card):
                return Play(i)
        if board.clues == 0:
            return Discard(board.current_hand_size - 1)
        else:
            return Clue(target=board.relative_player(1), color="r") # Clue the next player red

class CheatingBot(BaseBot):
    """
    Improves on BasicCheatingBot by looking at the card it's going to discard and picking safe discards
    Its weakness is probably getting unlucky with draws and running out of turns
    """
    def play(self, board: Board) -> Turn:
        hand = board._hands[board.current_player]

        # Play any playable cards. Neither ascending or descending order seem to help
        for i, card in enumerate(hand):
            if board.is_playable(card):
                return Play(i)

        # Clue if we're close to max clues
        if board.clues > 6:
            return Clue(target=board.relative_player(1), color="r")

        # Discard if we have freely discardable cards
        for i, card in enumerate(hand):
            if board.is_discardable(card):
                return Discard(i)

        # Clue if we have clues left
        if board.clues > 0:
            return Clue(target=board.relative_player(1), color="r")

        # Discard any cards that don't need to be saved
        hand.sort(key=lambda x: x.number, reverse=True) # this discards 4 > 3 > 2, but barely helps
        for i, card in enumerate(hand):
            if not board.is_unique(card):
                return Discard(i)

        # Last resort, discard
        logging.warning("If this happens, the bot needs to be more sophisticated and take turn order into account")
        return Discard(0)
