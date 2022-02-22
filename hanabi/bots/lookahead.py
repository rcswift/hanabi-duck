from __future__ import annotations
import logging
from operator import and_, not_, or_, eq

from .base import BaseBot
from .. import Clue, Discard, Play
from .clue import ClueBotAdvanced

class LookaheadBot(BaseBot):
    """
    LookaheadBot will always try to play a card on its turn. Knowing this about itself, it
    will assume other players will play on their turns and consider giving clues to cards
    that will be playable after others have played. 

    For sanity, this 'lookahead' process will only cover each other players next turn, since
    other players could choose to give us information and we can't predict that. 

    The average score for this bot is 16.38. Slightly better than ClueBotAdvanced.
    """

    def _is_hypothetical_playable(self, card: Card, played_cards: Dict[str][int]) -> bool:
        return played_cards[card.color] == card.number-1

    def play(self, board: Board) -> Turn:
        # If we have a clued card, play it immediately. 
        for i, card_info in reversed(list(enumerate(board.current_info))):
            # Play cards from oldest to newest
            if card_info.clued:
                return Play(i)

        # Grab a copy of the currently played cards
        future_cards = {}
        for color, number in board.played_cards.items():
            future_cards[color] = number

        # Give a clue, if we can
        if board.clues > 0:
            # Decide if a player will play on their turn
            for player in board.other_players:
                player_info = board.get_info(player)
                player_hand = board.get_hand(player)

                will_play = bool([info.clued for info in player_info].count(True))

                if will_play:
                    # Decide which card they will play, and add it to the hypothetical board state
                    for i, card_info in reversed(list(enumerate(player_info))):
                        # Play cards from oldest to newest
                        if card_info.clued:
                            # Add this card to the hypothetical board state
                            card = player_hand[i]
                            logging.debug(f"Player {player} will play card {i}: {card} on their turn")
                            if self._is_hypothetical_playable(card, future_cards):
                                future_cards[card.color] = card.number
                            else:
                                logging.debug(f"Player {player} is about to make a mistake!")
                            break
                else:
                    # This player has no cards currently clued. See if we can give them a clue. 
                    # Follow the rules set out in 'ClueBotAdvanced'
                    clued_cards = ClueBotAdvanced.get_clued_cards(board)
                    possible_clues = [Clue(player, number=number) for number in set(board.variant.CARD_NUMBERS)] + [Clue(player, color=color) for color in set(board.variant.CARD_COLORS)]

                    for clue in possible_clues:
                        clue_touched = board.cards_touched(clue)

                        # A clue must touch at least one card
                        if sum(clue_touched) == 0:
                            continue

                        # A clue must not touch any non-(hypothetically)-playable cards:
                        if sum([(not self._is_hypothetical_playable(card, future_cards)) for idx, card in enumerate(player_hand) if clue_touched[idx]]) > 0:
                            continue

                        # A clue must not touch a card already clued in another players' hand:
                        if sum([(card in clued_cards) for idx, card in enumerate(player_hand) if clue_touched[idx]]) > 0:
                            continue

                        # A clue must not touch multiple of the same card in the same hand:
                        if max([player_hand.count(card) for idx, card in enumerate(player_hand) if clue_touched[idx]]) > 1:
                            continue

                        # If we've made it this far, give the clue:
                        return(clue)

                    logging.debug(f"Player {player} has no valid clues")

        # In this case there are no clues to give. Discard.
        if board.clues < board.MAX_CLUES:
            # Oldest card. Any players would have been played already.
            return Discard(board.current_hand_size-1)

        # Couldn't Play. Couldn't Clue. Couldn't Discard. Nothing left to try. This is probably a strike.
        return Play(0)
       

