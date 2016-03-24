#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

"""

import logging
import importlib
from tornado.log import LogFormatter as _LogFormatter
from .globals import secret_key, running_dir, Base, Session, engine, attribute

from .api import  ApiManager
from .wrapper import BaseWrapper, AlchemyWrapper
from tornado_rbac import RBAC, AccessControl, recordOpt


__version__ = '0.7.1'
__all__     = [ApiManager, BaseWrapper, AlchemyWrapper, RBAC, AccessControl]

class LogFormatter(_LogFormatter, object):
    """Init tornado.log.LogFormatter from logging.config.fileConfig"""
    def __init__(self, **kwargs):
        if kwargs.get('fmt') is None:
            kwargs['fmt'] = '%(color)s[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d]%(end_color)s %(message)s'
        if kwargs.get('datefmt') is None:
            kwargs['datefmt'] = '%y%m%d %H:%M:%S'
        super(LogFormatter, self).__init__(**kwargs)

logger = logging.getLogger()
channel= logging.StreamHandler()
channel.setFormatter(LogFormatter())
logger.addHandler(channel)

from sqlalchemy.orm.session import Session
from sqlalchemy.event import listen
from sqlalchemy import orm

def AlchemyJSON(obj_dict):
    return dict((key, obj_dict[key]) for key in obj_dict if not key.startswith("_"))

class _SessionSignalEvents(object):

    def __init__(self):
        self.session = Session

    def register(self):
        listen(self.session, 'after_bulk_update', self.receive_after_bulk_update)
        listen(self.session, 'after_bulk_delete', self.receive_after_bulk_delete)

    def receive_after_bulk_update(self, session, query, query_context, result):
        "listen for the ’after_bulk_update’ event"
        affected_table = query_context.statement.froms[0].name
        affected_rows  = query_context.statement.execute()
        print "receive_after_bulk_update", affected_rows, affected_table

    def receive_after_bulk_delete(self, session, query, query_context, result):
        "listen for the ’after_bulk_delete’ event"
        affected_table = query_context.statement.froms[0].name
        affected_rows  = query_context.statement.execute()
        print "receive_after_bulk_delete", affected_rows, affected_table
        # thread.start_new_thread(preprocessor, ('delete', affected_table, affected_rows))

class _MapperSignalEvents(object):

    def __init__(self, mapper):
        self.mapper = mapper

    def register(self):
        listen(self.mapper, 'after_delete', self.mapper_signal_after_delete)
        listen(self.mapper, 'after_insert', self.mapper_signal_after_insert)
        listen(self.mapper, 'after_update', self.mapper_signal_after_update)

    def mapper_signal_after_delete(self, mapper, connection, target):
        self._record(mapper, target, 'delete')

    def mapper_signal_after_insert(self, mapper, connection, target):
        self._record(mapper, target, 'insert')

    def mapper_signal_after_update(self, mapper, connection, target):
        self._record(mapper, target, 'update')

    @staticmethod
    def _record(mapper, target, operation):
        print("_MapperSignalEvents:op=%s, table_name=%s, json=%s" % (operation, mapper.local_table.name, AlchemyJSON(target.__dict__)))

# this must happen only once
# _SessionSignalEvents().register()
# _MapperSignalEvents(orm.mapper).register()

# Dynamic loading the models module.
importlib.import_module('models')# imp.load_module('models', *imp.find_module('models'))
Base.metadata.create_all(engine)

