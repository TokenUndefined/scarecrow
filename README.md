# scarecrow

1 概述
scarecrow(稻草人)是基于数据库模型，使用SQLAlchemy提供REST风格API接口的简单快速生成方式，
生成的接口满足JSON规范要求。

scarecrow主要的核心代码源于1847业务系统的核心模块，并参照了部分tornado-restless的代码，
并初步具备RBAC(Role-Based Access Control)功能。

2 框架组织结构简介
    <proj-name>
        | -- <scarecrow>
                | -- <tornado_rbac>
                        | -- __init__.py    # RBAC权限管控模块
                        | -- model.py       # RBAC数据库模型
                | -- __init__.py
                | -- api.py                 # tornado Application类
                | -- errors.py              # HTTP状态码模块
                | -- globals.py             # 全局参数模块
                | -- handler.py             # 路由处理模块
                | -- wrapper.py             # SQLAlchemy封装模块
        | -- models.py                      # 数据库模型
        | -- run.py                         # 程序运行入口

3 API接口风格介绍
    举例说明:
        比如，数据库中有一个表，表名为resource，它的接口为:
        http://host-ip:host-port/api/tms/resource
        注:/api/tms为接口URI的一个前缀，可以任意设置
        那么它具备的访问方法为:
            (1)POST
                即创建接口，请求数据为resource表中的字段，返回的数据中会有errorcode标识创建成功与否的字段，
                成功的话还会插入成功的数据，失败的话则没有。
                操作示例:
                curl -d '{"name":"hello"}' -H "Content-Type:application/json" http://host-ip:host-port/api/tms/resource

            (2)DELETE
                即删除接口，此类接口有二种，一类是根据条件删除，一类是根据主键删除
                1> 根据条件删除
                curl -X DELETE http://host-ip:host-port/api/tms/resource?name=hello
                问号后面带的为删除条件，即满足name为hello的删除
                2> 根据主键删除
                curl -X DELETE http://host-ip:host-port/api/tms/resource/1,2
                删除主键为1和2的数据，可以是批量删除，数据之间用逗号隔开

            (3)PUT
                即更新接口，此类接口也同样有二种，一类是根据条件更新，一类是根据主键更新
                1> 根据条件删除
                curl -X PUT -d '{"name":"haha"}' -H "Content-Type:application/json" http://host-ip:host-port/api/tms/resource?name=hello
                将name为hello更新为haha
                2> 根据主键删除
                curl -X PUT -d '{"name":"haha"}' -H "Content-Type:application/json" http://host-ip:host-port/api/tms/resource/1,2
                将主键为1和2的name更新为haha，同样可以是批量更新，数据之间用逗号隔开

            (4)GET
                即获取类接口，此类接口内容比较丰富:
                1> 全部获取
                curl http://host-ip:host-port/api/tms/resource
                2> 根据主键获取
                curl http://host-ip:host-port/api/tms/resource/1,2
                3> 获取表中的某一列(某几列)
                curl http://host-ip:host-port/api/tms/resource/name,id
                即获取出来的数据只有name和id二列的值
                4> 根据条件筛选数据
                curl http://host-ip:host-port/api/tms/resource?name=hello\&id=2
                即筛选name为hello并且id为2的数据
                那么此时你是否会说，如果我要模糊搜索呢？也是支持的，例如
                curl http://host-ip:host-port/api/tms/resource?filters=[{"name":"name", "op":"like", "value":"hel"}]
                即搜索name中有出现hel字样的数据，它其它类似于数据库中的操作，支持的操作有:
                    is_null
                    is_not_null
                    is
                    is_not
                    ==, eq, equals, equals_to
                    !=, ne, neq, not_equal_to, does_not_equal
                    >, gt
                    <, lt
                    >=, ge, gte, geq
                    <=, le, lte, leq
                    ilike
                    not_ilike
                    like
                    not_like
                    match
                    in
                    not_in
                    has
                    any
                    between
                    contains
                    startswith
                    endswith
                    attr_is
                    method_is
                实际在用的时候，可能会有用到一些像or/not之类的操作，那么这儿是否也支持呢？答案是支持的，不过目前
                只支持filters/or_/not_三大类，比如
                curl http://host-ip:host-port/api/tms/resource?or_=[{"name":"name", "op":"like", "value":"hel"},{"name":"id", "op":"==", "value":"2"}]
                搜索name中出现hel字样的数据或者id为2的数据，not_与之类似。
                那如果要做多表联查呢？是不是也支持呢？哈哈，也是支持的，这儿支持那种多对多数据的查询,例如
                curl http://host-ip:host-port/api/tms/resource/id/node
                即根据resource的id值查找与之相关联的node信息

4 使用介绍
    (1) 依赖环境
        * python 2.6以上版本
        * Tornado
        * 数据库(支持PostgreSQL/MySQL等)
        * SQLAlchemy
    (2) 设置数据库连接
        在globals.py中修改connector的值，程序启动时会根据这个值自动创建数据库，同时可以根据命令行参数
        db的值去删除数据库，即设置db=drop。
    (3) 创建tornado Application实例，并传递到ApiManager中去，然后使用这一实例创建相应的api.
    Example:
        import tornado.httpserver, tornado.web, tornado.ioloop
        from scarecrow import ApiManager

        app = tornado.web.Application([])
        api = ApiManager(application=app)
        api.create_api('resource', methods=api.METHODS_ALL, allow_patch_many=True)
        # methods设置的是允许访问的方法,
        # allow_patch_many是批量更新、删除开关,
        # url_prefix设置URI的前缀
        if __name__ == '__main__':
            app.listen(8888)
            tornado.ioloop.IOLoop.instance().start()

5 与Tornado-restless相比较
    (1) Tornado-restless只支持python 3.0以上版本;
    (2) 与Tornado-restless相比，scarecrow具备了Tornado-restless的所有风格接口，还多出了多表联查功能、
        or_/not_类型的条件筛选、获取表中某几列的数据以及RBAC功能;
    (3) 在使用上scarecrow要相对方便些，Tornado-restless在创建api的时候需要传进去的是一个表的class，而scarecrow只需要一个
        表名，后面就能自己识别并转换能一个TableObject，除此之外，还可以将scarecrow应用到只知道数据库名称不知道数据库模型中去，
        只要嵌入这么个程序，就能将数据库中的表提供api接口出来。