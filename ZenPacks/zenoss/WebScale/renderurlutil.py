##############################################################################
#
# Copyright (C) Zenoss, Inc.  2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.ZenUtils.Utils import zenPath
from Products.ZenModel.PerformanceConf import RenderURLUtil, ProxyConfig

class NginxRenderURLUtil(RenderURLUtil):

    def __init__(self, context):
        super(NginxRenderURLUtil, self).__init__(context)
        self.context = context        

    def _get_reverseproxy_config(self):
        use_ssl = False
        http_port = 8080
        ssl_port = 443
        conf_path = zenPath("etc", "zenwebserver.conf")
        with open(conf_path) as file_:
            for line in (l.strip() for l in file_):
                if line and not line.startswith('#'):
                    key, val = line.split(' ', 1)
                    if key == "useSSL":
                        use_ssl = val.lower() == 'true'
                    elif key == "httpPort":
                        http_port = int(val.strip())
                    elif key == "sslPort":
                        ssl_port = int(val.strip())
        return ProxyConfig(useSSL=use_ssl,
                           port= ssl_port if use_ssl else http_port) 
