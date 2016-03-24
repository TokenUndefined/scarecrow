#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# ----------------------------------------------------------
#     FileName: wrapper.py
#       Author: wangdean
#        Email: wangdean@sowell-tech.com
#      Version: 0.7.1
#   LastChange: 2016-02-14 11:01
#         Desc:
#      History:
# ----------------------------------------------------------
"""

import sys
import uuid
import json
import logging
import scarecrow
from sqlalchemy.sql.expression import or_, not_
from sqlalchemy import Table, desc, asc, func
from sqlalchemy.orm import mapper
from sqlalchemy import inspect as Inspect

class BaseWrapper(object):
    def __init__(self):
        self.Session  = scarecrow.Session
        self.Base     = scarecrow.Base
        self.engine   = scarecrow.engine
        self.metadata = self.Base.metadata

    def showTables(self):
        """
            Lists the non-TEMPORARY tables in a given database.
        """
        return self.metadata.tables.keys()

    def getForeignKeys(self, table):
        """
            Return information about foreign_keys in table_name.
        """
        return Inspect(self.metadata.bind).get_foreign_keys(table)

    def getPrimaryKeys(self, table):
        """
            Return information about primary key constraint on table_name.
        """
        return Inspect(self.metadata.bind).get_pk_constraint(table)

    def getUniqueConstraints(self, table):
        """
            Return information about unique constraints in table_name.
        """
        return Inspect(self.metadata.bind).get_unique_constraints(table)

    def getColumns(self, table):
        """
            Return information about columns in table_name.
        """
        return Inspect(self.metadata.bind).get_columns(table)

class AlchemyWrapper(object):

    def getModel(self, table):
        model = None
        if table in self.base.showTables():
            class TableWrapper(object):pass
            table = Table(table, self.metadata, autoload=True)
            mapper(TableWrapper, table)
            model = TableWrapper
        else:
            logging.warning("table[%s] not in the tables!" % table)
        return model

    def to_filters(self, instance, argument_filters):
        if isinstance(argument_filters, list)==False:
            argument_filters = json.loads(argument_filters)

        logging.info("to_filters| argument_filters = %s" % argument_filters)

        # Create Alchemy Filters
        alchemy_filters = []
        for argument_filter in argument_filters:
            # Resolve right attribute
            if "val" in argument_filter.keys():
                right = argument_filter["val"]
            elif "value" in argument_filter.keys():  # Because we hate abbr sometimes ...
                right = argument_filter["value"]
            else:
                right = None

            # Operator
            op = argument_filter["op"]
            if op in ["like"]:
                right = '%' + right + '%'

            # Resolve left attribute
            if "name" not in argument_filter:
                logging.warning("Missing fieldname attribute 'name'")

            if argument_filter["name"] == "~":
                left = instance
                op = "attr_is"
            else:
                left = getattr(instance, argument_filter["name"])

            # Operators from flask-restless
            if op in ["is_null"]:
                alchemy_filters.append(left.is_(None))
            elif op in ["is_not_null"]:
                alchemy_filters.append(left.isnot(None))
            elif op in ["is"]:
                alchemy_filters.append(left.is_(right))
            elif op in ["is_not"]:
                alchemy_filters.append(left.isnot(right))
            elif op in ["==", "eq", "equals", "equals_to"]:
                alchemy_filters.append(left == right)
            elif op in ["!=", "ne", "neq", "not_equal_to", "does_not_equal"]:
                alchemy_filters.append(left != right)
            elif op in [">", "gt"]:
                alchemy_filters.append(left > right)
            elif op in ["<", "lt"]:
                alchemy_filters.append(left < right)
            elif op in [">=", "ge", "gte", "geq"]:
                alchemy_filters.append(left >= right)
            elif op in ["<=", "le", "lte", "leq"]:
                alchemy_filters.append(left <= right)
            elif op in ["ilike"]:
                alchemy_filters.append(left.ilike(right))
            elif op in ["not_ilike"]:
                alchemy_filters.append(left.notilike(right))
            elif op in ["like"]:
                alchemy_filters.append(left.like(right))
            elif op in ["not_like"]:
                alchemy_filters.append(left.notlike(right))
            elif op in ["match"]:
                alchemy_filters.append(left.match(right))
            elif op in ["in"]:
                alchemy_filters.append(left.in_(right))
            elif op in ["not_in"]:
                alchemy_filters.append(left.notin_(right))
            elif op in ["has"] and isinstance(right, list):
                alchemy_filters.append(left.any(*right))
            elif op in ["has"]:
                alchemy_filters.append(left.has(right))
            elif op in ["any"]:
                alchemy_filters.append(left.any(right))
            # Additional Operators
            elif op in ["between"]:
                alchemy_filters.append(left.between(*right))
            elif op in ["contains"]:
                alchemy_filters.append(left.contains(right))
            elif op in ["startswith"]:
                alchemy_filters.append(left.startswith(right))
            elif op in ["endswith"]:
                alchemy_filters.append(left.endswith(right))
            # Additional Checks
            elif op in ["attr_is"]:
                alchemy_filters.append(getattr(left, right))
            elif op in ["method_is"]:
                alchemy_filters.append(getattr(left, right)())
            # Test comparator
            elif hasattr(left.comparator, op):
                alchemy_filters.append(getattr(left.comparator, op)(right))
            # Raise Exception
            else:
                logging.warning("Unknown operator")

        return alchemy_filters

    def _apply_kwargs(self, instance, **kwargs):

        if 'filters' in kwargs:
            filters = kwargs.pop('filters')
            logging.info("_apply_kwargs | filters = %s" % filters)
            for alchemy_filter in self.to_filters(self.model, filters):
                instance = instance.filter(alchemy_filter)

        if 'not_' in kwargs or 'or_' in kwargs:
            operator = 'not_'
            if 'not_' in kwargs:
                argument_filters = kwargs.pop('not_')
            else:
                operator = "or_"
                argument_filters = kwargs.pop('or_')
            if isinstance(argument_filters, list)==False:
                argument_filters = json.loads(argument_filters)
            alchemy_list = []
            for filters in argument_filters:
                alchemy_list += self.to_filters(self.model, [filters])

            if operator=="not_":
                instance = instance.filter(not_(*alchemy_list))
            else:
                instance = instance.filter(or_(*alchemy_list))

        if 'order_by' in kwargs or 'direction' in kwargs:
            criterion = kwargs.pop('order_by')
            direction = kwargs.pop('direction')
            if direction == 'asc':
                expression = asc(getattr(self.model, criterion))
            else:
                expression = desc(getattr(self.model, criterion))
            instance = instance.order_by(expression)

        if 'offset' in kwargs:
            offset = kwargs.pop('offset')
            foffset= lambda instance: instance.offset(offset)
        else:
            foffset= lambda instance: instance

        if 'limit' in kwargs:
            limit = kwargs.pop('limit')
            flimit= lambda instance: instance.limit(limit)
        else:
            flimit= lambda instance: instance

        instance = instance.filter_by(**kwargs)
        instance = foffset(instance)
        instance = flimit(instance)
        return instance

    def logging_error(self):
        exc_type, exc_value = sys.exc_info()[:2]
        logging.error("exc_type=%s, message=%s" % (exc_type.__module__ + "." + exc_type.__name__, exc_value))

    def to_dict(self, obj_dict):
        return dict((key, obj_dict[key]) for key in obj_dict if not key.startswith("_"))

    def __init__(self, table_name):
        self.res_dict  = {}
        self.tablename = table_name
        self.Session   = scarecrow.Session
        self.Base      = scarecrow.Base
        self.engine    = scarecrow.engine
        self.metadata  = self.Base.metadata
        self.session   = self.Session()
        self.base      = BaseWrapper()
        self.model     = self.getModel(table_name)

    def __del__(self):
        self.session.close()

    def max(self, table_column, **kwargs):
        instance = self.session.query(func.max(getattr(self.model, table_column)))
        return self._apply_kwargs(instance, **kwargs).scalar()

    def insert(self, metadata):
        instance = self.model()
        try:
            if metadata.has_key('code') == False and hasattr(instance, 'code'):
                if self.tablename in ("roles", "users"):
                    name = metadata.get("role_name") if metadata.has_key("role_name") else metadata.get("username")
                    setattr(instance, 'code', str(uuid.uuid3(uuid.NAMESPACE_DNS, str(name))))
                else:
                    setattr(instance, 'code', str(uuid.uuid4()))

            for key, value in metadata.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            self.session.add(instance)

            # Flush
            self.session.flush()
            # To Dict
            result = self.to_dict(instance.__dict__)
            # Commit
            self.session.commit()
            result["errorcode"] = 1
        except:
            self.logging_error()
            # print(traceback.format_exc())
            self.session.rollback()
            result = {'errorcode':0}
        return result

    def count(self, **kwargs):
        instance = self.session.query(self.model)
        return self._apply_kwargs(instance, **kwargs).count()

    def get(self, *pargs):
        """
            query based on primary_keys

            :param pargs: ident
        """

        result = []
        try:
            instance = self.session.query(self.model)

            if isinstance(pargs, tuple):
                for args in pargs:
                    result.append(self.to_dict(instance.get(args).__dict__))
            else:
                result.append(self.to_dict(instance.get(pargs).__dict__))
        except:
            self.logging_error()
        return result

    def all(self, **kwargs):
        buffer   = []
        try:
            instance = self.session.query(self.model)
            for row in self._apply_kwargs(instance, **kwargs).all():
                buffer.append(self.to_dict(row.__dict__))
        except:
            self.logging_error()
        return buffer

    def one(self, **kwargs):
        try:
            instance = self.session.query(self.model)
            result   = self._apply_kwargs(instance, **kwargs).one()
            return [self.to_dict(result.__dict__)]
        except:
            return []

    def delete(self, **kwargs):
        instance = self.session.query(self.model)
        try:
            number = self._apply_kwargs(instance, **kwargs).delete()
            self.session.commit()
        except:
            self.logging_error()
            self.session.rollback()
            number = 0
        return number

    def update(self, values, **kwargs):
        instance = self.session.query(self.model)
        number   = 0
        try:
            number = self._apply_kwargs(instance, **kwargs).update(values)
            self.session.commit()
        except:
            self.logging_error()
            self.session.rollback()
        return number

    def get_fk_info(self, values, table=''):
        table = table if len(table)>0 else self.tablename
        model = self.getModel(table)
        fkeys = self.base.getForeignKeys(table)
        instance = self.session.query(model)

        for arg in self._apply_kwargs(instance, **values).all():
            temporary = self.res_dict.get(table, [])
            temporary.append(self.to_dict(arg.__dict__))
            for fk in fkeys:
                referred_table = fk['referred_table']
                referred_dict  = {fk['referred_columns'][0]:getattr(arg, fk['constrained_columns'][0])}
                self.get_fk_info(referred_dict, referred_table)
            self.res_dict[table] = temporary
        return self.res_dict

    def get_fk_info_ex(self, values, table=''):
        print('get_fk_info_ex, table is %s, search info is:%s' %(table, values))
        tablename= table if len(table)>0 else self.tablename
        model    = self.getModel(tablename)
        fkeys    = self.base.getForeignKeys(tablename)
        instance = self.session.query(model)

        for arg in self._apply_kwargs(instance, **values).all():
            temporary = self.res_dict.get(tablename, [])
            temporary.append(self.to_dict(arg.__dict__))
            if len(table)>0:
                self.res_dict[tablename] = temporary
            else:
                self.res_dict = self.to_dict(arg.__dict__)

            for fk in fkeys:
                referred_table = fk['referred_table']
                referred_dict  = {fk['referred_columns'][0]:getattr(arg, fk['constrained_columns'][0])}
                self.get_fk_info_ex(referred_dict, referred_table)
        return self.res_dict

    def get_tree_codelist(self, code):
        buffer   = []
        treeinfo = []
        instance = self.session.query(self.model).filter(getattr(self.model, 'code') == code).first()
        mapping  = self.session.query(self.getModel('treemapping'))
        def get_tree(node, buff):
            if node == None:
                return
            buff.append(node.code)
            children = node.children
            if children and children is not None:
                for child in children:
                    get_tree(child, buff)
            else:
                return
        get_tree(instance, buffer)
        for buf in buffer:
            for row in mapping.filter(getattr(self.getModel('treemapping'), 'parent_code')== buf):
                text = self.to_dict(row.__dict__)
                treeinfo.append(text)
                buffer.append(row.sub_code)
        return {'treemapping':treeinfo, 'codelist':buffer}

    def get_children_tree(self, code):
        result   = {}
        instance = self.session.query(self.model).filter(getattr(self.model, 'code') == code).first()
        def get_tree(node, buff):
            if node == None:
                return

            children = node.children
            if children and children is not None:
                for child in children:
                    query_res = self.to_dict(child.__dict__)
                    temporary = buff.get('subcategory', [])
                    temporary.append(query_res)
                    buff['subcategory'] = temporary
                    get_tree(child, query_res)
            else:
                return
        get_tree(instance, result)
        return result

    def multiple_table_query(self, keyword, kwargs):
        buff_A = []
        buff_B = []
        result = {}
        fkeys  = self.base.getForeignKeys(self.tablename)

        logging.info('multiple_table_query|kwargs=%s' % kwargs)

        if 'order_by' in kwargs:
            criterion = kwargs.pop('order_by')
            direction = kwargs.pop('direction')
        else:
            criterion = self.base.getPrimaryKeys(keyword).get('constrained_columns', [])[0]
            direction = 'desc'

        distinct= kwargs.pop('distinct')if 'distinct'in kwargs else None
        offset  = kwargs.pop('offset')  if 'offset'  in kwargs else None
        limit   = kwargs.pop('limit')   if 'limit'   in kwargs else None
        filters = kwargs.pop('filters') if 'filters' in kwargs else None

        for fk in fkeys:
            if keyword == fk['referred_table']:
                temporary= self.getModel(keyword)
                left     = getattr(temporary, fk['referred_columns'][0])
                right    = getattr(self.model, fk['constrained_columns'][0])

                if distinct is not None and (distinct==True or distinct.lower()=='true'):
                    instance = self.session.query(temporary).distinct().filter(left==right)
                else:
                    instance = self.session.query(self.model, temporary).filter(left==right)

                for key, value in kwargs.items():
                    instance = instance.filter(getattr(self.model, key)==value)

                if filters is not None:
                    for alchemy_filter in self.to_filters(temporary, filters):
                        instance = instance.filter(alchemy_filter)

                if hasattr(self.model(), 'sequence') and distinct is None:
                    order_ins = self.model
                    criterion = 'sequence'
                else:
                    order_ins = temporary
                if direction == 'asc':
                    expression = asc(getattr(order_ins, criterion))
                else:
                    expression = desc(getattr(order_ins, criterion))

                instance = instance.order_by(expression)
                count    = instance.count()

                if offset is not None:
                    instance = instance.offset(offset)
                if limit is not None:
                    instance = instance.limit(limit)

                if distinct is not None and (distinct==True or distinct.lower()=='true'):
                    for B in instance.all():
                        buff_B.append(self.to_dict(B.__dict__))
                    result = {keyword:buff_B, 'count':count}
                else:
                    for A, B in instance.all():
                        info_A = self.to_dict(A.__dict__)
                        info_B = self.to_dict(B.__dict__)
                        if hasattr(self.model(), 'sequence'):
                            info_B['sequence'] = info_A.get('sequence')

                        if keyword == 'program':
                            mapIns = self.getModel('program_genre_map')
                            buff   = []
                            for tag in self.session.query(mapIns).filter(getattr(mapIns, 'program_code')==info_B.get('code')):
                                buff.append(self.to_dict(tag.__dict__).get('genre_code'))
                            info_B['movie_genre'] = buff

                            level      = 0
                            lenth      = 0
                            ratemapIns = self.getModel('program_movierate_map')
                            rateIns    = self.getModel('movierate')
                            for tag in self.session.query(ratemapIns).filter(getattr(ratemapIns, 'program_code')==info_B.get('code')):
                                tagRes = self.session.query(rateIns).filter(getattr(rateIns, 'code')==self.to_dict(tag.__dict__).get('movierate_code')).first()
                                level += self.to_dict(tagRes.__dict__).get('movie_rate_level')
                                lenth += 1
                            if lenth==0:
                                info_B['movie_rate_level'] = 0
                            else:
                                info_B['movie_rate_level'] = float(level)/lenth

                            peopleIns = self.getModel('people')
                            pprIns    = self.getModel('program_people_role_map')
                            actorID   = str(uuid.uuid3(uuid.NAMESPACE_DNS, 'actor'))
                            directorID= str(uuid.uuid3(uuid.NAMESPACE_DNS, 'director'))
                            for actorTag in self.session.query(pprIns).filter(getattr(pprIns, 'program_code')==info_B.get('code'), getattr(pprIns, 'role_code')==actorID):
                                actorRes = self.session.query(peopleIns).filter(getattr(peopleIns, 'code')==self.to_dict(actorTag.__dict__).get('people_code')).first()
                                info_B['actor'] = self.to_dict(actorRes.__dict__).get('name') if len(info_B.get('actor', ''))==0 else info_B.get('actor', '') + ',' + self.to_dict(actorRes.__dict__).get('name')

                            for directorTag in self.session.query(pprIns).filter(getattr(pprIns, 'program_code')==info_B.get('code'), getattr(pprIns, 'role_code')==directorID):
                                directorRes = self.session.query(peopleIns).filter(getattr(peopleIns, 'code')==self.to_dict(directorTag.__dict__).get('people_code')).first()
                                info_B['director'] = self.to_dict(directorRes.__dict__).get('name') if len(info_B.get('director', ''))==0 else info_B.get('director', '') + ',' + self.to_dict(directorRes.__dict__).get('name')
                        buff_A.append(info_A)
                        buff_B.append(info_B)
                    result = {self.tablename:buff_A, keyword:buff_B, 'count':count}
                break
        return result
