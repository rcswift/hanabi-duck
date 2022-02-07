# Duck Bots

An arena for testing bots for the [Duck](https://github.com/Hanabi-Live/hanabi-live/blob/main/docs/VARIANTS.md#duck) variety of [Hanabi](https://hanab.live/lobby). 

todo: add summary

## Installation

None. Python >= 3.7

## Running

```
python main.py
```

## Bots

### API

Any bot you write should extend `BaseBot`. The game will call its `play` function, and you should return either a `Clue`, `Discard` or `Play` object.

The signatures for these classes are at the top of `hanabi.py`

### Included Bots

Scores are average of seeds 0-99 and are out of 25.

- DumbBot (1.56): Always plays the first card.
- BasicCheatingBot (23.17): Look at its own cards. Play any playable cards. Clue unnecessarily. Discard the last card
