##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging

log = logging.getLogger("zen.migrate")

import Globals
from Products.ZenModel.migrate.Migrate import Version
from Products.ZenModel.ZenPack import ZenPackMigration

from ZenPacks.zenoss.WebScale.config import ZopeConfig, NginxConfig

class RemoveUnusedPort(ZenPackMigration):
    version = Version(1, 2, 0)

    def migrate(self, dmd):
        port_to_remove = 9090
        zopeConfig = ZopeConfig()
        # Return if 9090 is a real port in use by the Zope configuration
        if port_to_remove in zopeConfig.zope_ports:
            return
        nginxConfig = NginxConfig()
        nginxConfig.remove_zope_server_by_port(port_to_remove)

RemoveUnusedPort()
