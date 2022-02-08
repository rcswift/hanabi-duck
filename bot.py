from __future__ import annotations
import logging

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
    def is_playable(card: Card, board: Board) -> bool:
        """can a card be played immediately?"""
        return board.played_cards[card.color] == card.number - 1

    @staticmethod
    def is_discardable(card: Card, board: Board) -> bool:
        """can a card be discarded? these cards are greyed out in the web version"""
        return board.played_cards[card.color] >= card.number

    @staticmethod
    def is_unique(card: Card, board: Board) -> bool:
        """does a card need to be saved? these cards have a red exclamation point in the web version"""
        original_count = {5: 1, 4: 2, 3: 2, 2: 2, 1: 3}[card.number] # original number of copies of that card
        return (original_count - board.discarded_cards.count(card)) == 1

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
        hand = board._hands[board.current_player]
        for i, card in zip(range(board.my_hand_size() - 1, -1, -1), reversed(hand)):

            if self.is_playable(card, board):
                return Play(i)
        if board.clues == 0:
            return Discard(board.my_hand_size() - 1)
        else:
            return Clue(target=0, color="r") # Clue the next player red

class CheatingBot(BaseBot):
    """
    Improves on BasicCheatingBot by looking at the card it's going to discard and picking safe discards
    Its weakness is probably getting unlucky with draws and running out of turns
    """
    def play(self, board: Board) -> Turn:
        hand = board._hands[board.current_player]

        # Play any playable cards. Neither ascending or descending order seem to help
        for i, card in enumerate(hand):
            if self.is_playable(card, board):
                return Play(i)

        # Clue if we're close to max clues
        if board.clues > 6:
            return Clue(target=0, color="r")

        # Discard if we have freely discardable cards
        for i, card in enumerate(hand):
            if self.is_discardable(card, board):
                return Discard(i)

        # Clue if we have clues left
        if board.clues > 0:
            return Clue(target=0, color="r")

        # Discard any cards that don't need to be saved
        hand.sort(key=lambda x: x.number, reverse=True) # this discards 4 > 3 > 2, but barely helps
        for i, card in enumerate(hand):
            if not self.is_unique(card, board):
                return Discard(i)

        # Last resort, discard
        logging.warning("If this happens, the bot needs to be more sophisticated and take turn order into account")
        return Discard(0)

class ClueBot(BaseBot):
    """Clues playable cards"""
    def play(self, board: Board) -> Turn:
        # Play clued cards
        for i, is_clued in enumerate(board.my_hand_clues()):
            if is_clued:
                return Play(i)

        # If out of clues, discard last card (card will never be clued because we play clued cards in prev step)
        if board.clues == 0:
            return Discard(board.my_hand_size() - 1)

        # Clue playable cards
        for i, hand in enumerate(board.visible_hands()):
            for j, card in enumerate(hand):
                if self.is_playable(card, board):
                    return Clue(target=i, color=card.color) # todo: pick the least ambiguous target

        # Otherwise discard last card
        if board.clues >= 7:
            return Clue(target=0, color="r") # throwaway clue. this is technically not allowed
        return Discard(board.my_hand_size() - 1)
