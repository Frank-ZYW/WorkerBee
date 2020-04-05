# -*- coding: utf-8 -*-

import logging
import time
import requests
from scrapy import signals
from scrapy.exceptions import NotConfigured
from scrapy_redis import connection
from twisted.internet import reactor, task

logger = logging.getLogger(__name__)


class AutoClose(object):
    """
    This extensions can stop spider automatically when the request queue stay empty for a while.

    Only supports RedisSpider.
    """

    def __init__(self, crawler, idle_number):
        self.crawler = crawler
        self.idle_number = idle_number
        self.idle_list = []
        self.idle_count = 0
        crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)
        crawler.signals.connect(self.spider_opened, signal=signals.spider_opened)

    @classmethod
    def from_crawler(cls, crawler):
        if 'redis_key' not in crawler.spidercls.__dict__.keys():
            raise NotConfigured('Only supports RedisSpider')
        idle_number = crawler.settings.getint('WAIT_MIN', 10) * 12
        if not idle_number:
            raise NotConfigured
        return cls(crawler, idle_number)

    def spider_opened(self, spider):
        logger.info("Opened spider %s redis spider Idle, Continuous idle limit： %d", spider.name, self.idle_number)

    def spider_idle(self, spider):
        self.idle_count += 1
        self.idle_list.append(time.time())
        idle_list_len = len(self.idle_list)

        # Determine if redis_key exists in redis. If the key is used up, the key won't exist
        if idle_list_len > 2 and spider.server.exists(spider.redis_key):
            self.idle_list = [self.idle_list[-1]]
        elif idle_list_len > self.idle_number:
            msg = "Spider %s's continued idle number exceed %d Times, meet the idle shutdown conditions, will close."
            logger.info(msg % (spider.name, self.idle_number))
            self.crawler.engine.close_spider(spider, 'closespider_autoclose')


class AutoStart(object):
    """
    This extensions can add the start url to redis to start spider automatically.

    Only supports RedisSpider.
    """

    def __init__(self, crawler):
        self.redis_server = connection.from_settings(crawler.settings)
        crawler.signals.connect(self.spider_opened, signal=signals.spider_opened)

    @classmethod
    def from_crawler(cls, crawler):
        if 'redis_key' not in crawler.spidercls.__dict__.keys():
            raise NotConfigured('Only supports RedisSpider')
        return cls(crawler)

    def spider_opened(self, spider):
        self.redis_server.lpush(spider.redis_key, spider.start_url)
        logger.info("Add spider %s's start urls: %s" % (spider.name, spider.start_url))


class ClearRequests(object):
    """
    This extensions can clear the spider's request queue in Redis when it shutdown.

    Only supports RedisSpider.
    """

    def __init__(self, crawler):
        self.redis_server = connection.from_settings(crawler.settings)
        crawler.signals.connect(self.spider_closed, signal=signals.spider_closed)

    @classmethod
    def from_crawler(cls, crawler):
        if 'redis_key' not in crawler.spidercls.__dict__.keys():
            raise NotConfigured('Only supports RedisSpider')
        return cls(crawler)

    def spider_closed(self, spider):
        self.redis_server.delete(spider.name + ':requests')
        logger.info("Clear spider %s's request queue" % spider.name)


class Monitor(object):
    """
    This Extension can
    Forces spiders to be closed and report reason to the server after certain conditions are met.
    Feedback the spider's running stats and report to server.

    Feedback function only support PyHive.
    """

    MESSAGE = {
        'spidererror': 'made too much page parse function error',
        'itemerror': 'made too much item insert error',
        'timeout': 'reached the limit of max running time',
        'requestignore': 'ignored too many requests'
    }

    def __init__(self, crawler):
        self.timeout_task = None
        self.check_request_drop_task = None
        self.crawler = crawler
        self.close_on = {
            'spidererror': crawler.settings.getint('MONITOR_SPIDERERROR'),
            'itemerror': crawler.settings.getint('MONITOR_ITEMERROR'),
            'timeout': crawler.settings.getfloat('MONITOR_TIMEOUT'),
            'requestignore': crawler.settings.getint('MONITOR_REQUESTIGNORE')
        }

        # check request ignore supported by retry middleware
        if self.close_on.get('requestignore'):
            middlewares = crawler.settings.getdict('DOWNLOADER_MIDDLEWARES')
            retry_middleware = 'workerbee.downloadermiddlewares.RetryMiddleware'
            if retry_middleware not in middlewares.keys() or not middlewares[retry_middleware]:
                raise NotConfigured

        self.feedback = crawler.settings.getbool('MONITOR_FEEDBACK', True)
        self.server_api = crawler.settings.get('MONITOR_SERVER_API')
        if self.feedback and not self.server_api:
            raise NotConfigured

        if self.close_on.get('spidererror'):
            crawler.stats.set_value('spider_error_count', 0)
            crawler.signals.connect(self.spider_error, signal=signals.spider_error)
        if self.close_on.get('itemerror'):
            crawler.stats.set_value('item_error_count', 0)
            crawler.signals.connect(self.item_error, signal=signals.item_error)
        crawler.signals.connect(self.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(self.spider_closed, signal=signals.spider_closed)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def spider_error(self, failure, response, spider):
        self.crawler.stats.inc_value('spider_error_count')
        if self.crawler.stats.get_value('spider_error_count') == self.close_on['spidererror']:
            self.crawler.engine.close_spider(spider, 'closespider_spidererror')

    def item_error(self, item, response, spider):
        self.crawler.stats.inc_value('item_error_count')
        if self.crawler.stats.get_value('item_error_count') == self.close_on['itemerror']:
            self.crawler.engine.close_spider(spider, 'closespider_itemerror')

    def spider_opened(self, spider):
        if self.close_on.get('timeout'):
            self.timeout_task = reactor.callLater(
                self.close_on['timeout'] * 3600,
                self.crawler.engine.close_spider,
                spider, reason='closespider_timeout'
            )

        if self.close_on.get('requestignore'):
            self.check_request_drop_task = task.LoopingCall(self._check_ignore, spider)
            self.check_request_drop_task.start(10, now=True)  # once per 10 second

    def spider_closed(self, spider):
        timeout_task = getattr(self, 'timeout_task', False)
        if timeout_task and timeout_task.active():
            timeout_task.cancel()

        if self.check_request_drop_task.running:
            self.check_request_drop_task.stop()

        self._log_and_feedback(spider)

    def _check_ignore(self, spider):
        if self.crawler.stats.get_value('request_ignore_count', 0) > self.close_on['requestignore']:
            self.crawler.engine.close_spider(spider, 'closespider_requestignore')

    def _log_and_feedback(self, spider):
        close_type = self.crawler.stats.get_value('finish_reason').replace('closespider_', '')
        error = close_type in self.close_on.keys()
        msg = ('Spider %s has ' + self.MESSAGE[close_type] + ', closed') % spider.name if error else ""
        if error:
            logger.error(msg)

        page_received = self.crawler.stats.get_value('response_received_count', 0)
        page_ignored = self.crawler.stats.get_value('request_ignore_count', 0)
        page_parsed_error = self.crawler.stats.get_value('spider_error_count', 0)
        item_scraped = self.crawler.stats.get_value('item_scraped_count', 0)
        item_dropped = self.crawler.stats.get_value('item_dropped_count', 0)
        item_error = self.crawler.stats.get_value('item_error_count', 0)

        msg = "Spider %s totally\ncrawled %d pages, ignored %d pages, parsed fail %d pages, " \
              "scraped %d items, dropped %d items, error %d items"
        logger.info(msg % (spider.name, page_received, page_ignored, page_parsed_error,
                           item_scraped, item_dropped, item_error), extra={'spider': spider})

        if self.feedback:
            data = {
                'pageReceived': page_received, 'pageIgnored': page_ignored, 'pageError': page_parsed_error,
                'itemScraped': item_scraped, 'itemDropped': item_dropped, 'itemError': item_error,
                'error': error, 'msg': msg,
            }
            try:
                requests.post(self.server_api, data=data, timeout=5)
            except Exception as e:
                logger.error(e)
