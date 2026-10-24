import re
import threading

from django.conf import settings
from django.contrib.auth.hashers import Argon2PasswordHasher


class _MemoryBudget:
    """Lets password hashes run concurrently only while their combined Argon2 memory fits the
    budget; the rest wait their turn (milliseconds each)."""

    def __init__(self, kib: int):
        self.total = kib
        self.free = kib
        self.cond = threading.Condition()

    def acquire(self, kib: int) -> int:
        kib = min(kib, self.total)  # one oversized hash may still run, alone
        with self.cond:
            self.cond.wait_for(lambda: self.free >= kib)
            self.free -= kib
        return kib

    def release(self, kib: int):
        with self.cond:
            self.free += kib
            self.cond.notify_all()


_budget = _MemoryBudget(getattr(settings, "PASSWORD_HASH_MEMORY_MB", 128) * 1024)
_MEMORY_PARAM = re.compile(r"\$m=(\d+),")


class BoundedArgon2PasswordHasher(Argon2PasswordHasher):
    """
    Argon2id at OWASP's recommended minimum (19 MiB, 2 passes, 1 lane) instead of Django's default
    (100 MiB, 8 lanes), which let ~5 simultaneous sign-ins exhaust a 512 MB server. Hashes run
    within a memory budget, so bursts of sign-ins queue briefly instead of running out of memory.

    It keeps the "argon2" identifier, so existing hashes still verify (within the budget, at their
    original cost); Django re-hashes them with these parameters the next time each person signs in.
    """

    time_cost = 2
    memory_cost = 19 * 1024
    parallelism = 1

    def encode(self, password, salt):
        held = _budget.acquire(self.memory_cost)
        try:
            return super().encode(password, salt)
        finally:
            _budget.release(held)

    def verify(self, password, encoded):
        found = _MEMORY_PARAM.search(encoded or "")
        held = _budget.acquire(int(found.group(1)) if found else self.memory_cost)
        try:
            return super().verify(password, encoded)
        finally:
            _budget.release(held)
