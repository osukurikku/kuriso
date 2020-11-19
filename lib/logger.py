import logging

PINK = '\033[95m'
BLUE = '\033[94m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'

logging.basicConfig(format='[%(asctime)s] %(message)s',
                    filemode='at',
                    filename='kuriso.log',
                    level=logging.INFO)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


def printColored(string: str, color: str):
    logging.info("%s%s%s", color, string, ENDC)


def klog(msg: str):  # kuriso log
    printColored(msg, PINK)


def elog(msg: str):  # error log
    printColored(msg, RED)


def wlog(msg: str):  # warning log
    printColored(msg, YELLOW)


def slog(msg: str):  # success log
    printColored(msg, GREEN)
