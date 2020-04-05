# -*- coding: utf-8 -*-

import weakref
import hashlib
from scrapy.utils.python import to_bytes

_fingerprint_cache = weakref.WeakKeyDictionary()


def request_fingerprint(request, include_headers=None):
    """
    Use hash function to compress the request into a fingerprint
    :param request: scrapy.Request
    :param include_headers: http header, default none
    :return: a 40-character string which include 0~f
    """
    if include_headers:
        include_headers = tuple(to_bytes(h.lower()) for h in sorted(include_headers))
    cache = _fingerprint_cache.setdefault(request, {})
    if include_headers not in cache:
        fp = hashlib.sha1()
        fp.update(to_bytes(request.method))
        fp.update(to_bytes(request.url))
        fp.update(request.body or b'')
        if include_headers:
            for hdr in include_headers:
                if hdr in request.headers:
                    fp.update(hdr)
                    for v in request.headers.getlist(hdr):
                        fp.update(v)
        cache[include_headers] = fp.hexdigest()
    return cache[include_headers]
