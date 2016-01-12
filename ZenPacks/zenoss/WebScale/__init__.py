##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Globals
import os
import time
import shutil
import logging
import subprocess
from Products.ZenUtils.Utils import zenPath
from Products.ZenModel.ZenPack import ZenPackBase

from ZenPacks.zenoss.WebScale.config import ZopeConfig

log = logging.getLogger("zen.WebScale")

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

    def _copy(self, fro, to, backup=False):
        """
        Copy from a path within this zenpack to a path under $ZENHOME.
        Do NOT overwrite existing files unless backup is True
        Pass in tuples of path segments.
        """
        src = self.path(*fro)
        dest = zenPath(*to)
        if backup and os.path.exists(dest):
            # save file to backup
            shutil.copyfile(dest, '%s.prev' % dest)
        if backup or not os.path.exists(dest):
            shutil.copyfile(src, dest)

    def _create_zenhome_dirs(self, *dirs):
        """
        Creates directories (with mode 0755) in ZENHOME. zenPath is called
        on each directory name to normalize it relative to ZENHOME.
        """
        for d in map(zenPath, dirs):
            if not os.path.isdir(d):
                os.makedirs(d, mode=0755)

    def _remove_zenhome_files(self, *files):
        """
        Removes files in ZENHOME (if found). zenPath is called on each
        filename to normalize it relative to ZENHOME.
        """
        for f in map(zenPath, files):
            if os.path.exists(f):
                os.remove(f)

    def _remove_zenhome_dirs(self, *dirs):
        """
        Removes directores in ZENHOME (if found). zenPath is called on each
        directory name to normalize it relative to ZENHOME.
        """
        for d in map(zenPath, dirs):
            if os.path.isdir(d):
                shutil.rmtree(d)

    def install(self, dmd):
        # Run migrate scripts
        ZenPackBase.install(self, dmd)

        log.info("Installing zenwebserver and nginx to $ZENHOME/bin")
        # Create zenwebserver symlink
        self._symlink(('zenwebserver',), ('bin', 'zenwebserver'))
        self._executable('zenwebserver')

        # Create bin/nginx symlink
        self._symlink(('bin', 'nginx'), ('bin', 'nginx'))
        self._executable('bin', 'nginx')

        log.info("Installing nginx configuration to $ZENHOME/etc")

        zopeConfig = ZopeConfig()
        port = zopeConfig.http_base_port
        log.info("Detected Zope is using port %s" % port)

        # Replace strings in zenwebserver.conf
        with open(self.path('zenwebserver.conf'), 'r') as f, open(self.path('zenwebserver.conf.tmp'), 'w') as f2:
            f2.write(f.read()
                     .replace('<<INSTANCE_HOME>>', zenPath())
                     .replace('<<PORT>>', str(port)))

        # Create mime.types symlink
        self._symlink(('mime.types',), ('etc', 'mime.types'))

        # make sure the html directory exists
        self._create_zenhome_dirs('html','etc/zope','log/nginx','var/nginx/cache','var/nginx/tmp')

        # copy 50x page
        self._copy(('zenwebserver_50x.html',), ('html', 'zenwebserver_50x.html'))

        #copy nginx config template to etc
        self._copy(('nginx.conf.template',), ('etc', 'nginx.conf.template'), backup=True)

        # Copy in nginx configs, does not replace existing configs
        self._copy(('zenwebserver.conf.tmp',), ('etc', 'zenwebserver.conf'))
        self._copy(('nginx-zope.conf',), ('etc', 'nginx-zope.conf'))

        # Clean up
        os.remove(self.path('zenwebserver.conf.tmp'))

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

        # Remove old directories which are no longer used
        self._remove_zenhome_dirs('fastcgi_temp', 'scgi_temp', 'uwsgi_temp')

        if not leaveObjects: # upgrade
            use_zopectl()
            log.info("Uninstalling zenwebserver and nginx")
            remove_files = ('bin/zenwebserver', 'bin/nginx', 'etc/mime.types', 'html/zenwebserver_50x.html',
                            'etc/nginx.conf', 'etc/nginx-zope.conf')
            self._remove_zenhome_files(*remove_files)

            remove_dirs = ['etc/zope', 'var/nginx', 'var/nginx_temp', 'var/nginx-cache']
            # Remove Zope directories
            var_dir = zenPath('var')
            if os.path.isdir(var_dir):
                zope_dirs = (entry for entry in os.listdir(var_dir) if entry.startswith('zope'))
                for zope_dir in zope_dirs:
                    full_path = os.path.join(var_dir, zope_dir)
                    if os.path.isdir(full_path):
                        remove_dirs.append('var/' + zope_dir)
            self._remove_zenhome_dirs(*remove_dirs)
            log.info("Uninstalled zenwebserver. You will need to start Zope.")
