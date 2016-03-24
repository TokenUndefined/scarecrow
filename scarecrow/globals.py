#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# ----------------------------------------------------------
#     FileName: globals.py
#       Author: wangdean
#        Email: wangdean@sowell-tech.com
#      Version: 0.0.1
#   LastChange: 2016-03-09 16:03
#         Desc: Defines all the global objects that are proxies to the current
#               active context.
#      History:
# ----------------------------------------------------------
"""

import sys,os
import logging
import tornado.web
from tornado.options import define, options
from sqlalchemy.pool import NullPool
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
define("db", default='create', help="setting the data base operation.", type=str)

def parse_command_line(args=None, options_dict=None):
    if args is None:
        args = sys.argv

    if options_dict is None:
        options_dict = options.as_dict()

    for i in range(1, len(args)):
        # All things after the last option are command line arguments
        if not args[i].startswith("-"):
            break
        arg = args[i].lstrip("-")
        name, equals, value = arg.partition("=")

        if options_dict.has_key(name) and options_dict.get(name)!=value:
            setattr(options, name, value)

def _get_alchemy_object(connector):
    """
    Base on the sql connector, set up the Alchemy object.

    :param connector: SQL connector
    :return:
    """

    parse_command_line()

    # Create or Drop a Database.
    database = connector.split('/')[-1]
    engine   = create_engine(connector.replace(database, ''), echo=False)
    session  = sessionmaker(bind=engine)()
    session.connection().connection.set_isolation_level(0)
    if options.db in ('create', 'drop'):
        try:
            if options.db=='create':
                session.execute('CREATE DATABASE %s' % database)
            else:
                session.execute('DROP DATABASE %s' % database)
        except:
            exc_type, exc_value = sys.exc_info()[:2]
            logging.error('DATABASE Exception: %s' % exc_value)
    else:
        logging.warning('Unrecognized operation[%s].' % options.db)

    if options.db not in ('create'):
        exit()

    # Init SQLAlchemy engine.
    engine  = create_engine(connector, echo=False, poolclass=NullPool, pool_recycle=3600)
    metadata= MetaData(engine)
    Base    = declarative_base(metadata=metadata)
    Session = scoped_session(sessionmaker(bind=engine))
    return Base, Session, engine

secret_key  = os.environ.get('SECRET_KEY', os.urandom(32))
attribute   = 'scarecrow'
connector   = 'postgresql://postgres@localhost/scarecrow'
running_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
Base, Session, engine = _get_alchemy_object(connector)
