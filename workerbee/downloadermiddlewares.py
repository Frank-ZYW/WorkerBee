# -*- coding: utf-8 -*-

from scrapy import signals
from scrapy.exceptions import IgnoreRequest
from scrapy.core.downloader.handlers.http11 import TunnelError
from twisted.internet import defer
from twisted.web.client import ResponseFailed
from twisted.internet.error import TimeoutError, DNSLookupError, ConnectionRefusedError, ConnectionDone, ConnectError,\
    ConnectionLost, TCPTimedOutError
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class RetryMiddleware(object):

    EXCEPTIONS_TO_RETRY = (
        defer.TimeoutError, TimeoutError, DNSLookupError, ConnectionRefusedError,
        ConnectionDone, ConnectError, ConnectionLost, TCPTimedOutError,
        ResponseFailed, IOError, TunnelError, IgnoreRequest
    )

    def __init__(self, crawler):
        self.crawler = crawler
        self.max_retry_times = crawler.settings.getint('RETRY_TIMES')
        self.retry_http_codes = set(int(x) for x in crawler.settings.getlist('RETRY_HTTP_CODES'))
        crawler.signals.connect(self.spider_opened, signal=signals.spider_opened)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def spider_opened(self, spider):
        self.crawler.stats.set_value('request_ignore_count', 0)

    def process_response(self, request, response, spider):
        if request.meta.get('dont_retry', False):
            return response
        if response.status in self.retry_http_codes:
            return self._retry(request, spider) or response
        return response

    def process_exception(self, request, exception, spider):
        if isinstance(exception, self.EXCEPTIONS_TO_RETRY):
            return self._retry(request, spider)

    def _retry(self, request, spider):
        """
        Retry the request if the limit is not reached or ignore the request
        :return: new Request or None
        """
        if not request.meta.get('dont_retry', False):
            retries = request.meta.get('retry_times', 0) + 1
            # retry
            if retries < self.max_retry_times:
                retryreq = request.copy()
                retryreq.meta['retry_times'] = retries
                return retryreq
        # ignore
        self.crawler.stats.inc_value('request_ignore_count')
        spider.logger.warning("Page Loading Failed: %s , gave up" % request.url)


class SeleniumChromeMiddleware(object):

    def __init__(self, crawler):
        # create a headless browser
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument('--no-sandbox')

        proxy = crawler.settings.get('SELENIUM_PROXY')
        if proxy:
            options.add_argument("-proxy-server=%s" % proxy)
        self.browser = webdriver.Chrome(options=options)

    def __del__(self):
        self.browser.quit()
