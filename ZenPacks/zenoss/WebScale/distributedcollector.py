##########################################################################
#
#   Copyright 2012 Zenoss, Inc. All Rights Reserved.
#
##########################################################################
import os
from subprocess import check_output, CalledProcessError
from zope.interface import implements
from zope.component import adapts
from Products.ZenUtils.Utils import zenPath
from ZenPacks.zenoss.DistributedCollector.DCUtils import CollectorConfFactory
from ZenPacks.zenoss.DistributedCollector.interfaces import IRemoteRenderUrlProvider
from Products.ZenWidgets.messaging import IMessageSender, WARNING

import logging
log = logging.getLogger("zen.webscale_dc")

_ZENRENDER_PORT = 8091

class WebScaleRenderUrlProvider(object):
    implements(IRemoteRenderUrlProvider)
    adapts(CollectorConfFactory)


    def __init__(self, confFactory):
        self.confFactory = confFactory

    def get_render_url(self):
        return '/remote-collector/%s' % self.confFactory._monitorName


def onCollectorInstalled(ob, event):
    errorMsg = _reconfigureNginx(ob.id, ob.hostname)
    if errorMsg:
        IMessageSender(ob).sendToBrowser('Error', errorMsg, WARNING)

def onCollectorDeleted(ob, event):
    filePath = _dcNginxConfPath(ob.id)
    try:
        os.remove(filePath)
    except Exception:
        pass

def onCollectorUpdated(ob, event):
    changes = event.propertyChanges
    if changes.has_key('hostname') or changes.has_key('renderurl') :
        errorMsg = _reconfigureNginx(ob.id, ob.hostname)
        if errorMsg:
            IMessageSender(ob).sendToBrowser('Error', errorMsg, WARNING)

def _reconfigureNginx(id, host):
    errorMsg = None
    try:
        #overwrite nginx conf for this collector
        _writeDcConf(id, host)
    except Exception as e:
        errorMsg = "Could not write Nginx configuration for collector %s: %s" % (id , e)
        log.warn(errorMsg)
    else:
        #reload nginx config
        try:
            _reloadNginxConf()
        except CalledProcessError as cpe:
            errorMsg = cpe.output
        except Exception as e:
            errorMsg = "Could not reload Nginx configuration: %s" % str(e)
            log.warn(errorMsg)
    return errorMsg

_NGINX_CONF_TMPL = """
location ^~ /remote-collector/{collectorId}/ {{
    rewrite ^/remote-collector/(.*)$ /$1 break;
    proxy_pass http://{collectorHost}:{collectorPort};

    proxy_set_header        Host    $host;
    proxy_set_header        X-Real-IP $remote_addr;
    proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
    }}
"""

def _writeDcConf(id, host):
    confValues = {'collectorId': id,
                  'collectorHost': host,
                  'collectorPort': _ZENRENDER_PORT}
    conf = _NGINX_CONF_TMPL.format(**confValues)
    filePath = _dcNginxConfPath(id)
    with open(filePath, 'w') as confFile:
        confFile.write(conf)

def _dcNginxConfPath(id):
    confName = 'nginx-dc-{collectorId}.conf'.format(collectorId=id)
    filePath = zenPath('etc', confName)
    return filePath

def _reloadNginxConf():
    return check_output([zenPath('bin','zenwebserver'), ' reload'])
