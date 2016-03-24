#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# ----------------------------------------------------------
#     FileName: run.py
#       Author: wangdean
#        Email: wangdean@sowell-tech.com
#      Version: 0.0.1
#   LastChange: 2016-02-14 11:01
#         Desc:
#      History:
# ----------------------------------------------------------
"""

import os,json
import tornado.httpserver, tornado.web, tornado.ioloop
from tornado.options import define, options
from scarecrow import ApiManager, BaseWrapper, RBAC, AccessControl, recordOpt
local_path = os.path.dirname(os.path.abspath(__file__))
define("port", default=8000, help="run on the given port", type=int)
options.parse_command_line()

class IndexHandler(tornado.web.RequestHandler):
    def get(self, *args):
        # m = re.match(aa, self.request.path)
        # if m:
        #     print '111',  m.group()
        self.write('hello, wangdean.')

class Test(tornado.web.RequestHandler):
    def get(self):
        base = BaseWrapper()
        print base.showTables()
        print base.getPrimaryKeys('roles')
        print base.getColumns('roles')
        print base.getUniqueConstraints('roles')
        print base.getForeignKeys('restrict')

class LoginHandler(tornado.web.RequestHandler):

    def get(self):
        print "token:+++", self.request.headers.get('token', None)
        pass

    def post(self):
        login_result = {"login": "Failed", "status": 0, "token":"Undefined"}
        content_type = self.request.headers.get('Content-Type')
        if 'application/json' not in content_type:
            raise tornado.web.HTTPError(415, content_type=content_type)

        request_body = json.loads(self.request.body)
        login_address= self.request.headers.get('X-Real-Ip', self.request.remote_ip)

        result = AccessControl().createToken(login_address, **request_body)
        if result is not None:
            login_result["status"] = 1
            login_result["login"]  = "Success"
            login_result = dict(login_result, **result)
        self.finish(login_result)

class LogoutHandler(tornado.web.RequestHandler):
    def get(self):
        ctl = AccessControl()
        token = self.request.headers.get('token', None)
        login_address = self.request.headers.get('X-Real-Ip', self.request.remote_ip)
        rest_status = ctl.resetToken(token, login_address)
        recordOpt(token, self.request.method, self.request.path)
        self.finish({"logout_status": rest_status})

class PasswordResetHandler(tornado.web.RequestHandler):

    def post(self):
        req_body = json.loads(self.request.body)
        ctl = AccessControl()
        login_address = self.request.headers.get('X-Real-Ip', self.request.remote_ip)
        token= self.request.headers.get('token', None)
        iRet = ctl.resetPassword(token, login_address, req_body.get("new_password"))
        recordOpt(token, self.request.method, self.request.path, request_body=req_body)
        self.finish({"password_reset":iRet})

app = tornado.web.Application([
                              (r'/api/login', LoginHandler),
                              (r'/api/logout', LogoutHandler),
                              (r'/api/password_reset', PasswordResetHandler),
                              ])

api = ApiManager(application=app)
api.create_api('restrict', methods=api.METHODS_ALL, allow_patch_many=True)
api.create_api('scepter', methods=api.METHODS_ALL, allow_patch_many=True)
api.create_api('resource', methods=api.METHODS_ALL, allow_patch_many=True)
api.create_api('users', methods=api.METHODS_ALL, allow_patch_many=True)
api.create_api('roles', methods=api.METHODS_ALL, allow_patch_many=True)
api.create_api('customer', methods=api.METHODS_ALL, allow_patch_many=True)

if __name__ == '__main__':
    RBAC(app)
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()