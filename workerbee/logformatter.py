# -*- coding: utf-8 -*-

import logging
from scrapy import logformatter


class PoliteLogFormatter(logformatter.LogFormatter):
    """
    Modify how DropItem(Exception) display in the log
    """

    def dropped(self, item, exception, response, spider):
        return {
            'level': logging.DEBUG,
            'msg': logformatter.DROPPEDMSG,
            'args': {
                'exception': exception,
                'item': item,
            }
        }
