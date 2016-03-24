#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

"""

import datetime
from scarecrow import Base, engine
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text

class Roles(Base):
    __tablename__     = 'roles'
    id                = Column(Integer,   primary_key=True)
    role_name         = Column(String(64),unique=True, nullable=False)
    code              = Column(String(36), unique=True, nullable=False)
    short_title       = Column(String(36))
    status            = Column(Integer,   default=0)
    usage_note        = Column(String(128))
    created_timestamp = Column(DateTime, default=datetime.datetime.now)
    updated_timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

class Users(Base):
    __tablename__     = 'users'
    id                = Column(Integer,    primary_key=True)
    username          = Column(String(36), unique=True, nullable=False) # 用户名
    password          = Column(String(64), nullable=False)              # 密码
    nickname          = Column(String(36))                              # 昵称
    code              = Column(String(36), unique=True, nullable=False) # 用户ID
    status            = Column(Integer,    default=0)                   # 用户激活状态
    note              = Column(String(128))                             # 备注
    email             = Column(String(128),unique=True, nullable=False) # 注册邮箱
    role_code         = Column(String(36), ForeignKey(Roles.code, ondelete='CASCADE', onupdate='CASCADE'))
    created_timestamp = Column(DateTime, default=datetime.datetime.now)
    login_address     = Column(String(64))                              # 正在登陆的地址
    last_address      = Column(String(64))                              # 最近一次登陆的地址
    recent_access_time= Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

class Resource(Base):
    __tablename__  = 'resource'
    id             = Column(Integer,    primary_key=True)
    attribute      = Column(String(64), nullable=False, default="scarecrow")# 节点属性
    code           = Column(String(36), unique=True, nullable=False)        # 节点ID
    resource_name  = Column(String(256))                                    # 节点名称 # 是否有必要设置为必填？
    resource_URI   = Column(String(512),nullable=False)                     # 节点URI
    note           = Column(String(128))
    __table_args__ = (UniqueConstraint(attribute, resource_URI),)

class Scepter(Base):
    __tablename__  = 'scepter'
    id             = Column(Integer,    primary_key=True)
    resource_code  = Column(String(36), ForeignKey(Resource.code, ondelete='CASCADE', onupdate='CASCADE'))
    role_code      = Column(String(36), ForeignKey(Roles.code, ondelete='CASCADE', onupdate='CASCADE'))
    operation      = Column(String(36), nullable=False, default="delete") # get/post/put/delete
    __table_args__ = (UniqueConstraint(resource_code, role_code, operation),)

class Restrict(Base):
    __tablename__  = 'restrict'
    id             = Column(Integer,    primary_key=True)
    resource_code  = Column(String(36), ForeignKey(Resource.code, ondelete='CASCADE', onupdate='CASCADE'))
    role_code      = Column(String(36), ForeignKey(Roles.code, ondelete='CASCADE', onupdate='CASCADE'))
    user_code      = Column(String(36), ForeignKey(Users.code, ondelete='CASCADE', onupdate='CASCADE'))
    table_name     = Column(String(128),nullable=False)
    constraints    = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint(resource_code, role_code, user_code, table_name),)

class OperationLogs(Base):
    __tablename__     = 'operation_logs'
    id                = Column(Integer,    primary_key=True)
    username          = Column(String(36), nullable=False) # 用户名
    role_name         = Column(String(64), nullable=False)
    operation         = Column(String(36), nullable=False, default="post") # post/put/delete
    user_code         = Column(String(36), ForeignKey(Users.code, ondelete='CASCADE', onupdate='CASCADE'))
    role_code         = Column(String(36), ForeignKey(Roles.code, ondelete='CASCADE', onupdate='CASCADE'))
    opt_address       = Column(String(64), nullable=False, default='127.0.0.1')
    request_arguments = Column(String(1024))
    request_body      = Column(Text)
    request_path      = Column(String(512), nullable=False)
    created_timestamp = Column(DateTime, default=datetime.datetime.now)

Base.metadata.create_all(engine)