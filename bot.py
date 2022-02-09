from __future__ import annotations
import logging

from operator import and_, not_, or_, eq

from hanabi import Board, CardInfo, Clue, Discard, Play, CARD_NUMBERS, CARD_COLORS

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

    def listen(self, player: int, turn: Turn) -> None:
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
        for i, card in zip(range(self.board.current_hand_size - 1, -1, -1), reversed(hand)):

            if self.board.is_playable(card):
                return Play(i)
        if self.board.clues == 0:
            return Discard(self.board.current_hand_size - 1)
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
        for i, card_info in enumerate(self.board.current_info):
            if card_info.clued:
                return Play(i)

        # If out of clues, discard last card (card will never be clued because we play clued cards in prev step)
        if self.board.clues == 0:
            return Discard(self.board.current_hand_size - 1)

        # Clue playable cards
        for player_idx, hand in self.board.visible_hands:
            for j, card in enumerate(hand):
                if self.board.is_playable(card):
                    return Clue(target=player_idx, color=card.color) # todo: pick the least ambiguous target

        # Otherwise discard last card
        if self.board.clues >= 7:
            return Clue(target=self.board.relative_player(1), color="r") # throwaway clue. this is technically not allowed
        return Discard(self.board.current_hand_size - 1)

class ClueBotImproved(BaseBot):
    """Prioritizes clues based on turn order"""
    
    def play(self) -> Turn:
        # Play clued cards
        for i, card_info in enumerate(self.board.current_info):
            # Play cards from right to left
            if card_info.clued:
                return Play(i)

        # If out of clues, discard last card (card will never be clued because we play clued cards in prev step)
        if self.board.clues == 0:
            return Discard(self.board.current_hand_size - 1)

        # Clue playable cards in order of preference:
        for player_idx, hand in self.board.visible_hands:
            for card_idx, card in enumerate(hand):
                if self.board.is_playable(card) and not self.board.get_info(player_idx)[card_idx].clued:
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
        return Discard(self.board.current_hand_size - 1)
    
class ClueBotMk3(BaseBot):
    """
    More nuanced cluing and discarding.
    This bot is capable of playing a pefect game, but it has to get really lucky.
    
    It's weakness appears to be duplicate cards. The bot does not keep track of what's already been
    clued in other's hands when forming its own clues, so it can touch a duplicate card. Since it also
    tries to play every clue, it frequently loses. 

    Average score is about 12 points. 
    """
    @property
    def chop(self) -> int:
        """Return the index of the highest un-clued card"""
        non_clued_cards = [idx for idx, info in enumerate(self.board.current_info) if not info.clued]
        if len(non_clued_cards) == 0:
            chop = 0
        else:
            chop = max(non_clued_cards)
        logging.debug(f"Discarding card from position {chop}")
        return chop

    def cards_touched(self, clue: Clue) -> List[bool]:
        """Simulate a clue on a hand to check which cards are touched"""
        hand = self.board.get_hand(clue.target)
        if clue.number:
            return [card.number == clue.number for card in hand]
        elif clue.color:
            return [card.color == clue.color for card in hand]

    def play(self) -> Turn:
        # Play clued cards
        for i, card_info in enumerate(self.board.current_info):
            # Play cards from right to left
            if card_info.clued:
                return Play(i)

        # If out of clues, discard last card (card will never be clued because we play clued cards in prev step)
        if self.board.clues == 0:
            return Discard(self.chop)

        good_clues = []

        # Scan all possible clues:
        for player_offset in range(1,self.board.num_players):
            target = self.board.relative_player(player_offset)
             # The hand that this potential clue would target
            hand = self.board.get_hand(target)
            # The cards that are immediately playable from this hand
            playable = list(map(self.board.is_playable, hand))
            # The cards that have not yet been clued
            not_clued = [not info.clued for info in self.board.get_info(target)]

            should_touch = list(map(and_, playable, not_clued))

            possible_clues = [Clue(target, number=number) for number in set(CARD_NUMBERS)] + [Clue(target, color=color) for color in set(CARD_COLORS)]

            for clue in possible_clues:
                would_touch = self.cards_touched(clue)
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
            if self.board.clues >= 7:
                return Clue(target=self.board.relative_player(1), color="r") # throwaway clue. this is technically not allowed
            return Discard(self.chop)

class ListenerBot(BaseBot):
    """
    This bot listens to other players' clues to avoid cluing duplicates

    The to_be_played property tracks the value for play clues that have been given.
    Decisions on wether or not a card is a player are still made based on cards that
    have actually been played, so there is no concern about order. 
    """
    def reset(self):
        self.to_be_played = {"r": 0, "y": 0, "g": 0, "b": 0, "p": 0}

    @property
    def chop(self) -> int:
        """Return the index of the highest un-clued card"""
        non_clued_cards = [idx for idx, info in enumerate(self.board.current_info) if not info.clued]
        if len(non_clued_cards) == 0:
            chop = 0
        else:
            chop = max(non_clued_cards)
        logging.debug(f"Discarding card from position {chop}")
        return chop

    def already_clued(self, card: Card) -> bool:
        return self.to_be_played[card.color] >= card.number

    def cards_touched(self, clue: Clue) -> List[bool]:
        """Simulate a clue on a hand to check which cards are touched"""
        hand = self.board.get_hand(clue.target)
        if clue.number:
            return [card.number == clue.number for card in hand]
        elif clue.color:
            return [card.color == clue.color for card in hand]

    def play(self) -> Turn:
        logging.debug(f"to_be_played: {self.to_be_played}")
        # Play clued cards
        for i, card_info in enumerate(self.board.current_info):
            # Play cards from right to left
            if card_info.clued:
                return Play(i)

        # If out of clues, discard last card (card will never be clued because we play clued cards in prev step)
        if self.board.clues == 0:
            return Discard(self.chop)

        for target in self.board.other_players:
            # The hand that this potential clue would target
            hand = self.board.get_hand(target)

            for card in hand:
                if self.board.is_playable(card) and not self.already_clued(card):
                    # Decide if Number or Color is better:
                    cards_touched_by_number = sum([c.number == card.number for c in hand])
                    cards_touched_by_color = sum([c.color == card.color for c in hand])

                    if cards_touched_by_number <= cards_touched_by_color:
                        return Clue(target, number=card.number)
                    else:
                        return Clue(target, color=card.color)

        # Otherwise discard last card
        if self.board.clues >= 7:
            return Clue(target=self.board.relative_player(1), color="r") # throwaway clue. this is technically not allowed
        return Discard(self.chop)
                    

    def listen(self, player: int, turn: Turn) -> None:
        # When a clue is given add those cards to our internal 'to_be_played' tracker so we know not to clue duplicates
        # This bot is 'listening to itself' rather than also doing this update in the play() method
        if isinstance(turn, Clue):
            logging.debug(f"Bot {self.index} Heard Clue from Player {player}: {turn}")
            if self.index != turn.target:
                hand = self.board.get_hand(turn.target)

                cards_clued = []

                if turn.number:
                    cards_clued = [card for card in hand if card.number == turn.number]
                elif turn.color:
                    cards_clued = [card for card in hand if card.color == turn.color]

                for card in cards_clued:
                    if self.board.is_playable(card):
                        self.to_be_played[card.color] = card.number
                
