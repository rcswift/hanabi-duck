from __future__ import annotations
import logging

from hanabi import Board, Clue, Discard, Play

class BaseBot():
    def __init__(self, board: Board, index: int):
        self.board = board
        self.index = index

    def play(self) -> Turn:
        raise NotImplemented

    def reset(self):
        pass


class DumbBot(BaseBot):
    """Dumb bot always plays the first card"""
    def play(self) -> Turn:
        return Play(0)

class BasicCheatingBot(BaseBot):
    """
    Cheating bot looks at its hand and plays the last playable cards.
    Otherwise clues or discards unnecessarily depending on the number of available clues.

    Its main problem is discarding 5s from the initial deal
    """
    def play(self) -> Turn:
        hand = self.board._hands[self.board.current_player]
        for i, card in zip(range(self.board.my_hand_size - 1, -1, -1), reversed(hand)):

            if self.board.is_playable(card):
                return Play(i)
        if self.board.clues == 0:
            return Discard(self.board.my_hand_size - 1)
        else:
            return Clue(target=0, color="r") # Clue the next player red

class CheatingBot(BaseBot):
    """
    Improves on BasicCheatingBot by looking at the card it's going to discard and picking safe discards
    Its weakness is probably getting unlucky with draws and running out of turns
    """
    def play(self) -> Turn:
        hand = self.board._hands[self.board.current_player]

        # Play any playable cards. Neither ascending or descending order seem to help
        for i, card in enumerate(hand):
            if self.board.is_playable(card):
                return Play(i)

        # Clue if we're close to max clues
        if self.board.clues > 6:
            return Clue(target=0, color="r")

        # Discard if we have freely discardable cards
        for i, card in enumerate(hand):
            if self.board.is_discardable(card):
                return Discard(i)

        # Clue if we have clues left
        if self.board.clues > 0:
            return Clue(target=0, color="r")

        # Discard any cards that don't need to be saved
        hand.sort(key=lambda x: x.number, reverse=True) # this discards 4 > 3 > 2, but barely helps
        for i, card in enumerate(hand):
            if not self.board.is_unique(card):
                return Discard(i)

        # Last resort, discard
        logging.warning("If this happens, the bot needs to be more sophisticated and take turn order into account")
        return Discard(0)

class ClueBot(BaseBot):
    """Clues playable cards"""
    def play(self) -> Turn:
        # Play clued cards
        for i, is_clued in enumerate(self.board.my_hand_clues):
            if is_clued:
                return Play(i)

        # If out of clues, discard last card (card will never be clued because we play clued cards in prev step)
        if self.board.clues == 0:
            return Discard(self.board.my_hand_size - 1)

        # Clue playable cards
        for player_idx, hand in self.board.visible_hands:
            for j, card in enumerate(hand):
                if self.board.is_playable(card):
                    return Clue(target=player_idx, color=card.color) # todo: pick the least ambiguous target

        # Otherwise discard last card
        if self.board.clues >= 7:
            return Clue(target=0, color="r") # throwaway clue. this is technically not allowed
        return Discard(self.board.my_hand_size - 1)
