import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def execution_time_log(description):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start
            logger.debug(f'{description}. Duration: {duration}')
            return result

        return wrapper
    return decorator


def change_encoding():
    file = 'Полная парадигма. Морфология.txt'
    with open(file, encoding='cp1251') as fp:
        with open(file + '2.txt', 'wt') as result_fp:
            while True:
                buffer = fp.read(1024 * 16)
                if not buffer:
                    break
                result_fp.write(buffer)


def prepare_words():
    file = 'Полная парадигма. Морфология.txt2.txt'
    with open(file) as fp:
        with open('words.txt', 'wt') as words_fp:
            for row in fp:
                if '|' in row:
                    word, params, counter = row.split('|')
                    params = params.split(' ')
                    if 'сущ' in params and 'ед' in params and 'им' in params:
                        words_fp.write(word.strip() + '\n')


if __name__ == '__main__':
    change_encoding()
    prepare_words()
