#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# ----------------------------------------------------------
#     FileName: app.py
#       Author: wangdean
#        Email: wangdean@sowell-tech.com
#      Version: 0.0.1
#   LastChange: 2016-02-14 11:01
#         Desc:
#      History:
# ----------------------------------------------------------
"""

from tornado.web import URLSpec

from .handler import BaseHandler
from .errors import IllegalArgumentError

class ApiManager(object):
    """
        The tornado api manager

        You normally only need the table name to spawn your tornado routes
    """

    METHODS_READ = frozenset(['GET'])
    METHODS_MODIFY = frozenset(['POST', 'PUT'])
    METHODS_DELETE = frozenset(['DELETE'])
    METHODS_UPDATE = METHODS_READ | METHODS_MODIFY
    METHODS_ALL = METHODS_READ | METHODS_MODIFY | METHODS_DELETE

    def __init__(self, application):
        """
        Create an instance of the scarecrow engine

        :param application: is the tornado.web.Application object
        """
        self.application = application

    def create_api_blueprint(self,
                             table_name,
                             methods=METHODS_READ,
                             preprocessor=None,
                             postprocessor=None,
                             url_prefix='/api',
                             collection_name=None,
                             allow_patch_many=False,
                             allow_method_override=False,
                             validation_exceptions=None,
                             exclude_queries=False,
                             exclude_hybrids=False,
                             include_columns=None,
                             exclude_columns=None,
                             results_per_page=10,
                             max_results_per_page=100,
                             blueprint_prefix='',
                             handler_class=BaseHandler):
        """
        Create a tornado route for a sqlalchemy model

        :param table_name:
        :param methods: Allowed methods for this model
        :param url_prefix: The url prefix of the application
        :param collection_name:
        :param allow_patch_many: Allow PATCH with multiple datasets
        :param allow_method_override: Support X-HTTP-Method-Override Header
        :param validation_exceptions:
        :param exclude_queries: Don't execude dynamic queries (like from associations or lazy relations)
        :param exclude_hybrids: When exclude_queries is True and exclude_hybrids is False, hybrids are still included.
        :param include_columns: Whitelist of columns to be included
        :param exclude_columns: Blacklist of columns to be excluded
        :param results_per_page: The default value of how many results are returned per request
        :param max_results_per_page: The hard upper limit of resutest per page
        :param blueprint_prefix: The Prefix that will be used to unique collection_name for named_handlers
        :param preprocessor: A dictionary of list of preprocessors that get called
        :param postprocessor: A dictionary of list of postprocessor that get called
        :param handler_class: The Handler Class that will be used in the route
        :type handler_class: tornado_restless.handler.BaseHandler or a subclass
        :return: :class:`tornado.web.URLSpec`
        :raise: IllegalArgumentError
        """
        if exclude_columns is not None and include_columns is not None:
            raise IllegalArgumentError('Cannot simultaneously specify both include columns and exclude columns.')

        regex = "%s/%s(?:/(.+))?[/]?" % (url_prefix, table_name)
        application_name = '%s%s' % (blueprint_prefix, table_name)
        kwargs = {'table_name': table_name,
                  'manager': self,
                  'methods': methods,
                  'preprocessor': preprocessor or {},
                  'postprocessor': postprocessor or {},
                  'allow_patch_many': allow_patch_many,
                  'allow_method_override': allow_method_override,
                  'validation_exceptions': validation_exceptions,
                  'include_columns': include_columns,
                  'exclude_columns': exclude_columns,
                  'exclude_queries': exclude_queries,
                  'exclude_hybrids': exclude_hybrids,
                  'results_per_page': results_per_page,
                  'max_results_per_page': max_results_per_page,
                  'regex': regex,
                  'application_name': application_name}

        blueprint = URLSpec(
            regex,
            handler_class,
            kwargs,
            application_name)
        return blueprint

    def create_api(self,
                   table_name,
                   virtualhost=r".*$", *args, **kwargs):
        """
        Creates and registers a route for the model in your tornado application

        The positional and keyword arguments are passed directly to the create_api_blueprint method

        :param table_name:
        :param virtualhost: bindhost for binding, .*$ in default
        """
        blueprint = self.create_api_blueprint(table_name, *args, **kwargs)

        for vhost, handlers in self.application.handlers:
            if vhost == virtualhost:
                handlers.append(blueprint)
                break
        else:
            self.application.add_handlers(virtualhost, [blueprint])

        self.application.named_handlers[blueprint.name] = blueprint