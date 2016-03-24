#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# ----------------------------------------------------------
#     FileName: handler.py
#       Author: wangdean
#        Email: wangdean@sowell-tech.com
#      Version: 0.0.1
#   LastChange: 2016-02-22 16:11
#         Desc:
#      History:
# ----------------------------------------------------------
"""

import inspect
import uuid
import logging

import scarecrow
from json import loads, JSONEncoder, dumps
from math import ceil
from traceback import print_exception
from datetime import date, datetime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import UnmappedInstanceError
from sqlalchemy.util import memoized_instancemethod
from tornado.web import RequestHandler, HTTPError
from tornado.options import options

from .errors import IllegalArgumentError, MethodNotAllowedError, ProcessingException
from .wrapper import AlchemyWrapper, BaseWrapper

class DateTimeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        else:
            return JSONEncoder.default(self, obj)

class BaseHandler(RequestHandler):
    """
        Basic Blueprint for a sqlalchemy model

        Subclass of:class:`tornado.web.RequestHandler` that handles web requests.
        Overwrite  :func:`get() <get>`
                    func:`post() <post>`
                    func:`put() <put>`
                    func:`delete() <delete>`
    """

    SPRIT = "/"
    ID_SEPARATOR = ","
    SUPPORTED_METHODS = ['GET', 'POST', 'PUT', 'DELETE']

    # noinspection PyMethodOverriding
    def initialize(self,
                   table_name,
                   methods,
                   manager,
                   preprocessor,
                   postprocessor,
                   allow_patch_many,
                   allow_method_override,
                   validation_exceptions,
                   exclude_queries,
                   exclude_hybrids,
                   include_columns,
                   exclude_columns,
                   results_per_page,
                   max_results_per_page,
                   regex,
                   application_name):
        """

        Init of the handler, derives arguments from api create_api_blueprint

        :param table_name:
        :param methods: Allowed methods for this model
        :param manager: The Scarecrow Api Manager
        :param preprocessor: A dictionary of preprocessor functions
        :param postprocessor: A dictionary of postprocessor functions
        :param allow_patch_many: Allow PATCH with multiple datasets
        :param allow_method_override: Support X-HTTP-Method-Override Header
        :param validation_exceptions:
        :param exclude_queries: Don't execude dynamic queries (like from associations or lazy relations)
        :param exclude_hybrids: When exclude_queries is True and exclude_hybrids is False, hybrids are still included.
        :param include_columns: Whitelist of columns to be included
        :param exclude_columns: Blacklist of columns to be excluded
        :param results_per_page: The default value of how many results are returned per request
        :param max_results_per_page: The hard upper limit of resutest per page
        :reqheader X-HTTP-Method-Override: If allow_method_override is True, this header overwrites the request method
        """

        # Override Method if Header provided
        if allow_method_override and 'X-HTTP-Method-Override' in self.request.headers:
            self.request.method = self.request.headers['X-HTTP-Method-Override']

        super(BaseHandler, self).initialize()
        self.table_name = table_name
        self.instance = AlchemyWrapper(table_name)

        self.application_name = application_name
        self.regex = regex
        if not self.regex.endswith('$'):
            self.regex += '$'

        self.attribute = getattr(options, "attribute", "scarecrow")
        self.node_code = str(uuid.uuid3(uuid.NAMESPACE_DNS, str(self.regex + self.attribute)))
        self.login_address = self.request.headers.get('X-Real-Ip', self.request.remote_ip)

        self.methods = [method.lower() for method in methods]
        self.allow_patch_many = allow_patch_many
        self.validation_exceptions = validation_exceptions

        self.preprocessor = preprocessor
        self.postprocessor = postprocessor

        self.results_per_page = results_per_page
        self.max_results_per_page = max_results_per_page

        self.multi = {}
        self.token = None
        self.control = getattr(options, "access_control", False)

    def parse_pk(self, instance_id):
        return instance_id.split(self.ID_SEPARATOR)

    def parse_fk(self, fk_args):
        result = {}
        for fk in fk_args:
            result[fk['referred_table']] = fk['constrained_columns'][0]
        return result

    def get_search_params(self):
        """
        Get all the query arguments from json encoded body

        :return:

        """
        arguments = {}
        for arg in self.request.arguments:
            if arg not in ('offset', 'page', 'limit', 'results_per_page'):
                arguments[arg] = self.get_argument(arg)

        if self.control:
            tkn = scarecrow.AccessControl()

            stuff_info = tkn.stuffParams(self.request.method, self.token,
                                         self.login_address, res_code=self.node_code,
                                         table_name=self.table_name)
            if stuff_info.get("valid")==False:
                raise MethodNotAllowedError(self.request.method)
            else:
                if stuff_info.get("limits") is not None:
                    arguments = dict(arguments, **stuff_info.get("limits"))
        return arguments

    def delete_single(self, instance_id):
        """
            Remove one instance

            :param instance_id: list of primary keys
            :statuscode 200: instance successfull removed
        """

        # Trigger deletion
        number = 0
        self.pkey = BaseWrapper().getPrimaryKeys(self.table_name).get('constrained_columns', [])[0]
        for pk in instance_id:
            trigger = {self.pkey:pk}
            number += self.instance.delete(**trigger)
        # Status
        self.set_status(200, "Instance removed")
        return {"num_removed": number}

    def delete_many(self):
        """
            Remove many instances

            :statuscode 200: instances successfull removed

            :query limit: limit the count of deleted instances
            :query single: If true sqlalchemy will raise an error if zero or more than one instances would be deleted
        """

        # All search params
        search_params = self.get_search_params()

        # Call Preprocessor
        # self._call_preprocessor(filters=filters)

        num = self.instance.delete(**search_params)
        # Result
        self.set_status(200, "Removed")
        return {'num_removed': num}

    def delete(self, instance_id=None):
        """
            DELETE request

            :param instance_id: query argument of request
            :type instance_id: comma seperated string list

            :statuscode 403: DELETE MANY disallowed
            :statuscode 405: DELETE disallowed
        """
        logging.info('BaseHandler|delete, table_name:%s, instance_id:%s, request.arguments=%s.'
                     %(self.table_name, instance_id, self.request.arguments))
        if not 'delete' in self.methods:
            raise MethodNotAllowedError(self.request.method)

        # Call Preprocessor
        # self._call_preprocessor(search_params=self.search_params)

        if instance_id is None:
            if self.allow_patch_many:
                result = self.delete_many()
            else:
                raise MethodNotAllowedError(self.request.method, status_code=403)
        else:
            result = self.delete_single(self.parse_pk(instance_id))

        # self._call_postprocessor(result=result)
        self.finish(result)

    def get_single(self, instance_id):
        """
            Get one instance

            :param instance_id: query argument of request
            :type instance_id: list of primary keys
        """
        if self.instance is None:
            raise IllegalArgumentError("instance is None")
        result = self.instance.get(*instance_id)
        return {"num_results": len(result),
                "total_pages": 1,
                "page": 1,
                "objects": result}

    def get_multi_table(self):
        """
            Get multi-table instance

        """
        if self.instance is None:
            raise IllegalArgumentError("instance is None")
        results_per_page = int(self.get_argument("results_per_page", self.results_per_page))
        # All search params
        search_params = self.get_search_params()
        keyword = self.multi.get("keyword")
        params = self.multi.get("params")
        # Get table's primary keys
        self.pkey = BaseWrapper().getPrimaryKeys(keyword).get('constrained_columns', [])[0]
        # Offset & Page
        page = int(self.get_argument("page", '1'))
        search_params["offset"] = (page-1) * results_per_page
        # Limit
        search_params['limit'] = self.get_query_argument("limit", results_per_page)
        # Order_by & Direction
        search_params["order_by"] = self.get_argument('order_by', self.pkey)
        search_params["direction"] = self.get_argument('direction', 'desc')

        result = self.instance.multiple_table_query(keyword, dict(params, **search_params))
        return {"num_results": result.get('count', 0),
                "total_pages": int(ceil((result.get('count', 0) + results_per_page - 1) / results_per_page)),
                "page": page,
                "objects": result.get(keyword,[])}

    def get_many(self):
        """
            Get all instances

            Note that it is possible to provide offset and page as argument then
            it will return instances of the nth page and skip offset items

            :statuscode 400: if results_per_page > max_results_per_page or offset < 0

            :query results_per_page: Overwrite the returned results_per_page
            :query offset: Skip offset instances
            :query page: Return nth page
            :query limit: limit the count of modified instances
            :query single: If true sqlalchemy will raise an error if zero or more than one instances would be deleted
        """
        if self.instance is None:
            raise IllegalArgumentError("instance is None")

        results_per_page = int(self.get_argument("results_per_page", self.results_per_page))

        # All search params
        search_params = self.get_search_params()

        # Results per Page Check
        if results_per_page > self.max_results_per_page:
            raise IllegalArgumentError("request.results_per_page > application.max_results_per_page")

        # Num Results
        num_results = self.instance.count(**search_params)
        if results_per_page:
            total_pages = ceil((num_results + results_per_page - 1) / results_per_page)
        else:
            total_pages = 1

        # Offset & Page
        page = int(self.get_argument("page", '1'))
        search_params['offset'] = int(self.get_query_argument("offset", 0)) + (page - 1) * results_per_page
        if search_params['offset'] < 0:
            raise IllegalArgumentError("request.offset < 0")
        # Limit
        search_params['limit'] = self.get_query_argument("limit", results_per_page)

        if self.get_query_argument("single", False):
            result = self.instance.one(**search_params)
        else:
            result = self.instance.all(**search_params)

        return {"num_results": num_results,
                "total_pages": total_pages,
                "page": page,
                "objects": result}

    def get(self, instance_id=None):
        """
            GET request

            :param instance_id: query argument of request
            :type instance_id: comma seperated string list

            :statuscode 405: GET disallowed
        """
        logging.info('BaseHandler|get, table_name:%s, instance_id:%s, request.arguments=%s.'
                     % (self.table_name, instance_id, self.request.arguments))

        if not 'get' in self.methods:
            raise MethodNotAllowedError(self.request.method)

        # Call Preprocessor
        self._call_preprocessor(instance_id=instance_id, request_arguments=self.request.arguments)
        # Get table's primary keys
        self.pkey = BaseWrapper().getPrimaryKeys(self.table_name).get('constrained_columns', [])[0]

        if instance_id is None:
            result = self.get_many()
        else:
            if len(self.multi):
                result = self.get_multi_table()
            else:
                result = self.get_single(self.parse_pk(instance_id))

        # self._call_postprocessor(result=result)
        result = dumps(result, sort_keys=True, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        self.finish(result)

    def get_argument_values(self):
        """
            Get all values provided via arguments

        """

        return self.get_body_arguments()

    def put_many(self):
        values = self.get_argument_values()
        # All search params
        search_params = self.get_search_params()
        if len(values)==0:
            raise MethodNotAllowedError(self.request.method, status_code=404)

        num = self.instance.update(values,**search_params)
        # Result
        self.set_status(200, "updated")
        return {'num_updated': num}

    def put_single(self, instance_id):
        values = self.get_argument_values()
        # Trigger
        number = 0
        self.pkey = BaseWrapper().getPrimaryKeys(self.table_name).get('constrained_columns', [])[0]
        for pk in instance_id:
            trigger = {self.pkey:pk}
            ret = self.instance.update(values, **trigger)
            number = (number+1) if ret else number
        # Result
        self.set_status(200, "updated")
        return {'num_updated': number}

    def put(self, instance_id=None):
        """
            PUT (update instance) request

            :param instance_id: query argument of request
            :type instance_id: comma seperated string list

            :statuscode 403: PUT MANY disallowed
            :statuscode 404: Error
            :statuscode 405: PUT disallowed
        """

        if not 'put' in self.methods:
            raise MethodNotAllowedError(self.request.method)

        # Call Preprocessor
        # self._call_preprocessor(search_params=self.search_params)

        if instance_id is None:
            if self.allow_patch_many:
                result = self.put_many()
            else:
                raise MethodNotAllowedError(self.request.method, status_code=403)
        else:
            result = self.put_single(self.parse_pk(instance_id))

        # self._call_postprocessor(result=result)
        result = dumps(result, sort_keys=True, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        self.finish(result)

    def post_single(self):
        """
            Post one instance
        """
        values = self.get_argument_values()
        return self.instance.insert(values)

    def post(self, instance_id=None):
        """
            POST (new input) request

            :param instance_id: (ignored)

            :statuscode 204: instance successfull created
            :statuscode 404: Error
            :statuscode 405: POST disallowed
        """
        logging.info('BaseHandler|post, table_name:%s, request.body:%s'% (self.table_name, self.request.body))
        if not 'post' in self.methods:
            raise MethodNotAllowedError(self.request.method)

        # Call Preprocessor
        # self._call_preprocessor(search_params=self.search_params)

        result = self.post_single()

        # self._call_postprocessor(result=result)
        result = dumps(result, sort_keys=True, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        self.finish(result)

    def prepare(self):
        """
            Prepare the request
        """
        self.token = self.request.headers.get('token', None)
        if self.control:
            tkn = scarecrow.AccessControl()
            is_allowed = tkn.isAccessAllowed(self.token, self.request.method, self.login_address, res_code=self.node_code)
            if is_allowed==False:
                raise MethodNotAllowedError(self.request.method)
            else:
                request_body = self.get_body_arguments() if self.request.method.lower() in ("post", "put") else None
                scarecrow.recordOpt(self.token, self.request.method, self.request.path,
                                    self.get_search_params(), request_body)
        self._call_preprocessor()

    def on_finish(self):
        """
            Finish the request
        """

        self._call_postprocessor()

    def write_error(self, status_code, **kwargs):
        """
            Encodes any exceptions thrown to json

            SQLAlchemyError will be encoded as 400 / SQLAlchemy: Bad Request
            Errors from the restless api as 400 / Restless: Bad Arguments
            ProcessingException will be encoded with status code / ProcessingException: Stopped Processing
            Any other exceptions will occur as an 500 exception

            :param status_code: The Status Code in Response
            :param kwargs: Additional Parameters
        """
        if 'exc_info' in kwargs:
            exc_type, exc_value = kwargs['exc_info'][:2]
            if status_code >= 300:
                print_exception(*kwargs['exc_info'])
            if issubclass(exc_type, UnmappedInstanceError):
                self.set_status(400, reason='SQLAlchemy: Unmapped Instance')
                self.finish(dict(type=exc_type.__module__ + "." + exc_type.__name__,
                                 message="%s" % exc_value))
            elif issubclass(exc_type, SQLAlchemyError):
                self.set_status(400, reason='SQLAlchemy: Bad Request')
                self.finish(dict(type=exc_type.__module__ + "." + exc_type.__name__,
                                 message="%s" % exc_value))
            elif issubclass(exc_type, IllegalArgumentError):
                self.set_status(400, reason='Restless: Bad Arguments')
                self.finish(dict(type=exc_type.__module__ + "." + exc_type.__name__,
                                 message="%s" % exc_value))
            elif issubclass(exc_type, ProcessingException):
                self.set_status(status_code,
                                reason='ProcessingException: %s' % (exc_value.reason or "Stopped Processing"))
                self.finish(dict(type=exc_type.__module__ + "." + exc_type.__name__,
                                 message="%s" % exc_value))
            elif issubclass(exc_type, HTTPError) and exc_value.reason:
                self.set_status(status_code, reason=exc_value.reason)
                self.finish(dict(type=exc_type.__module__ + "." + exc_type.__name__,
                                 message="%s" % exc_value, **exc_value.__dict__))
            else:
                super(BaseHandler, self).write_error(status_code, **kwargs)
        else:
            super(BaseHandler, self).write_error(status_code, **kwargs)

    @memoized_instancemethod
    def get_body_arguments(self):
        """
            Get arguments encode as json body

            :statuscode 415: Content-Type mismatch

            :reqheader Content-Type: application/x-www-form-urlencoded or application/json
        """

        content_type = self.request.headers.get('Content-Type')
        if 'www-form-urlencoded' in content_type:
            payload = self.request.arguments
            for key, value in payload.items():
                if len(value) == 0:
                    payload[key] = None
                elif len(value) == 1:
                    payload[key] = str(value[0])
                else:
                    payload[key] = [str(value) for value in value]
            return payload
        elif 'application/json' in content_type:
            return loads(str(self.request.body))
        else:
            raise HTTPError(415, content_type=content_type)

    def get_body_argument(self, name, default=RequestHandler._ARG_DEFAULT):
        """
        Get an argument named key from json encoded body

        :param name: Name of argument
        :param default: Default value, if not provided HTTPError 404 is raised
        :return:

        :statuscode 404: Missing Argument
        """
        arguments = self.get_body_arguments()
        if name in arguments:
            return arguments[name]
        elif default is RequestHandler._ARG_DEFAULT:
            raise HTTPError(400, "Missing argument %s" % name)
        else:
            return default

    def _call_preprocessor(self, **kwargs):
        """
            Calls a preprocessor with args and kwargs
        """

        # Multi table judge
        if kwargs.has_key("instance_id") \
                and kwargs.has_key("request_arguments")\
                and self.request.method.lower()=='get':
            instance_id = kwargs.get("instance_id")
            if instance_id is not None:
                if self.ID_SEPARATOR in instance_id and self.SPRIT in instance_id:
                    raise MethodNotAllowedError(self.request.method)
                elif self.SPRIT in instance_id:
                    self.instance = None
                    instance_id = instance_id[:-1] if instance_id.endswith(self.SPRIT) else instance_id
                    baseURI= self.table_name + '/' + instance_id
                    tables = baseURI.split('/')[::2]
                    target = baseURI.split('/')[1::2]
                    keyword= tables[-1]
                    base   = BaseWrapper()
                    logging.info('Multi table|get keyword=%s, table list is:%s , code list is:%s.' % (keyword, tables, target))

                    if(len(tables)-len(target)!=1):
                        raise MethodNotAllowedError(self.request.method, status_code=400)

                    for table in base.showTables():
                        fkeys = self.parse_fk(base.getForeignKeys(table))
                        if set(tables)==set(fkeys.keys()) \
                                or (self.get_query_argument("distinct", False)
                                    and len(fkeys.keys())>0
                                    and len(set(tables)-set(fkeys.keys()))==0):
                            fields = [fkeys[key] for key in tables]
                            self.table_name = table
                            self.multi = {"keyword": keyword, "params": dict(zip(fields, target))}
                            self.instance = AlchemyWrapper(self.table_name)
                            break
                else:
                    pass

        func_name = inspect.stack()[1][3]
        if func_name in self.preprocessor:
            for func in self.preprocessor[func_name]:
                func(table_name=self.table_name, handler=self, **kwargs)

    def _call_postprocessor(self, *args, **kwargs):
        """
            Calls a postprocessor with args and kwargs
        """
        func_name = inspect.stack()[1][3]
        if func_name in self.postprocessor:
            for func in self.postprocessor[func_name]:
                func(*args, table_name=self.table_name, handler=self, **kwargs)