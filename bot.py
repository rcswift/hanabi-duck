from __future__ import annotations
import logging

from hanabi import Board, CardInformation, Clue, Discard, Play

class BaseBot():
    def __init__(self, board: Board, index: int):
        self.board = board
        self.index = index

        self.reset()

    def reset(self):
        """Executed once at the start of the game"""
        pass

    def play(self) -> Turn:
        """Executed on my turn"""
        raise NotImplemented

    def listen(self, turn: Turn) -> None:
        """Executed after every turn"""
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
            return Clue(target=self.board.relative_player(1), color="r") # Clue the next player red

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
            return Clue(target=self.board.relative_player(1), color="r")

        # Discard if we have freely discardable cards
        for i, card in enumerate(hand):
            if self.board.is_discardable(card):
                return Discard(i)

        # Clue if we have clues left
        if self.board.clues > 0:
            return Clue(target=self.board.relative_player(1), color="r")

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
        for i, card_info in enumerate(self.board.current_information):
            if card_info.clued:
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
            return Clue(target=self.board.relative_player(1), color="r") # throwaway clue. this is technically not allowed
        return Discard(self.board.my_hand_size - 1)

class ClueBotImproved(BaseBot):
    """Prioritizes clues based on turn order"""
    
    def play(self) -> Turn:
        # Play clued cards
        for i, card_info in enumerate(self.board.current_information):
            # Play cards from right to left
            if card_info.clued:
                return Play(i)

        # If out of clues, discard last card (card will never be clued because we play clued cards in prev step)
        if self.board.clues == 0:
            return Discard(self.board.my_hand_size - 1)

        # Clue playable cards in order of preference:
        for player_idx, hand in self.board.visible_hands:
            for card_idx, card in enumerate(hand):
                if self.board.is_playable(card) and not self.board.information[player_idx][card_idx].clued:
                    # Decide if Number or Color is better:
                    cards_touched_by_number = sum([c.number == card.number for c in hand])
                    cards_touched_by_color = sum([c.color == card.color for c in hand])

                    if cards_touched_by_number < cards_touched_by_color:
                        return Clue(player_idx, number=card.number)
                    else:
                        return Clue(player_idx, color=card.color)

        # Otherwise discard last card
        if self.board.clues >= 7:
            return Clue(target=self.board.relative_player(1), color="r") # throwaway clue. this is technically not allowed
        return Discard(self.board.my_hand_size - 1)

    
