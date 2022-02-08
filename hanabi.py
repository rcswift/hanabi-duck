from dataclasses import dataclass
import logging
from textwrap import dedent, indent
from typing import List, Union
import random

# Turn
@dataclass
class Clue:
    target: int
    # target is the index into visible_hands or (1 + the number relative to us)
    # i.e. 0 will be the next player, 1 will be the player in 2 turns etc.
    # negative targets are valid: -2 is the player before me
    color: str = None
    number: int = None

    def __post_init__(self):
        if (self.color is None) == (self.number is None):
            raise ValueError("Exactly one of color and number must be specified")
@dataclass
class Discard:
    index: int
@dataclass
class Play:
    index: int

Turn = Union[Clue, Discard, Play]

@dataclass
class Card:
    color: str
    number: int
    clued: bool = False

    def __str__(self):
        return f"{self.color}{self.number}{'*' if self.clued else ' '}"
    
class InvalidMove(Exception):
    pass

class Board:
    def __init__(self, num_players=4, seed=None, starting_player=0):
        self.num_players = num_players

        ### Hidden attributes. DO NOT ACCESS THESE ATTRIBUTES IN YOUR BOT ###
        self._deck: List[Card] = [Card(c, n) for c in "rygbp" for n in (1, 1, 1, 2, 2, 3, 3, 4, 4, 5)]
        random.seed(seed)
        random.shuffle(self._deck)

        self._hands: List[List[Card]] = [[] for i in range(num_players)]
        for i in range(num_players):
            for j in range(4): # TODO: make number of cards per player dynamic
                self._draw_card(i)

        # History
        self.turns: List[Turn] = [] # History of turns. For debugging only I think

        # Visible board state
        self.played_cards: Dict[str, int] = {"r": 0, "y": 0, "g": 0, "b": 0, "p": 0}
        self.discarded_cards: List[Card] = []
        self.starting_player: int = 0
        self.turn_index = 0
        self.turns_left: Optional[int] = None # None until the deck is exhausted, then counts down to 0
        self.strikes = 0
        self.clues = 8

    @property
    def current_player(self):
        return (self.turn_index + self.starting_player) % self.num_players

    @property
    def game_over(self) -> bool:
        return self.strikes == 3 or all(v == 5 for v in self.played_cards.values()) or self.turns_left == 0

    @property
    def score(self) -> int:
        return sum(self.played_cards.values())

    @property
    def visible_hands(self) -> List[List[Card]]:
        """Other players' hands from the perspective of the current player"""
        return self._hands[self.current_player + 1:] + self._hands[:self.current_player]

    @property
    def my_hand_clues(self) -> List[bool]:
        """Which cards in my hand are clued"""
        return [card.clued for card in self._hands[self.current_player]]

    @property
    def my_hand_size(self) -> int:
        """How many cards are in my hand"""
        return len(self._hands[self.current_player])

    def evaluate(self, turn: Turn):
        hand = self._hands[self.current_player]

        if isinstance(turn, Clue):
            target = (self.current_player + turn.target + 1) % self.num_players
            logging.info(f"Player {self.current_player} clued player {target} {turn.color or turn.number}")

            if target == self.current_player:
                raise InvalidMove("cannot clue self")
            if self.clues == 0:
                raise InvalidMove("no clues available")

            for card in self._hands[target]:
                if card.number == turn.number or card.color == turn.color:
                    card.clued = True
            # TODO: A Clue must clue a card. For duck, negative clues are worthless though so not going to implement.

            self.clues -= 1
        elif isinstance(turn, Play):
            played_card = hand.pop(turn.index)

            if self.played_cards[played_card.color] == played_card.number - 1:
                logging.info(f"Player {self.current_player} played from slot {turn.index}, {str(played_card)} successfully")
                self.played_cards[played_card.color] += 1

                if played_card.number == 5:
                    self.clues += 1
                    self.clues = max(self.clues, 8)
            else:
                logging.info(f"Player {self.current_player} tried to play from slot {turn.index}, {str(played_card)}")
                self.discarded_cards.append(played_card)
                self.strikes += 1

            self._draw_card()
        elif isinstance(turn, Discard):
            if self.clues == 8:
                logging.warning("Cannot discard at max clues")
                raise InvalidMove("cannot discard at max clues")
            discarded_card = hand.pop(turn.index)
            logging.info(f"Player {self.current_player} discarded the card in slot {turn.index}, {str(discarded_card)}")
            self.discarded_cards.append(discarded_card)
            self._draw_card()
            self.clues += 1
        else:
            raise InvalidMove("invalid turn", turn)

        if self.turns_left is not None:
            self.turns_left -= 1
            
        self.turns.append(turn)
        self.turn_index += 1

    def _draw_card(self, index=None):
        """Draw a card for the `index`th player or the current player"""

        if self._deck:
            new_card = self._deck.pop()
            player = index if index is not None else self.current_player
            self._hands[player].insert(0, new_card)
        else:
            if self.turns_left is None:
                self.turns_left = self.num_players + 1

    def __str__(self):
        newline = "\n"
        return dedent(f"""
        ================ Game at turn {self.turn_index} ===================

        Played cards ({self.score} / 25):
            {self.played_cards}

        Hands:{newline}{indent(newline.join(" ".join(map(str, hand)) + (" <- current" if i == self.current_player else "") for i, hand in enumerate(self._hands)), " " * 12)}

        {self.strikes} strikes, {self.clues} clues, {f"{self.turns_left} turns remaining" if self.turns_left is not None else ""}

        Discarded:
            {" ".join(map(str, self.discarded_cards))}
        """)
