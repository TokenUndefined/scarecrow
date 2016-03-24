import sys,httplib,json,time
import yaml
from itsdangerous import JSONWebSignatureSerializer


def postRequest(path, msg, header, host='127.0.0.1', port=8000):
    try:
        conn = httplib.HTTPConnection(host, port)
        for i in range(0, 3):
            conn.request("POST", path, json.dumps(msg), headers=header)
            response = conn.getresponse()
            if response.status==200:
                break
            time.sleep(i+1)
    except:
        exc_type, exc_value = sys.exc_info()[:2]
        print('postRequest failed:%s.' % (exc_value))

if __name__ == '__main__':
    headers = {"Content-Type":"application/json"}
    bb = json.dumps([{"name":"id", "op":">", "value":2}])
    aa = {"resource_code":"09dd820b-5bae-38dc-9540-d21ac48b9714",
          "role_code":"1ff04c83-2308-3f26-81ff-dedfd3031b85",
          "user_code":"397d7c28-06d4-382d-8854-4af3f143d945",
          "table_name":"resource",
          "constraints":bb}
    postRequest('/api/restrict', aa, headers)

    # yaml_file = '/home/ott/scarecrow/setting/rom.bin'
    # f = open(yaml_file)
    # s = yaml.load(f)
    # f.close()
    #
    # print s, type(s)
    # serial = JSONWebSignatureSerializer('cat')
    # if isinstance(s, dict):
    #     s['db_status'] = 1
    #     f = open(yaml_file, 'w')
    #     s = serial.dumps(s)
    #     yaml.dump(s, f,default_flow_style=False)
    #     f.close()
    #
    # if isinstance(s, str):
    #     print '###1', serial.loads(s)

# pip install pyyaml


# from tornado.options import define, options
# define("db111", default='created_wda', help="setting the data base operation.", type=str)
# def wda_test():
#     print "++++++111", options.db111