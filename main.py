import argparse
import logging
import random
from typing import List

from bot import *
from hanabi import Board, VariantDefault, VariantRainbow, VariantDuck


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
        for p in players:
            p.reset()
        board.reset(seed)
        scores.append(run(board, bots))

    return scores

if __name__ == "__main__":

    logging_levels = {
        "DEBUG"    : logging.DEBUG,
        "INFO"     : logging.INFO,
        "WARNING"  : logging.WARNING,
        "ERROR"    : logging.ERROR,
        "CRITICAL" : logging.CRITICAL,
    }

    bot_types = [DumbBot, ClueBot, ClueBotImproved, ClueBotMk3, ClueBotAdvanced, BasicCheatingBot, CheatingBot, LookaheadBot]
    bot_names = {bot.__name__: bot for bot in bot_types}

    variant_types = {
        "Default" : VariantDefault,
        "Rainbow" : VariantRainbow,
        "Duck"    : VariantDuck,
    }

    parser = argparse.ArgumentParser(description='Hanabi game simulator')
    parser.add_argument('-p', '--num_players', default=4, type=int, help="Number of players")
    parser.add_argument('-s', '--seed', default=0, nargs="?", help="Random seed to use for the game (leave blank for 'None')")
    parser.add_argument('-v', '--verbosity', default="ERROR", choices=list(logging_levels.keys()), type=str, help="Level of information to print")
    parser.add_argument('-n', '--num_games', default=100, type=int, help="Number of games to play")
    parser.add_argument('-b', '--bots', default=None, action='append', choices=bot_names)

    args = parser.parse_args()

    logging.basicConfig(level=logging_levels[args.verbosity])
    # I misuse logging here. Debug is for debugging, info is for watching a single game, warning is for many runs of the bot

    STARTING_PLAYER = 0

    if args.bots:
        selected_bots = [bot_names[x] for x in args.bots]
    else:
        selected_bots = bot_types

    if not args.seed:
        # If no seed is provided, pick a random random seed. This ensures that each bot is playing the same games. 
        args.seed = random.randint(0, 2**31)
        # Capture the seed so we can replay this game later
        logging.debug(f"Using Random Seed {args.seed}")
    else:
        args.seed = int(args.seed,0)

    for bot_type in selected_bots:
        board = Board(args.num_players, args.seed, STARTING_PLAYER, variant=VariantDuck)

        bots = [bot_type() for _ in range(args.num_players)]

        scores = score_bot(board, bots, args.num_games, args.seed)

        final_result = (f"Bot {bot_type.__name__} completed {len(scores)} trials with an average score of {sum(scores) / len(scores)} " +
            f"(max: {max(scores)}, min: {min(scores)}, {scores.count(25)} perfect)")
        logging.error(final_result)
