import logging

PINK = "\033[95m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
ENDC = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.FileHandler("kuriso.log", "at", "utf-8")
handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))

logger.addHandler(handler)

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)


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
