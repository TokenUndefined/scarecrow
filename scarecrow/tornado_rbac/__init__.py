#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# ----------------------------------------------------------
#     FileName: __init__.py (tornado_rbac)
#       Author: wangdean
#        Email: wangdean@sowell-tech.com
#      Version: 0.0.1
#   LastChange: 2016-02-23 16:04
#         Desc:
#      History:
# ----------------------------------------------------------
"""

import uuid
import datetime
import imp, os, re
import logging, json

from tornado.options import define, options
from scarecrow import AlchemyWrapper, secret_key
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

def recordOpt(token, opt, path, params=None, request_body=None):
    token= AccessControl().isTokenValid(token)
    user = AlchemyWrapper("users")
    role = AlchemyWrapper("roles")
    optLg= AlchemyWrapper('operation_logs')
    if token is not None:
        usr = user.all(code=token.get("user_code"))
        rle = role.all(code=token.get("role_code"))
        if len(usr)==1 and len(rle)==1 and opt.lower() in ("post", "put", "delete"):
            logs = {"operation": opt.lower(),
                    "opt_address": token.get("login_address"),
                    "request_path": path,
                    "user_code": token.get("user_code"),
                    "role_code": token.get('role_code'),
                    "username": usr[0].get("username"),
                    "role_name": rle[0].get("role_name"),}

            if params is not None:
                logs["request_arguments"] = json.dumps(params)
            if request_body is not None:
                logs["request_body"] = json.dumps(request_body)

            optLg.insert(logs)
            max_tms = optLg.max("created_timestamp", user_code=token.get("user_code"), role_code=token.get('role_code'))
            if isinstance(max_tms, datetime.datetime):
                tms = max_tms - datetime.timedelta(days=30)
                dlt = {"filters": [{"name":"created_timestamp", "op":"<", "value":tms}]}
                #logging.info("operation_logs[%s] will be cleared automatically." % (dlt))
                optLg.delete(**dlt)

class AccessControl(object):

    def __init__(self):
        self.serial = Serializer(secret_key, expires_in=3600)
        self.user = AlchemyWrapper("users")
        self.scepter = AlchemyWrapper("scepter")
        self.restrict = AlchemyWrapper("restrict")
        self.attribute = getattr(options, "attribute", "scarecrow")

    def resetToken(self, token, login_address):
        token = self.isTokenValid(token)
        if token is None:
            return False
        else:
            # update
            update_info = {"login_address":"0.0.0.0", "last_address": login_address}
            self.user.update(update_info, code=token.get('user_code'))
            return True

    def createToken(self, login_address, **kwargs):
        data = {"login_address": login_address}
        wrapper = AlchemyWrapper("users")
        login_params = {"or_":[
            {'name':'username', 'op':'==', 'value':kwargs.get("username", "")},
            {'name':'nickname', 'op':'==', 'value':kwargs.get("nickname", "")},
            {'name':'email', 'op':'==', 'value':kwargs.get("email", "")}
        ], "password":kwargs.get("password", ""), "status":1}

        result = wrapper.all(**login_params)
        if len(result)==1:
            # record the user login address.
            wrapper.update(data, code=result[0].get("code"))
            # use TimedJSONWebSignatureSerializer create the token
            data["role_code"] = result[0].get("role_code")
            data["user_code"] = result[0].get("code")
            token = self.serial.dumps(data)
            result = {"token": token,
                      "username": result[0].get("username"),
                      "nickname": result[0].get("nickname"),}
            return result
        else:
            return None

    def isTokenValid(self, token):
        data = None
        try:
            data = self.serial.loads(token)
        except:
            logging.error("Token[%s] authentication failed." % token)
        return data

    def getResCode(self, req_path=None, res_code=None):
        if req_path is None and res_code is None:
            return None

        if res_code is None:
            for api in getattr(options, "apps", {}).get("api", []):
                if re.match(api.get('url'), req_path):
                    combinat = api.get("url") + self.attribute
                    res_code = str(uuid.uuid3(uuid.NAMESPACE_DNS, str(combinat)))
                    break

        if res_code is None and req_path is not None:
            logging.warning("request path[%s] is out of the control!" % req_path)
            return None
        else:
            return res_code

    def isAccessAllowed(self, token, request_opt, login_address, req_path=None, res_code=None):
        token = self.isTokenValid(token)
        logging.info("isAccessAllowed| after parse token is :%s" % token)
        if token is None \
                or token.get("login_address")!=login_address:
            logging.warning("Illegal, token is not right.(may be the toke is None, "
                            "or token record of the login address and the actual address is not the same.)")
            return False

        visitor = self.user.all(code=token.get("user_code"), role_code=token.get("role_code"), status=1)
        if len(visitor)!=1:
            logging.warning("Token[%s] is not illegal!!!!!" % token)
            return False
        else:
            #
            if visitor[0].get("login_address")!=login_address:
                logging.warning("login_address[%s]:The token used has exited!" % (login_address))
                return False

        res_code = self.getResCode(req_path, res_code)
        res_limit = self.scepter.all(role_code=token.get("role_code"), resource_code=res_code, operation=request_opt.lower())
        if len(res_limit)>0:
            return False
        return True

    def resetPassword(self, token, login_address, new_password):
        tkn = self.isTokenValid(token)
        if tkn is None or tkn.get("login_address")!=login_address:
            return False

        if self.user.update({"password": new_password}, code=tkn.get("user_code")):
            self.resetToken(token, login_address)
            return True

        return False

    def stuffParams(self, opt, token, login_address,
                    req_path=None, res_code=None, table_name=None):
        result = {"valid": False, "limits": None}
        logging.info("stuffParams|opt=%s, token=%s, login_address=%s, "
                     "req_path=%s, res_code=%s, table_name=%s."
                     % (opt, token, login_address, req_path, res_code, table_name))

        token = self.isTokenValid(token)
        logging.info("stuffParams| after parse token is :%s" % token)
        if token is None \
                or token.get("login_address")!=login_address:
            logging.warning("Illegal, token is not right.(may be the toke is None, "
                            "or token record of the login address and the actual address is not the same.)")
            return result

        visitor = self.user.all(code=token.get("user_code"), role_code=token.get("role_code"), status=1)
        if len(visitor)!=1:
            logging.warning("Token[%s] is not illegal!!!!!" % token)
            return result
        else:
            #
            if visitor[0].get("login_address")!=login_address:
                logging.warning("login_address[%s]:The token used has exited!" % (login_address))
                return result
            else:
                result["valid"] = True

        res_code = self.getResCode(req_path, res_code)
        restrict = AlchemyWrapper("restrict")
        limits   = restrict.all(role_code=token.get("role_code"), user_code=token.get("user_code"))

        for limit in limits:
            if limit.get("table_name")==table_name \
                    and limit.get("resource_code")==res_code:
                result["limits"] = {"not_": json.loads(limit.get("constraints"))}
                break
        return result

class RBAC(object):
    def __init__(self, app=None):
        self.model_path = os.path.dirname(os.path.abspath(__file__))
        # zero, load module
        imp.load_module('model', *imp.find_module('model', [self.model_path,]))
        if app is not None:
            self.init_app(app)
        else:
            self.app = None

    def initialize(self):
        root  = {"role_name": "root"}
        admin = {"username": "admin",
                 "password": "123456",
                 "status": 1,
                 "email": "admin@sowell-tech.com",
                 "role_code": str(uuid.uuid3(uuid.NAMESPACE_DNS, "root"))}

        roles = AlchemyWrapper("roles")
        users = AlchemyWrapper("users")
        node  = AlchemyWrapper("resource")
        if len(roles.all(**root))==0:
            roles.insert(root)
        if len(users.all(username="admin"))==0:
            users.insert(admin)

        attribute = getattr(options, "attribute", "scarecrow")
        for api in self.api_list.get("api"):
            combinat  = api.get("url") + attribute
            node_code = str(uuid.uuid3(uuid.NAMESPACE_DNS, str(combinat)))
            node_info = {"attribute": attribute,
                         "code": node_code,
                         "resource_name": api.get("name"),
                         "resource_URI": api.get("url")}
            if len(node.all(**node_info))==0:
                node.insert(node_info)

    def init_app(self, app):
        # first, pick up the api list.
        patterns = []
        for pattern, handlers in app.handlers:
            for spec in handlers:
                patterns.append({"url": spec.regex.pattern, "name": spec.name})
        self.api_list = {"api": patterns}
        define("apps", default=self.api_list, help="set up the api list.")

        # second, set up the access_control flag.
        define("access_control", default=True, help="set up the access_control flag about the rbac.", type=bool)

        # third, initialize
        self.initialize()
