import logging
from enum import Enum

import words.bot
from words.human import Human
from words.vocabulary import BloomVocabulary


logger = logging.getLogger('words')


class PlayerType(Enum):
    HUMAN = 1
    BOT = 2


class Game:

    def __init__(self, N, M, humans, bots, word=None):
        self._N = N
        self._M = M

        self.used_words = set()

        self.vocabulary = BloomVocabulary()

        self._initial_word = word
        self.field = self._init_field()
        self._free_cells = (N - 1) * M
        self._players = self._init_players(humans, bots)

    def _init_field(self):
        field = [['' for _ in range(self._N)]
                           for _ in range(self._M)]

        if self._initial_word and len(self._initial_word) == self._M:
            field[self._N // 2] = list(self._initial_word)
            self.used_words.add(self._initial_word)
        else:
            word = self.vocabulary.get_word(self._M)
            field[self._N // 2] = list(word)
            self.used_words.add(word)

        return field

    def _init_players(self, humans, bots):
        players = []
        i = 0
        if type(humans) == int:
            for _ in range(humans):
                players.append(Player(Human(self), f'Player_{i}'))
                i += 1

        if type(bots) == int:
            for _ in range(bots):
                players.append(Player(words.bot.Druz(self), f'Player_{i}'))
                i += 1

        return players

    def run(self):
        passes = 0
        while True:
            for player in self._players:
                guess = player.move()
                if not guess:
                    passes += 1
                    if passes == len(self._players):
                        break
                else:
                    cell, letter, word = guess
                    self._free_cells -= 1
                    self.field[cell[0]][cell[1]] = letter
                    self.used_words.add(word)
                    player._score += len(word)
                    passes = 0

                    print(word)
                    print(self)

            if self._free_cells < len(self._players):
                break

            if passes == len(self._players):
                break

        print('Game over')

    def __str__(self):
        score = 'Score:\n'
        score += '\n'.join([str(x) for x in self._players])

        field = ''
        for row in game.field:
            field += '|'.join([f" {x or ' '} " for x in row]) + '\n'
            field += '+'.join(['---' for _ in row]) + '\n'
        return score + '\n\n' + field


class Player:

    def __init__(self, engine, name):
        self._engine = engine
        self._name = name
        self._score = 0

    def move(self):
        return self._engine.guess_next()

    def __str__(self):
        return f'{self._name}: {self._score}'


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(ch)

    game = Game(10, 10, 0, 3, 'АБВГДЕЖЗИК')
    game.run()
