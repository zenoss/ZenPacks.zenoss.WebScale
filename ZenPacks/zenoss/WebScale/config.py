##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Globals
import os
import re
from App.config import getConfiguration
from Products.ZenUtils.Utils import zenPath
from tempfile import NamedTemporaryFile

import logging
log = logging.getLogger('zen.webscale.config')

ZOPE_CONFIG_DIR = zenPath('etc', 'zope')

class ZopeConfig(object):
    """
    Loads Zope configuration from App.config and the multi-zope
    configuration files in $ZENHOME/etc/zope. Provides the HTTP
    base port used in the Zope configuration and also the ports
    of all of the configured Zope instances.
    """
    DEFAULT_HTTP_BASE_PORT = 8080

    def __init__(self, zope_config_dir=ZOPE_CONFIG_DIR):
        self._zope_config_dir = zope_config_dir
        self._http_base_port = self._get_http_base_port()
        self._zope_ports = self._get_zope_ports()

    def _get_http_base_port(self):
        config = getConfiguration()
        servers = getattr(config, 'servers', [])
        base_port = ZopeConfig.DEFAULT_HTTP_BASE_PORT
        for server in servers:
            if server.servertype() == 'HTTPServer':
                base_port = int(server.port)
                break
        return base_port

    @property
    def http_base_port(self):
        """
        Returns the base port (as specified in the Zope configuration). The
        default value is 8080.
        """
        return self._http_base_port

    def _get_zope_ports(self):
        ports = []
        if os.path.isdir(self._zope_config_dir):
            config_files = [conf_file for conf_file in os.listdir(self._zope_config_dir) \
                            if conf_file.endswith('.conf')]
            for config_file in config_files:
                full_path = os.path.join(self._zope_config_dir, config_file)
                port = self._read_zope_port(full_path)
                if port:
                    ports.append(port)
        return ports

    def _read_zope_port(self, zope_config_file):
        if not os.path.isfile(zope_config_file):
            return
        with open(zope_config_file, 'r') as f:
            for line in f.readlines():
                if line.startswith('port-base'):
                    setting = line.strip().split(None, 1)
                    try:
                        return int(setting[1]) + self._http_base_port
                    except ValueError:
                        log.warning('Unable to read port from line: %s', line)

    @property
    def zope_ports(self):
        """
        Returns all of the configured Zope ports (in a multi-instance setup).
        """
        return self._zope_ports


class ZopeServerAddress(object):
    """
    Simple container for Zope address/port definitions found in nginx-zope.conf.
    """

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def __repr__(self):
        return "ZopeServerAddress<host=%s,port=%s>" % (self.host, self.port)

NGINX_ZOPE_CONFIG = zenPath('etc', 'nginx-zope.conf')

class NginxConfig(object):
    """
    Configuration class representing various parts of configuration of Nginx.
    Currently, there is only handling for the nginx-zope.conf configuration
    file (retrieiving the configured Zope instances and also removing port
    numbers from nginx-zope.conf).
    """

    _ZOPE_SERVER_PATTERN = re.compile(r'\s*server\s+(?P<server>[^\s;]+)\s*;')

    def __init__(self, nginx_zope_config=NGINX_ZOPE_CONFIG):
        self._nginx_zope_config = nginx_zope_config
        self._zope_servers = self._parse_nginx_zope_conf()

    def _parse_server(self, line):
        m = re.match(NginxConfig._ZOPE_SERVER_PATTERN, line)
        if m:
            server_parts = m.groupdict()['server'].rsplit(':', 1)
            if len(server_parts) == 2:
                try:
                    return ZopeServerAddress(server_parts[0], int(server_parts[1]))
                except ValueError:
                    log.warning('Invalid port number: %s', server_parts[1])
            else:
                log.warning('Unknown server definition: %s', line)

    def _parse_nginx_zope_conf(self):
        servers = []
        if os.path.isfile(self._nginx_zope_config):
            with open(self._nginx_zope_config, 'r') as f:
                for line in f.readlines():
                    server = self._parse_server(line)
                    if server:
                        servers.append(server)
        return servers

    def remove_zope_server_by_port(self, port):
        """
        Removes a Zope server using its port number from the Zope configuration
        file.
        """
        if not os.path.isfile(self._nginx_zope_config):
            return
        etc_dir = os.path.dirname(self._nginx_zope_config)
        dest = NamedTemporaryFile(dir=etc_dir, delete=False)
        try:
            with open(self._nginx_zope_config, 'r') as src:
                modified = False
                for line in src.readlines():
                    server = self._parse_server(line)
                    if server and server.port == int(port):
                        log.info("Removing server with port: %s", port)
                        modified = True
                    else:
                        dest.write(line)
                dest.close()
                if modified:
                    os.rename(dest.name, self._nginx_zope_config)
        finally:
            if os.path.exists(dest.name):
                os.remove(dest.name)

    @property
    def zope_servers(self):
        """
        Returns the Zope servers configured in the nginx-zope.conf file.

        @rtype:  list of ZopeServerAddress
        @return: A list of ZopeServerAddress objects for the configured zopes.
        """
        return self._zope_servers
