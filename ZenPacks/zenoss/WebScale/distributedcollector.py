##########################################################################
#
#   Copyright 2012 Zenoss, Inc. All Rights Reserved.
#
##########################################################################
from zope.interface import implements
from zope.component import adapts
from ZenPacks.zenoss.DistributedCollector.DCUtils import CollectorConfFactory
from ZenPacks.zenoss.DistributedCollector.interfaces import IRemoteRenderUrlProvider

class WebScaleRenderUrlProvider(object):
    implements(IRemoteRenderUrlProvider)
    adapts(CollectorConfFactory)

    ZENRENDER_PORT = 8091

    def __init__(self, confFactory):
        self.confFactory = confFactory

    def get_render_url(self):
        return '/remote-collector/%s:%s/%s' % (self.confFactory._host, self.ZENRENDER_PORT,
                                               self.confFactory._monitorName)

