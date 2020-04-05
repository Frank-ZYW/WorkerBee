# -*- coding: utf-8 -*-

from scrapy_redis.dupefilter import RFPDupeFilter

from workerbee.request import request_fingerprint


class SimpleHash(object):
    def __init__(self, cap, seed):
        self.cap = cap
        self.seed = seed

    def hash(self, value):
        ret = 0
        for i in range(len(value)):
            ret += self.seed * ret + ord(value[i])
        return (self.cap - 1) & ret


class BloomFilter(object):
    """
    Bloom Filter
    """

    def __init__(self, redis_server, blocknum=1, key='bloomfilter'):
        """
        :param redis_server: Redis client instance
        :param blocknum: one blockNum for about 90,000,000; if you have more strings for filtering, increase it.
        :param key: the key's name in Redis
        """
        self.server = redis_server
        # max size of Redis String is 512M, now use 256M
        self.bit_size = 1 << 31
        self.seeds = [5, 7, 11, 13, 31, 37, 61]
        self.key = key
        self.blockNum = blocknum
        self.hashfunc = []
        for seed in self.seeds:
            self.hashfunc.append(SimpleHash(self.bit_size, seed))

    def isContains(self, str_input):
        """
        return True if already exist else False
        """
        if not str_input:
            return False
        key = self.key + str(int(str_input[0:2], 16) % self.blockNum)
        bitfield_operation = self.server.bitfield(key)
        for f in self.hashfunc:
            bitfield_operation.get('u1', f.hash(str_input))
        return all(self.server.execute_command(*bitfield_operation.command))

    def insert(self, str_input):
        """
        return True if already exist else False
        """
        key = self.key + str(int(str_input[0:2], 16) % self.blockNum)
        bitfield_operation = self.server.bitfield(key)
        for f in self.hashfunc:
            bitfield_operation.set('u1', f.hash(str_input), 1)
        return all(self.server.execute_command(*bitfield_operation.command))


class RFPDupeFilterAlter(RFPDupeFilter):
    """
    Alter Redis-based request duplicates filter (RFPDupeFilter).
    This class can also be used with default scrapy-redis's scheduler.
    """

    def request_seen(self, request):
        """
        Returns True if request was already seen.
        Parameters
        ----------
        request : scrapy.http.Request
        Returns
        -------
        bool
        """
        fp = request_fingerprint(request)

        # This returns the number of values ismember, one if already exists
        ismember = self.server.sismember(self.key, fp)
        return ismember
