import logging
from typing import List

from bot import BaseBot, DumbBot
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

def score_bot(players: List[BaseBot], num_players=4, trials=100, starting_seed=None) -> float:
    """Get a bot's average score"""

    scores = []

    for i in range(trials):
        seed = None if starting_seed is None else starting_seed + i
        scores.append(run(players, seed=seed))
        for p in players:
            p.reset()

    result = sum(scores) / trials
    logging.warning(f"Completed {trials} trials of bot with an average score of {result} " +
        f"(max: {max(scores)}, min: {min(scores)})")
    return result

if __name__ == "__main__":
    NUM_PLAYERS = 4
    score_bot([DumbBot() for i in range(NUM_PLAYERS)], starting_seed=0)
