from __future__ import annotations
import logging
from operator import and_, not_, or_, eq

from .base import BaseBot
from .. import Clue, Discard, Play

class ClueBot(BaseBot):
    """Clues playable cards"""
    def play(self, board: Board) -> Turn:
        # Play clued cards
        for i, card_info in enumerate(board.current_info):
            if card_info.clued:
                return Play(i)

        # If out of clues, discard last card (card will never be clued because we play clued cards in prev step)
        if board.clues == 0:
            return Discard(board.current_hand_size - 1)

        # Clue playable cards
        for player_idx, hand in board.visible_hands:
            for j, card in enumerate(hand):
                if board.is_playable(card):
                    return Clue(target=player_idx, color=card.color) # todo: pick the least ambiguous target

        # Otherwise discard last card
        if board.clues >= 7:
            return Clue(target=board.relative_player(1), color="r") # throwaway clue. this is technically not allowed
        return Discard(board.current_hand_size - 1)

class ClueBotImproved(BaseBot):
    """Prioritizes clues based on turn order"""
    
    def play(self, board: Board) -> Turn:
        # Play clued cards
        for i, card_info in enumerate(board.current_info):
            # Play cards from right to left
            if card_info.clued:
                return Play(i)

        # If out of clues, discard last card (card will never be clued because we play clued cards in prev step)
        if board.clues == 0:
            return Discard(board.current_hand_size - 1)

        # Clue playable cards in order of preference:
        for player_idx, hand in board.visible_hands:
            for card_idx, card in enumerate(hand):
                if board.is_playable(card) and not board.get_info(player_idx)[card_idx].clued:
                    # Decide if Number or Color is better:
                    cards_touched_by_number = sum([c.number == card.number for c in hand])
                    cards_touched_by_color = sum([c.color == card.color for c in hand])

                    if cards_touched_by_number < cards_touched_by_color:
                        return Clue(player_idx, number=card.number)
                    else:
                        return Clue(player_idx, color=card.color)

        # Otherwise discard last card
        if board.clues >= 7:
            return Clue(target=board.relative_player(1), color="r") # throwaway clue. this is technically not allowed
        return Discard(board.current_hand_size - 1)
    
class ClueBotMk3(BaseBot):
    """
    More nuanced cluing and discarding.
    This bot is capable of playing a pefect game, but it has to get really lucky.
    
    It's weakness appears to be duplicate cards. The bot does not keep track of what's already been
    clued in other's hands when forming its own clues, so it can touch a duplicate card. Since it also
    tries to play every clue, it frequently loses. 

    Average score is about 12 points. 
    """
    def chop(self, board) -> int:
        """Return the index of the highest un-clued card"""
        non_clued_cards = [idx for idx, info in enumerate(board.current_info) if not info.clued]
        if len(non_clued_cards) == 0:
            chop = 0
        else:
            chop = max(non_clued_cards)
        logging.debug(f"Discarding card from position {chop}")
        return chop

    def play(self, board: Board) -> Turn:
        # Play clued cards
        for i, card_info in enumerate(board.current_info):
            # Play cards from right to left
            if card_info.clued:
                return Play(i)

        # If out of clues, discard last card (card will never be clued because we play clued cards in prev step)
        if board.clues == 0:
            return Discard(self.chop(board))

        good_clues = []

        # Scan all possible clues:
        for player_offset in range(1,board.num_players):
            target = board.relative_player(player_offset)
             # The hand that this potential clue would target
            hand = board.get_hand(target)
            # The cards that are immediately playable from this hand
            playable = list(map(board.is_playable, hand))
            # The cards that have not yet been clued
            not_clued = [not info.clued for info in board.get_info(target)]

            should_touch = list(map(and_, playable, not_clued))

            possible_clues = [Clue(target, number=number) for number in set(board.variant.CARD_NUMBERS)] + [Clue(target, color=color) for color in set(board.variant.CARD_COLORS)]

            for clue in possible_clues:
                would_touch = board.cards_touched(clue)
                num_touch = sum(would_touch)

                # Check that this clue touches only playable cards
                if sum(map(eq, should_touch, would_touch)) == len(hand) and num_touch != 0:
                    good_clues.append((clue, num_touch))


        if len(good_clues) > 0:
            # Now that we have a list of good clues (clues that touch only immediately playable cards), we pick which one 
            # to give based on which player needs information the most:
            good_clues.sort(key=lambda x: x[1])
            good_clues.reverse()
            for clue, num_touch in good_clues:
                logging.debug(f"Good Clue: {clue} : {num_touch} cards")
            return good_clues[0][0]
        else:
            # Otherwise discard last card
            if board.clues >= 7:
                return Clue(target=board.relative_player(1), color="r") # throwaway clue. this is technically not allowed
            return Discard(self.chop(board))

class ClueBotAdvanced(BaseBot):
    """
    This bot implements more detailed rules:
        First, try to play any clued cards
                                                                                                                   
        If no cards are clued, try to give a clue
        Rules for clues:
          1. A clue must not touch any non-playable cards
          2. A clue must not touch any duplicate cards (either in the same hand, or already clued in another hand)
          3. A clue must touch at least one playable card
                                                                                                                   
        If no clue meets the requirements, or there are no clues to give, discard.
        If any cards were playable, they would have been played above so the chop must be the last card

    (Derived from ListenerBotMk2, but without the Listening)
    """

    @staticmethod
    def get_clued_cards(board) -> List[Cards]:
        """Identify the set of all cards that are currently clued, waiting to be played"""
        clued_cards = []
        for target in board.other_players:
            for card, info in zip(board.get_hand(target), board.get_info(target)):
                if info.clued:
                    clued_cards.append(card)
        return clued_cards

    @staticmethod
    def get_valid_clues(board) -> List[Clue]:
        """Finds all the rule-compliant clues able to be given"""
        
        clued_cards = ClueBotAdvanced.get_clued_cards(board)

        logging.debug(f"Clued Cards: {[str(x) for x in clued_cards]}")
        
        # Then explore all possible clues that can be given:
        valid_clues = []

        for target in board.other_players:
            target_hand = board.get_hand(target)
            target_info = board.get_info(target)

            target_playable = [board.is_playable(card) for card in target_hand]
            target_clued = [card.clued for card in target_info]

            possible_clues = [Clue(target, number=number) for number in set(board.variant.CARD_NUMBERS)] + [Clue(target, color=color) for color in set(board.variant.CARD_COLORS)]

            for clue in possible_clues:
                clue_touched = board.cards_touched(clue)

                # A clue must touch at least one card
                if sum(clue_touched) == 0:
                    continue

                # A clue must not touch any non-playable cards:
                if sum([(not board.is_playable(card)) for idx, card in enumerate(target_hand) if clue_touched[idx]]) > 0:
                    continue

                # A clue must not touch a card already clued in another players' hand:
                if sum([(card in clued_cards) for idx, card in enumerate(target_hand) if clue_touched[idx]]) > 0:
                    continue

                # A clue must not touch multiple of the same card in the same hand:
                if max([target_hand.count(card) for idx, card in enumerate(target_hand) if clue_touched[idx]]) > 1:
                    continue

                # If we've made it this far, the clue is valid:
                logging.debug(f"Valid Clue: {clue}")
                valid_clues.append(clue)

        return valid_clues

    def play(self, board: Board) -> Turn:
        # Play clued cards
        logging.debug(f"Current Information: {[card.clued for card in board.current_info]}")
        for i, card_info in reversed(list(enumerate(board.current_info))):
            # Play cards from oldest to newest
            if card_info.clued:
                return Play(i)

        # Give a Clue
        if board.clues > 0: 
            valid_clues = self.get_valid_clues(board)

            if valid_clues:
                valid_targets = set([clue.target for clue in valid_clues])

                # Select the player with the least information
                # 'sorted()' is stable w.r.t. the original order, so this sorts lowest-to-highest and preserves turn order.
                clue_target = sorted([(target, sum([card.clued for card in board.get_info(target)])) for target in valid_targets], key=lambda x: x[1])[0][0]
                logging.debug(f"Give Clue to Player {clue_target}")

                # Of the remaining clues, pick the one that touches the most cards
                return sorted([(clue, sum(board.cards_touched(clue))) for clue in valid_clues if clue.target == clue_target], key=lambda x: x[1], reverse=True)[0][0]

        # Discard
        if board.clues < board.MAX_CLUES:
            # Oldest card. Any players would have been played already.
            return Discard(board.current_hand_size-1)

        # Couldn't Play. Couldn't Clue. Couldn't Discard. Nothing left to try. This is probably a strike.
        return Play(0)
