# -*- coding: utf-8 -*-

import MySQLdb
import logging
from twisted.enterprise import adbapi
from scrapy_redis import connection
from scrapy.exceptions import DropItem

from workerbee.request import request_fingerprint
from workerbee.filter import BloomFilter

logger = logging.getLogger(__name__)


class MysqlPipeline(object):
    """
    Pushes serialized item into Mysql DB
    """

    def __init__(self, redis_server, mysql_pool, table, upsert, blocknum):
        """
        Initialize pipeline.
        :param redis_server: Redis client instance
        :param mysql_pool: Mysql connection pool
        :param table: Mysql table to save item
        :param upsert: True if use update or create to add data & avoid data filter
        """
        self.redis_server = redis_server
        self.bloomfilter = BloomFilter(redis_server, blocknum=blocknum)
        self.mysql_pool = mysql_pool
        self.table = table
        self.upsert = upsert

    @classmethod
    def from_settings(cls, settings):
        params = {
            'redis_server': connection.from_settings(settings),
            'mysql_pool': adbapi.ConnectionPool(
                'MySQLdb',
                host=settings.get('MYSQL_HOST', 'localhost'),
                port=settings.getint('MYSQL_PORT', 3306),
                user=settings.get('MYSQL_USER', 'root'),
                passwd=settings.get('MYSQL_PASSWORD'),
                db=settings.get('MYSQL_DB'),
                charset=settings.get('MYSQL_CHARSET', 'utf8'),
            ),
            'table': settings.get('MYSQL_TABLE'),
            'upsert': settings.getbool('MYSQL_UPSERT', False),
            'blocknum': settings.getint('REDIS_BLOCKNUM', 2)
        }
        return cls(**params)

    @classmethod
    def from_crawler(cls, crawler):
        return cls.from_settings(crawler.settings)

    def process_item(self, item, spider):
        return self.mysql_pool.runInteraction(self._process_item, item, spider)

    def _process_item(self, tb, item, spider):
        request = item.pop('request', None)
        item_fingerprint = item.fingerprint()
        data_exist = True
        if self.upsert or not self.bloomfilter.isContains(item_fingerprint):
            sql, values = self._generate_sql(item)
            try:
                tb.execute(sql, values)
            except MySQLdb.IntegrityError as e:
                logger.debug(e)
            else:
                data_exist = False
                self.bloomfilter.insert(item_fingerprint)
        self._add_fingerprint(request, spider.name)
        if data_exist:
            raise DropItem
        return item

    def _generate_sql(self, data):
        def columns(d):
            return ', '.join(['`{}`'.format(k) for k in d])

        def values(d):
            return [v for v in d.values()]

        def placeholders(d):
            return ', '.join(['%s'] * len(d))

        def on_duplicate_placeholders(d):
            return ', '.join(['`{}` = %s'.format(k) for k in d])

        if self.upsert:
            sql_template = 'INSERT INTO `{}` ( {} ) VALUES ( {} ) ON DUPLICATE KEY UPDATE {}'
            return (
                sql_template.format(
                    self.table,
                    columns(data),
                    placeholders(data),
                    on_duplicate_placeholders(data)
                ),
                values(data) + values(data)
            )
        else:
            sql_template = 'INSERT INTO `{}` ( {} ) VALUES ( {} )'
            return (
                sql_template.format(
                    self.table,
                    columns(data),
                    placeholders(data)
                ),
                values(data)
            )

    def _add_fingerprint(self, request, spider_name):
        if request and not request.dont_filter:
            fp = request_fingerprint(request)
            self.redis_server.sadd(spider_name + ':dupefilter', fp)

    def close_spider(self, spider):
        self.mysql_pool.close()
