import math
import time
from typing import List

def calculate_standard_deviation(mrts: List[float]) -> float:

    n = len(mrts)
    if n == 0:
        return 0.0
    mean = sum(mrts) / n
    variance = sum((x - mean) ** 2 for x in mrts) / n
    return math.sqrt(variance)

def register_time(received_message: str) -> str:

    parts = received_message.rstrip(';').split(';')
    last_ts = int(parts[-1])
    now = int(time.time() * 1000)
    delta = now - last_ts
    return f"{received_message}{now};{delta};"
