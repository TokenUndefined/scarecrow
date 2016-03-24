#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

"""

import datetime
from scarecrow import Base
from sqlalchemy import Column, ForeignKey, Integer, String

class Customer(Base):
    __tablename__ = 'customer'
    id            = Column(Integer,    primary_key=True)
    customer_name = Column(String(128),unique=True, nullable=False)   # 客户名称
    status        = Column(Integer, default=1)                        # 客户状态
    area          = Column(String(48))                                # 客户所在地区
    note          = Column(String(256))                               # 备注
    customer_ID   = Column(String(2), unique=True, nullable=False)    # 客户ID
    model_ID      = Column(String(2), nullable=False)                 # 机型ID
    left_point    = Column(Integer)                                   # 左端点
    right_point   = Column(Integer)                                   # 右端点
    offset_point  = Column(Integer)                                   # 偏移量
    test_offset_point = Column(Integer, default=90000000)             # 测试偏移量
    created_timestamp = Column(String(19), default=str(datetime.datetime.now())[:19])
    updated_timestamp = Column(String(19), default=str(datetime.datetime.now())[:19])

class Order(Base):
    __tablename__ = 'order'
    id            = Column(Integer, primary_key=True)
    order_number  = Column(String(128), unique=True, nullable=False)# 订单编号
    order_type    = Column(Integer, default=1)                      # 订单类型：1，订单；0，测试
    customer_name = Column(String(128), ForeignKey(Customer.customer_name, ondelete='CASCADE', onupdate='CASCADE'))
    product_amount= Column(Integer, nullable=False)                 # 生产数量
    spare_amount  = Column(Integer, default=0)                      # 备品数量
    note          = Column(String(2048))                            # 备注
    status        = Column(Integer, default=0)                      # 审核状态
    left_point    = Column(Integer)                                 # 左端点
    right_point   = Column(Integer)                                 # 右端点
    storage_file_name     = Column(String(256), nullable=False)
    relative_file_location= Column(String(1024), nullable=False)
    created_timestamp     = Column(String(19), default=str(datetime.datetime.now())[:19])
    updated_timestamp     = Column(String(19), default=str(datetime.datetime.now())[:19])

class SerialNumber(Base):
    __tablename__ = 'serial_number'
    id            = Column(Integer, primary_key=True)
    customer_name = Column(String(128), ForeignKey(Customer.customer_name, ondelete='CASCADE', onupdate='CASCADE'))
    order_number  = Column(String(128), ForeignKey(Order.order_number, ondelete='CASCADE', onupdate='CASCADE'))
    username      = Column(String(128),unique=True)
    password      = Column(String(128))
    status        = Column(Integer, default=0)                       # 状态
    sn            = Column(String(128),unique=True, nullable=False)
    created_timestamp = Column(String(19), default=str(datetime.datetime.now())[:19])
    updated_timestamp = Column(String(19), default=str(datetime.datetime.now())[:19])