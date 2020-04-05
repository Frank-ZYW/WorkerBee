# -*- coding: utf-8 -*-

import scrapy
from abc import ABC, abstractmethod


class Item(scrapy.Item, ABC):
    """
    WorkBee Item
    """

    # save the request of item
    request = scrapy.Field()

    # return fingerprint of item
    # abstractmethod ! Must be overload in the Subclass
    @abstractmethod
    def fingerprint(self):
        pass

    # define the way to make fingerprint of item
    # abstractmethod ! Must be overload in the Subclass
    @abstractmethod
    def make_fingerprint(self):
        pass
