from dataclasses import dataclass, field
import logging
from textwrap import dedent, indent
from typing import List, Union, Tuple, Set, Dict
import random


# Turn
@dataclass
class Clue:
    target: int
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

    def __str__(self):
        return f"{self.color}{self.number}"

@dataclass
class CardInfo:
    # This syntax is required to initialize each new CardInfo object with a COPY of the constant values
    color: Set[str]
    number: Set[int] 
    clued: bool = False

    def __str__(self):
        return ("*" if self.clued else "") + "".join(map(str, self.color)) + "".join(map(str, self.number))
    
class InvalidMove(Exception):
    pass

class VariantBase:
    """
    The variant class implements the rules for cluing and touching cards as well as
    defining the initial contents of the deck. 

    All methods in this class are @classmethods. An instance of this class should 
    not need to be created. 
    """
    @classmethod
    def clue_touched(self, card: Card, clue: Clue) -> bool:
        """Return 'True' if the given clue touches the given card"""
        raise NotImplemented

    @classmethod
    def update_info(self, card_info: CardInfo, clue: Clue, touched: bool) -> None:
        """Update the given CardInfo struct based on if the given clue touched the corresponding card"""
        raise NotImplemented

    CARD_COLORS : List[str] = []
    CARD_NUMBERS : List[int] = []


class VariantDefault(VariantBase):
    @classmethod
    def clue_touched(self, card: Card, clue: Clue) -> bool:
        return (card.color == clue.color or card.number == clue.number)

    @classmethod
    def update_info(self, card_info: CardInfo, clue: Clue, touched: bool) -> None:
        if touched:
            card_info.clued = True

        if clue.color:
            if touched:
                for color in set(self.CARD_COLORS):
                    if not color == clue.color:
                        card_info.color.discard(color)
            else:
                card_info.color.discard(clue.color)

        if clue.number:
            if touched:
                for number in set(self.CARD_NUMBERS):
                    if not number == clue.number:
                        card_info.number.discard(number)
            else:
                card_info.number.discard(clue.number)

    CARD_COLORS  : List[str] = ["r", "y", "g", "b", "p"]
    CARD_NUMBERS : List[int] = [1, 1, 1, 2, 2, 3, 3, 4, 4, 5]

class VariantRainbow(VariantDefault):
    @classmethod
    def clue_touched(self, card: Card, clue: Clue) -> bool:
        if clue.color == "m":
            raise InvalidMove("cannot clue rainbow suit 'm'")
        return (card.color == clue.color or card.color == "m" or card.number == clue.number)

    @classmethod
    def update_info(self, card_info: CardInfo, clue: Clue, touched: bool) -> None:
        if touched:
            card_info.clued = True

        if clue.color:
            if touched:
                for color in set(self.CARD_COLORS):
                    if not (color == clue.color or color == "m"):
                        card_info.color.discard(color)
            else:
                card_info.color.discard(clue.color)

        if clue.number:
            if touched:
                for number in set(self.CARD_NUMBERS):
                    if not number == clue.number:
                        card_info.number.discard(number)
            else:
                card_info.number.discard(clue.number)
        
    CARD_COLORS : List[str] = ["r", "y", "g", "b", "p", "m"]

class VariantDuck(VariantDefault):
    @classmethod
    def update_info(self, card_info: CardInfo, clue: Clue, touched: bool) -> None:
        if touched:
            card_info.clued = True
    
class Board:
    MAX_CLUES = 8

    def __init__(self, num_players, seed=None, starting_player=0, variant=VariantDefault):
        self.num_players = num_players
        self.variant = variant

        self._rng = random.Random(0)

        self.reset(seed, starting_player)

    def reset(self, seed=None, starting_player=0):
        # Visible board state
        self.played_cards: Dict[str, int] = {"r": 0, "y": 0, "g": 0, "b": 0, "p": 0}
        self.discarded_cards: List[Card] = []
        self.starting_player: int = 0
        self.turn_index = 0
        self.turns_left: Optional[int] = None # None until the deck is exhausted, then counts down to 0
        self.strikes = 0
        self.clues = Board.MAX_CLUES

        ### Hidden attributes. DO NOT ACCESS THESE ATTRIBUTES IN YOUR BOT ###
        self._card_info: List[List[CardInfo]] = [[] for _ in range(self.num_players)]
        self._deck: List[Card] = [Card(c, n) for c in self.variant.CARD_COLORS for n in self.variant.CARD_NUMBERS]
        self._rng.seed(seed)
        self._rng.shuffle(self._deck)

        self._hands: List[List[Card]] = [[] for i in range(self.num_players)]
        for i in range(self.num_players):
            for j in range(self.initial_cards_per_player):
                self._draw_card(i)

        # History
        self.turns: List[Turn] = [] # History of turns. For debugging only I think

    """
    Global game properties
    """
    @property
    def initial_cards_per_player(self):
        return 5 if self.num_players < 3 else 4

    @property
    def game_over(self) -> bool:
        return self.strikes == 3 or all(v == 5 for v in self.played_cards.values()) or self.turns_left == 0

    @property
    def score(self) -> int:
        return sum(self.played_cards.values())

    """
    Properties for information about players or their cards
    """
    @property
    def current_player(self) -> int:
        return (self.turn_index + self.starting_player) % self.num_players

    @property
    def other_players(self) -> Set[int]:
        """Returns an iterator through the other player's indices in relative turn order"""
        players = list(range(self.num_players))
        return players[self.current_player+1:] + players[:self.current_player]

    @property
    def current_info(self) -> List[CardInfo]:
        return self.get_info(self.current_player)

    @property
    def visible_hands(self) -> List[Tuple[int, List[Card]]]: 
        """Other players' hands in turn-order with respect to the current player"""
        return [(player, self.get_hand(player)) for player in self.other_players]

    @property
    def current_hand_size(self) -> int:
        """How many cards are in my hand"""
        return len(self._current_hand)

    def get_hand(self, player: int) -> List[Card]:
        if player == self.current_player:
            raise InvalidMove("cannot look at own hand")
        return self._hands[player]

    def get_info(self, player: int) -> List[CardInfo]:
        return self._card_info[player]

    """
    Common helper functions
    """
    def is_playable(self, card: Card) -> bool:
        """can a card be played immediately?"""
        return self.played_cards[card.color] == card.number - 1

    def is_discardable(self, card: Card) -> bool:
        """can a card be discarded? these cards are greyed out in the web version"""
        return self.played_cards[card.color] >= card.number

    def is_unique(self, card: Card) -> bool:
        """does a card need to be saved? these cards have a red exclamation point in the web version"""
        return (self.variant.CARD_NUMBERS.count([card.number]) - self.discarded_cards.count(card)) == 1

    def relative_player(self, idx: int) -> int:
        """Returns the absolute index of a player relative to the current player 
           i.e. +1 for the next player, 0 for the current player, -1 for the previous player"""
        return (self.current_player + idx) % self.num_players

    def clue_touched(self, card: Card, clue: Clue) -> bool:
        """Checks if a given card is touched by a given clue"""
        return self.variant.clue_touched(card, clue)

    def cards_touched(self, clue: Clue) -> List[bool]:
        """Returns a list of cards that will be touched by this clue"""
        return [self.clue_touched(card, clue) for card in self.get_hand(clue.target)]

    def evaluate(self, turn: Turn):
        """Processes the results of each players' turn"""
        if isinstance(turn, Clue):
            self._clue_turn(turn)
        elif isinstance(turn, Play):
            self._play_turn(turn)
        elif isinstance(turn, Discard):
            self._discard_turn(turn)
        else:
            raise InvalidMove("invalid turn", turn)

        if self.turns_left is not None:
            self.turns_left -= 1
            
        self.turns.append(turn)
        self.turn_index += 1

    #
    # Private Methods
    #
    @property
    def _current_hand(self) -> List[Card]:
        """Bots should NOT access this property"""
        return self._hands[self.current_player]

    def _clue_turn(self, clue: Clue):
        target = clue.target
        logging.info(f"Player {self.current_player} clued player {target} {clue.color or clue.number}")

        if target == self.current_player:
            raise InvalidMove("cannot clue self")
        if self.clues == 0:
            raise InvalidMove("no clues available")

        # Update Information
        logging.debug(f"Player {target} Old Information: {[str(x) for x in self._card_info[target]]}")

        for card, card_info in zip(self._hands[target], self._card_info[target]):
            self.variant.update_info(card_info, clue, self.variant.clue_touched(card, clue))

        logging.debug(f"Player {target} New Information: {[str(x) for x in self._card_info[target]]}")

        self.clues -= 1

    def _play_turn(self, card: Play):
        played_card = self._current_hand.pop(card.index)

        if self.played_cards[played_card.color] == played_card.number - 1:
            logging.info(f"Player {self.current_player} played from slot {card.index}, {str(played_card)} successfully")
            self.played_cards[played_card.color] += 1

            if played_card.number == 5:
                self.clues += 1
                self.clues = max(self.clues, Board.MAX_CLUES)
        else:
            logging.info(f"Player {self.current_player} tried to play from slot {card.index}, {str(played_card)}")
            self.discarded_cards.append(played_card)
            self.strikes += 1

        # Update information
        logging.debug(f"Player {self.current_player} Old Information: {[str(x) for x in self.current_info]}")
        self.current_info.pop(card.index)

        self._draw_card()

        logging.debug(f"Player {self.current_player} New Information: {[str(x) for x in self.current_info]}")

    def _discard_turn(self, card: Discard):
        if self.clues == Board.MAX_CLUES:
            logging.warning("Cannot discard at max clues")
            raise InvalidMove("cannot discard at max clues")
        discarded_card = self._current_hand.pop(card.index)
        logging.info(f"Player {self.current_player} discarded the card in slot {card.index}, {str(discarded_card)}")
        self.discarded_cards.append(discarded_card)

        # Update information
        logging.debug(f"Player {self.current_player} Old Information: {[str(x) for x in self.current_info]}")
        self.current_info.pop(card.index)

        self._draw_card()

        logging.debug(f"Player {self.current_player} New Information: {[str(x) for x in self.current_info]}")

        self.clues += 1

    def _draw_card(self, index=None):
        """Draw a card for the `index`th player or the current player"""

        if self._deck:
            new_card = self._deck.pop()
            player = index if index is not None else self.current_player
            self._hands[player].insert(0, new_card)
            self._card_info[player].insert(0, CardInfo(set(self.variant.CARD_COLORS), set(self.variant.CARD_NUMBERS)))
        else:
            if self.turns_left is None:
                self.turns_left = self.num_players + 1

    def __str__(self):
        newline = "\n"
        return dedent(f"""
        ================ Game at turn {self.turn_index} ===================

        Played cards ({self.score} / 25):
            {self.played_cards}

        Hands:{newline}{indent(newline.join(str(i) + ": " + " ".join(map(str, hand)) + (" <- current" if i == self.current_player else "") for i, hand in enumerate(self._hands)), " " * 12)}

        {self.strikes} strikes, {self.clues} clues, {f"{self.turns_left} turns remaining" if self.turns_left is not None else ""}

        Discarded:
            {" ".join(map(str, self.discarded_cards))}
        """)
