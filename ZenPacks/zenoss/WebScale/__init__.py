######################################################################
#
# Copyright 2007 Zenoss, Inc.  All Rights Reserved.
#
######################################################################
import Globals
import os
import sys
import time
import shutil
import logging
import subprocess
from Products.ZenUtils.Utils import zenPath
from Products.ZenModel.ZenPack import ZenPackBase


log = logging.getLogger("zen.WebScale")


def get_port():
    port = '8080'
    with open(zenPath('etc', 'zope.conf'), 'r') as f:
        for line in f:
            if line.strip().startswith('address'):
                port = line.split()[-1]
                break
    return port


def replace_zopectl_in_daemons_txt():
    daemonstxt = zenPath('etc', 'daemons.txt')
    if os.path.exists(daemonstxt):
        with open(daemonstxt, 'r') as f:
            newfile = f.read().replace('zopectl', 'zenwebserver')
        with open(daemonstxt, 'w') as f:
            f.write(newfile)


def is_using_many_zopes():
    # This is relatively naive, but errs on the side of caution. Also I don't
    # know what else we can do.
    daemonstxt = zenPath('etc', 'daemons.txt')
    if not os.path.exists(daemonstxt):
        # Using the default daemons, so no more zopes
        return False
    with open(daemonstxt, 'r') as f:
        count = 0
        for line in f:
            if 'zope' in line:
                count += 1
                if count > 1:
                    return True
    return False


def use_zenwebserver():
    """
    Make the change to force zenwebserver
    """
    log.info("Replacing zopectl with zenwebserver")
    subprocess.call([zenPath('bin', 'zenglobalconf'), '-u', 'webserverctl=zenwebserver'])


def use_zopectl():
    """
    Undo zenwebserver and use the default
    """
    log.info("Removing zenwebserver and restoring zopectl")
    subprocess.call([zenPath('bin', 'zenglobalconf'), '-r', 'webserverctl'])


class ZenPack(ZenPackBase):

    def _executable(self, *path):
        """
        Make specified file executable.
        """
        fname = self.path(*path)
        os.chmod(fname, 0755)

    def _symlink(self, fro, to):
        """
        Symlink from a path within this zenpack to a path under $ZENHOME.
        Pass in tuples of path segments.
        """
        src = self.path(*fro)
        dest = zenPath(*to)
        if os.path.lexists(dest):
            os.remove(dest)
        os.symlink(src, dest)

    def _copy(self, fro, to):
        """
        Copy from a path within this zenpack to a path under $ZENHOME.
        Do NOT overwrite existing files.
        Pass in tuples of path segments.
        """
        src = self.path(*fro)
        dest = zenPath(*to)
        if not os.path.exists(dest):
            shutil.copyfile(src, dest)

    def install(self, dmd):
        log.info("Installing zenwebserver and nginx to $ZENHOME/bin")
        # Create zenwebserver symlink
        self._symlink(('zenwebserver',), ('bin', 'zenwebserver'))
        self._executable('zenwebserver')

        # Create bin/nginx symlink
        self._symlink(('bin', 'nginx'), ('bin', 'nginx'))
        self._executable('bin', 'nginx')

        log.info("Installing nginx configuration to $ZENHOME/etc")

        port = get_port()
        log.info("Detected Zope is using port %s" % port)


        # Replace strings in zenwebserver.conf
        with open(self.path('zenwebserver.conf'), 'r') as f, open(self.path('zenwebserver.conf.tmp'), 'w') as f2:
            f2.write(f.read()
                     .replace('<<INSTANCE_HOME>>', zenPath())
                     .replace('<<PORT>>', port))

        # Create mime.types symlink
        self._symlink(('mime.types',), ('etc', 'mime.types'))

        # copy 50x page
        self._copy(('zenwebserver_50x.html',), ('html', 'zenwebserver_50x.html'))

        # Copy in nginx configs, does not replace existing configs
        self._copy(('zenwebserver.conf.tmp',), ('etc', 'zenwebserver.conf'))
        self._copy(('nginx-zope.conf',), ('etc', 'nginx-zope.conf'))

        # Clean up
        os.remove(self.path('zenwebserver.conf.tmp'))

        try:
            os.mkdir(zenPath('etc', 'zope'))
            log.info("Created multi-Zope config directory")
        except OSError:
            # Already exists
            pass

        try:
            os.mkdir(zenPath('log', 'nginx'))
            log.info("Created nginx log directory")
        except OSError:
            # Already exists
            pass

        if is_using_many_zopes():
            log.warn("Already using multiple Zopes; not switching to use zenwebserver by default.")
        else:
            replace_zopectl_in_daemons_txt()
            use_zenwebserver()
            log.info("Attempting to shut down running zopectl")
            subprocess.call([zenPath('bin', 'zopectl'), 'stop'])
            time.sleep(4) # Wait for it to shut down
            log.info("Configuring zenwebserver")
            subprocess.call([zenPath('bin', 'zenwebserver'), 'configure'])
        log.info("Installed successfully. Run 'zenwebserver start' to start the UI server.")


    def remove(self, dmd, leaveObjects=False):
        try:
            subprocess.call([zenPath('bin', 'zenwebserver'), 'stop'])
        except OSError:
            log.warn('Unable to shut down zenwebserver')
        if not leaveObjects: # upgrade
            use_zopectl()
            log.info("Uninstalling zenwebserver and nginx")
            for f in ('bin/zenwebserver', 'bin/nginx', 'etc/mime.types'):
                try:
                    os.remove(zenPath(f))
                except OSError:
                    log.info("%s doesn't exist, so not removing" % zenPath(f))
            try:
                shutil.rmtree(zenPath('etc', 'zope'))
            except OSError:
                log.info("Multi-zope config directory doesn't exist, so not removing")
            log.info("Uninstalled zenwebserver. You will need to start Zope.")
