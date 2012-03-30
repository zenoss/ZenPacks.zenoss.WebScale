###########################################################################
#
# Copyright 2012 Zenoss, Inc. All Rights Reserved.
#
###########################################################################

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
