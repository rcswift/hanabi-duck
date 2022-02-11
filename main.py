import logging
from typing import List

from bot import *
from hanabi import Board, VariantDuck

logging.basicConfig(level=logging.ERROR)
# I misuse logging here. Debug is for debugging, info is for watching a single game, warning is for many runs of the bot

def run(board: Board, bots: List[BaseBot]):
    """Run a single game"""

    while not board.game_over:
        logging.info(str(board))
        turn = bots[board.current_player].play(board)
        board.evaluate(turn)

    logging.warning(f"Game is complete with a score of {board.score}")
    return board.score

def score_bot(board: Board, players: List[BaseBot], trials=100, starting_seed=None) -> List[int]:
    """Get a bot's average score"""

    scores = []

    for i in range(trials):
        seed = None if starting_seed is None else starting_seed + i
        scores.append(run(board, bots))
        for p in players:
            p.reset()
        board.reset(seed)

    return scores

if __name__ == "__main__":
    NUM_PLAYERS = 4
    STARTING_SEED = 0
    STARTING_PLAYER = 0
    TRIALS = 100

    bot_types = [DumbBot, ClueBot, ClueBotImproved, ClueBotMk3, ClueBotAdvanced, BasicCheatingBot, CheatingBot]

    for bot_type in bot_types:
        board = Board(NUM_PLAYERS, STARTING_SEED, STARTING_PLAYER, variant=VariantDuck)

        bots = [bot_type() for _ in range(NUM_PLAYERS)]

        scores = score_bot(board, bots, TRIALS, STARTING_SEED)

        final_result = (f"Bot {bot_type.__name__} completed {len(scores)} trials with an average score of {sum(scores) / len(scores)} " +
            f"(max: {max(scores)}, min: {min(scores)}, {scores.count(25)} perfect)")
        logging.warning(final_result)
        print(final_result)
