import logging
import os
import psutil
import time
from collections import defaultdict
from pprint import pprint

from words.utils import execution_time_log
from words.vocabulary import VocabularyAnswers, Vocabulary

logger = logging.getLogger(__name__)


possible_letters = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
process = psutil.Process(os.getpid())


class Wasserman:

    def __init__(self, game):
        self._game = game

        self._vocabulary_checks = 0
        self._longest_word = ''
        self._tested_routes = set()

    @execution_time_log('Wasserman guess next')
    def guess_next(self):
        self._vocabulary_checks = 0
        self._longest_word = ''
        position = None
        chosen_letter = None

        for cell in self._get_possible_places():
            for letter in possible_letters:
                word = self._extend_search(letter, (cell,))
                if len(word) > len(self._longest_word):
                    self._longest_word = word
                    position = cell
                    chosen_letter = letter

        if not position:
            return None
        else:
            return position, chosen_letter, self._longest_word

    def _get_possible_places(self):
        places = []
        for i in range(len(self._game.field)):
            for j in range(len(self._game.field[0])):
                if not self._game.field[i][j] and (
                        (j < len(self._game.field[0]) - 1 and self._game.field[i][j+1]) or
                        (j > 0 and self._game.field[i][j-1]) or
                        (i < len(self._game.field) - 1 and self._game.field[i+1][j]) or
                        (i > 0 and self._game.field[i-1][j])
                ):
                    places.append((i, j))
        return places

    def _extend_search(self, letters, path, longest_lenght=0):
        longest_word = ''
        for cell in self._get_neighbors(path[-1]):
            letter = self._game.field[cell[0]][cell[1]]
            if cell not in path and letter:
                word = self._check_next_step(
                    letters + letter,
                    path + (cell, ),
                    longest_lenght
                )
                longest_word = self._get_longest(longest_word, word)

        for cell in self._get_neighbors(path[0]):
            letter = self._game.field[cell[0]][cell[1]]
            if cell not in path and letter:
                word = self._check_next_step(
                    letter + letters,
                    (cell,) + path,
                    longest_lenght
                )
                longest_word = self._get_longest(longest_word, word)

        return longest_word

    def _check_next_step(self, letters, path, longest_length=0):
        longest_word = ''
        hit, potential = self._game.vocabulary.check(letters)

        self._vocabulary_checks += 1

        if VocabularyAnswers.COMPLETE_FORWARD in hit and letters not in self._game.used_words:
            longest_word = self._get_longest(longest_word, letters)
        elif VocabularyAnswers.COMPLETE_BACKWARD in hit:
            backward = ''.join(reversed(letters))
            if backward not in self._game.used_words:
                longest_word = self._get_longest(longest_word, backward)

        if VocabularyAnswers.PART in hit:
            longest_length = max(len(self._longest_word), len(longest_word), longest_length)
            if potential > longest_length:
                word = self._extend_search(letters, path, longest_length)
                longest_word = self._get_longest(word, longest_word)

        return longest_word

    def _get_neighbors(self, cell):
        if cell[1] < len(self._game.field[0]) - 1:
            yield (cell[0], cell[1] + 1)
        if cell[1] > 0:
            yield (cell[0], cell[1] - 1)
        if cell[0] < len(self._game.field) -1:
            yield (cell[0] + 1, cell[1])
        if cell[1] > 0:
            yield (cell[0] - 1, cell[1])

    def _get_longest(self, a, b):
        if len(a) > len(b):
            return a
        else:
            return b


class Druz:

    def __init__(self, game):
        self._game = game

        self._vocabulary_checks = 0
        self._checked_starts = []
        self._words = defaultdict(lambda: defaultdict(list))
        self._known_letters = set()
        self._empty_border = defaultdict(lambda: defaultdict(list))
        self._just_visited = set()
        self._filled = set()

    @execution_time_log('Druz guess next')
    def guess_next(self):
        logger.debug(f'Memory usage: {process.memory_info().rss / 1000000}')
        self._vocabulary_checks = 0

        self._update_routes()
        return self._get_longest_available()

    def _update_routes(self):
        t1 = time.perf_counter()
        self._build_routes_for_new_cells()
        logger.debug(f'New cells time: {time.perf_counter() - t1}')
        t2 = time.perf_counter()
        self._update_existing_routes_with_new_letters()
        logger.debug(f'Existing routes time: {time.perf_counter() - t2}')

    def _build_routes_for_new_cells(self):
        initial_cells = self._get_new_initial_cells()

        to_remove = []
        for cell in self._checked_starts:
            if self.field[cell[0]][cell[1]] and cell in self._words:
                del self._words[cell]

        for cell in to_remove:
            del self._checked_starts[cell]

        for cell in initial_cells:
            self._checked_starts.append(cell)
            for letter in possible_letters:
                self._just_visited = set()
                self._build_route(cell, letter, letter, (cell,))

    def _get_new_initial_cells(self):
        filled = set()
        border = set()
        for i in range(len(self.field)):
            for j in range(len(self.field[0])):
                if self.field[i][j]:
                    filled.add((i, j))
                    if (i, j) not in self._filled:
                        for cell in self._get_neighbors((i, j)):
                            if not self.field[cell[0]][cell[1]]:
                                border.add(cell)
        self._filled = filled
        return border

    def _build_route(self, initial_cell, insert_letter, letters, path):
        self._just_visited.add(frozenset(path))
        hit = self._check_vocabulary(letters)

        if initial_cell == (1, 1):
            a = 1

        if VocabularyAnswers.COMPLETE_FORWARD in hit:
            self._words[initial_cell][insert_letter].append((letters, path))
        if VocabularyAnswers.COMPLETE_BACKWARD in hit:
            self._words[initial_cell][insert_letter].append((backward(letters), path))

        if VocabularyAnswers.PART in hit:
            for cell in self._get_neighbors(path[-1]):
                letter = self.field[cell[0]][cell[1]]
                if cell not in path:
                    if not letter:
                        self._empty_border[cell][initial_cell].append((insert_letter, letters, path))
                    else:
                        word = letters + letter
                        next_path = path + (cell,)
                        if frozenset(next_path) not in self._just_visited:
                            self._build_route(initial_cell, insert_letter, word, next_path)

            for cell in self._get_neighbors(path[0]):
                letter = self.field[cell[0]][cell[1]]
                if cell not in path:
                    if not letter:
                        self._empty_border[cell][initial_cell].append((insert_letter, letters, path))
                    else:
                        word = letter + letters
                        next_path = (cell,) + path
                        if frozenset(next_path) not in self._just_visited:
                            self._build_route(initial_cell, insert_letter, word, next_path)

    def _update_existing_routes_with_new_letters(self):
        i = 0
        to_remove = []
        for border, values in self._empty_border.items():
            if self.field[border[0]][border[1]]:
                for initial_cell, routes in values.items():
                    letter = ''
                    for route in routes:
                        if not self.field[initial_cell[0]][initial_cell[1]]:
                            i += 1
                            if letter != route[0]:
                                self._just_visited = set()
                                letter = route[0]
                            if (
                                        route[2][0][0] == border[0]
                                        and route[2][0][1] - border[1] in [1, -1]
                                    ) \
                                    or (
                                        route[2][0][1] == border[1]
                                        and route[2][0][0] - border[0] in [1, -1]
                                    ):
                                self._build_route(
                                    initial_cell,
                                    route[0],
                                    self.field[border[0]][border[1]] + route[1],
                                    (border, ) + route[2]
                                )
                            else:
                                self._build_route(
                                    initial_cell,
                                    route[0],
                                    route[1] + self.field[border[0]][border[1]],
                                    route[2] + (border, )
                                )
                to_remove.append(border)

        logger.debug(f'Existing routes rechecks: {i}')

        for cell in to_remove:
            del self._empty_border[cell]

    def _get_longest_available(self):
        longest = [None, '', '']
        for cell in self._words:
            for letter in self._words[cell]:
                for word in self._words[cell][letter]:
                    if word[0] not in self.used_words \
                            and len(word[1]) > len(longest[2]):
                        longest = (cell, letter, word[0])

        if longest[0]:
            return longest

    def _get_neighbors(self, cell):
        if cell[1] < len(self.field[0]) - 1:
            yield (cell[0], cell[1] + 1)
        if cell[1] > 0:
            yield (cell[0], cell[1] - 1)
        if cell[0] < len(self.field) -1:
            yield (cell[0] + 1, cell[1])
        if cell[0] > 0:
            yield (cell[0] - 1, cell[1])

    def _check_vocabulary(self, word):
        hit = self._game.vocabulary.check(word)
        self._vocabulary_checks += 1
        return hit
    
    @property
    def field(self):
        return self._game.field

    @property
    def used_words(self):
        return self._game.used_words


def longest(a, b):
    if len(a) > len(b):
        return a
    else:
        return b


def backward(word):
    return ''.join(reversed(word))


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(ch)

    class TestDruz(Druz):

        def __init__(self):
            self.test_vocabulary = Vocabulary()
            super().__init__(None)

        def _check_vocabulary(self, word):
            hit, potential = self.test_vocabulary.check(word)
            self._vocabulary_checks += 1
            return hit

        field = [
            ['С', '',  ''],
            ['Л', '',  ''],
            ['',  'В', ''],
        ]

        used_words = set()

    player = TestDruz()

    print(player.guess_next())

    pprint(player._empty_border)

    player.field = [
            ['С', '',  ''],
            ['Л', '',  ''],
            ['',  'В', 'О'],
        ]

    print(player.guess_next())

    pprint(player._empty_border)

    # logger.debug(f'Vocabulary checks: {player._vocabulary_checks}')

    # row = []
    # letter_places = player._get_possible_places()
    #
    # for i in range(len(field)):
    #     for j in range(len(field[0])):
    #         if (i, j) in letter_places:
    #             row.append('X')
    #         else:
    #             row.append(' ')
    #     print(row)
    #     row = []
    #
    # print(player.guess_next())
