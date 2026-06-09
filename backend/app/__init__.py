"""Monkey-patch httpx compatibility for openai SDK."""
import httpx

_original_init = httpx.AsyncClient.__init__


def _patched_init(self, *args, **kwargs):
    kwargs.pop("proxies", None)
    _original_init(self, *args, **kwargs)


httpx.AsyncClient.__init__ = _patched_init
