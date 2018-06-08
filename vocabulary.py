import logging
import pickle
import random
import time
import traceback
from collections import defaultdict
from enum import Flag, auto
from pathlib import Path

from bloom_filter import BloomFilter

from words.utils import execution_time_log


logger = logging.getLogger(__name__)


class VocabularyAnswers(Flag):
    MISSING = auto()
    PART = auto()
    COMPLETE_FORWARD = auto()
    COMPLETE_BACKWARD = auto()


_RAW_WORDS_PATH = Path(__file__).parent / 'words.txt'
_VOCABULARY_PATH = Path(__file__).parent / 'words.pkl'


class Vocabulary:

    @execution_time_log('Init vocabulary')
    def __init__(self):
        try:
            self._words, self._parts = pickle.load(_VOCABULARY_PATH.open('rb'))
        except Exception:
            logger.warning('Vocabulary unpickling error: \n' + traceback.format_exc())
            self._build_from_file()
            pickle.dump((self._words, self._parts), _VOCABULARY_PATH.open('wb'))

    def _build_from_file(self):
        self._words = set()
        for word in open(_RAW_WORDS_PATH):
            self._words.add(word.strip().upper())
            # self._words.add(bytes([ord(x) - 1040 for x in word.strip().upper()]))

        self._parts = defaultdict(int)
        for word in self._words:
            for i in range(1, len(word)):
                for j in range(len(word) - i + 1):
                    part = word[j: j+i]
                    self._parts[part] = max(self._parts[part], len(word))
                    rev = ''.join(reversed(part))
                    self._parts[rev] = max(self._parts[rev], len(word))

    # @execution_time_log('Vocabulary check')
    def check(self, checking_word):
        result = VocabularyAnswers.MISSING
        reversed_word = ''.join(reversed(checking_word))

        if checking_word in self._words:
            result |= VocabularyAnswers.COMPLETE_FORWARD
        if reversed_word in self._words:
            result |= VocabularyAnswers.COMPLETE_BACKWARD

        potential = None
        if checking_word in self._parts:
            # logger.debug(f'Part: {checking_word}')
            result |= VocabularyAnswers.PART
            potential = self._parts[checking_word]

        return result, potential

    def get_word(self, length):
        words = []
        for word in self._words:
            if len(word) == length:
                words.append(word)

        return random.choice(words)


class DiskVocabulary:

    @execution_time_log('Init vocabulary')
    def __init__(self):
        try:
            self._words, self._parts = pickle.load(_VOCABULARY_PATH.open('rb'))
            raise Exception()
        except Exception:
            logger.warning('Vocabulary unpickling error: \n' + traceback.format_exc())
            self._build_from_file()
            pickle.dump((self._words, self._parts), _VOCABULARY_PATH.open('wb'))

    def _build_from_file(self):
        self._words = set()
        self._parts = set()

        for word in open(_RAW_WORDS_PATH):
            word = word.strip().upper()
            # self._words.add(word.strip().upper())
            self._words.add(sum([34 ** i * (ord(x) - 1039) for i, x in enumerate(word)]))

            for i in range(1, len(word)):
                for j in range(len(word) - i + 1):
                    part = word[j: j+i]
                    self._parts.add(sum([34 ** i * (ord(x) - 1039) for i, x in enumerate(part)]))


    # @execution_time_log('Vocabulary check')
    def check(self, checking_word):
        reversed_word = ''.join(reversed(checking_word))
        checking_word = sum([34 ** i * (ord(x) - 1039) for i, x in enumerate(checking_word)])
        result = VocabularyAnswers.MISSING
        reversed_word = sum([34 ** i * (ord(x) - 1039) for i, x in enumerate(reversed_word)])

        if checking_word in self._words:
            result |= VocabularyAnswers.COMPLETE_FORWARD
        if reversed_word in self._words:
            result |= VocabularyAnswers.COMPLETE_BACKWARD

        if checking_word in self._parts:
            # logger.debug(f'Part: {checking_word}')
            result |= VocabularyAnswers.PART

        return result

    def get_word(self, length):
        words = []
        for word in self._words:
            if len(word) == length:
                words.append(word)

        return random.choice(words)


class BloomVocabulary:

    @execution_time_log('Init vocabulary')
    def __init__(self):
        self.words_bloom = BloomFilter(max_elements=64_000, error_rate=0.000001)
        self.parts_bloom = BloomFilter(max_elements=700_000, error_rate=0.000001)

        try:
            self.words_bloom, self.parts_bloom = pickle.load(_VOCABULARY_PATH.open('rb'))
        except Exception:
            logger.warning('Vocabulary unpickling error: \n' + traceback.format_exc())
            self._build_from_file()
            pickle.dump((self.words_bloom, self.parts_bloom), _VOCABULARY_PATH.open('wb'))

    def _build_from_file(self):
        for word in open(_RAW_WORDS_PATH):
            word = word.strip().upper()
            self.words_bloom.add(word.strip().upper())

            for i in range(1, len(word)):
                for j in range(len(word) - i + 1):
                    part = word[j: j+i]
                    self.parts_bloom.add(part.strip().upper())

    # @execution_time_log('Vocabulary check')
    def check(self, checking_word):
        reversed_word = ''.join(reversed(checking_word))
        result = VocabularyAnswers.MISSING

        if checking_word.upper() in self.words_bloom:
            result |= VocabularyAnswers.COMPLETE_FORWARD
        if reversed_word.upper() in self.words_bloom:
            result |= VocabularyAnswers.COMPLETE_BACKWARD
        if checking_word.upper() in self.parts_bloom:
            result |= VocabularyAnswers.PART

        return result


if __name__ == '__main__':
    import os
    import psutil

    process = psutil.Process(os.getpid())

    logger = logging.getLogger('words')
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(ch)

    print(f'Memory usage: {process.memory_info().rss / 1000000}')

    vocabulary = BloomVocabulary()

    # from pprint import pprint
    # pprint(vocabulary._parts)

    print(vocabulary.check('ТЮЛЕН'))
    print(vocabulary.check('БАРА'))
    print(vocabulary.check('СЛОВО'))
    print(vocabulary.check('ЛЮ'))
    print(vocabulary.check('ОРОТАВАКСКЭВ'))

    print(f'Memory usage: {process.memory_info().rss / 1000000:,}')

