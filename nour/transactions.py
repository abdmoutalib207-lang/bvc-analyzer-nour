"""Build in isolation, then atomically exchange complete local site generations."""
from contextlib import contextmanager
import ctypes
import errno
import os
from pathlib import Path
import shutil
import tempfile
import time
from urllib.error import HTTPError, URLError

from .resilience import GlobalIntegrityError


def retry_transient(function, attempts=3, wait=time.sleep):
    if not 1 <= attempts <= 4:
        raise ValueError('Retry bound must be 1..4')
    for n in range(attempts):
        try:
            return function()
        except HTTPError as exc:
            if exc.code not in (408,429,500,502,503,504) or n == attempts-1:
                raise
        except (URLError, TimeoutError, ConnectionError):
            if n == attempts-1:
                raise
        wait(min(2, .25*2**n))


def exchange(stage, target):
    if not target.exists():
        os.replace(stage,target)
        return
    # renameat2(RENAME_EXCHANGE) has no interval with a missing/half-written site.
    libc = ctypes.CDLL(None, use_errno=True)
    function = getattr(libc, 'renameat2', None)
    if function is None:
        raise GlobalIntegrityError('Échange atomique de répertoires indisponible ; ancien site conservé')
    function.argtypes = [ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    function.restype = ctypes.c_int
    if function(-100, os.fsencode(stage), -100, os.fsencode(target), 2):
        code = ctypes.get_errno()
        raise GlobalIntegrityError('Échange atomique refusé ; ancien site conservé : '+os.strerror(code))


@contextmanager
def site_transaction(target):
    target = Path(target)
    stage = Path(tempfile.mkdtemp(prefix='.nour-stage-',dir=target.parent))
    try:
        if target.exists():
            shutil.copytree(target,stage,dirs_exist_ok=True)
        yield stage
        exchange(stage,target)
    finally:
        # After an exchange, stage contains the complete previous generation.
        # Git/Pages keeps its published history; an interrupted build never swaps.
        if stage.exists():
            shutil.rmtree(stage)
