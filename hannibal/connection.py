import boto
from boto import connect_autoscale
from boto.ec2.connection import EC2Connection
from boto.ec2.elb import ELBConnection
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.mturk.connection import MTurkConnection

class Connector(object):
    def cached_wrapper(func):
        def inner(self):
            attr = '_%s' % func.__name__
            if hasattr(self, attr):
                boto.log.debug('Fetching cached %s...' % attr)
                return getattr(self, attr)
            conn = func()
            boto.log.debug('Connecting %s...' % attr)
            setattr(self, attr, conn)
            return conn
        return property(inner)

    ec2 = cached_wrapper(EC2Connection)
    autoscale = cached_wrapper(connect_autoscale)
    mturk = cached_wrapper(MTurkConnection)
    elb = cached_wrapper(ELBConnection)
    cw = cached_wrapper(CloudWatchConnection)
