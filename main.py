import logging
from typing import List

from bot import BaseBot, BasicCheatingBot, DumbBot
from hanabi import Board

logging.basicConfig(level=logging.INFO)
# I misuse logging here. Debug is for debugging, info is for watching a single game, warning is for many runs of the bot

def run(bots, seed=None):
    """Run a single game"""
    board = Board(NUM_PLAYERS, seed)

    while not board.is_game_over():
        turn = bots[board.current_player()].play(board)
        board.evaluate(turn)

        logging.info(str(board))

    logging.warning(f"Game is complete with a score of {board.score()}")
    return board.score()

def score_bot(players: List[BaseBot], num_players=4, trials=100, starting_seed=None) -> List[int]:
    """Get a bot's average score"""

    scores = []

    for i in range(trials):
        seed = None if starting_seed is None else starting_seed + i
        scores.append(run(players, seed=seed))
        for p in players:
            p.reset()

    return scores

if __name__ == "__main__":
    NUM_PLAYERS = 4

    # Score your bot on 100 runs
    bot = BasicCheatingBot
    scores = score_bot([bot() for i in range(NUM_PLAYERS)], starting_seed=0)
    final_result = (f"Bot {bot.__name__} completed {len(scores)} trials with an average score of {sum(scores) / len(scores)} " +
        f"(max: {max(scores)}, min: {min(scores)}, {scores.count(25)} perfect)")
    logging.warning(final_result)
    print(final_result)

    # Test your bot once
    # run([bot() for i in range(NUM_PLAYERS)], seed=0)
