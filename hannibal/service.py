from json import load

from .connection import Connector
from .creation import Creator
from .deploy import Deployment


class Service(dict):
    def __init__(self, config_or_file):
        if not hasattr(config_or_file, 'read') and isinstance(config_or_file, str):
            config_or_file = open(config_or_file, 'rb')

        self.config = load(config_or_file)
        self.conn = Connector()
        self.cre = Creator(self.conn, self.config)
        self.deploy = Deployment(self)
        self.update(instances=[])
        self.sync()
        self.deploy.setup()

    def __repr__(self):
        return '<Service %s>' % self.config['name']

    def sync(self):
        self.cre.sync()
        self.update(self.cre)
        self['instances'] = self['security_group'].instances()
        if self['auto_scaling_group']:
            self['instances'].extend(self['auto_scaling_group'].instances)

    def delete(self):
        self.terminate()
        self.cre.delete()

    @property
    def ids(self):
        l = []
        for ins in self['instances']:
            if hasattr(ins, 'id'):
                l.append(ins.id)
            elif hasattr(ins, 'instance_id'):
                l.append(ins.instance_id)
        return l

    @property
    def hosts(self):
        l = []
        for ins in self['instances']:
            if ins.public_dns_name:
                l.append(ins.public_dns_name)
        return l

    def tag(self, *resources, **tags):
        if len(resources) and not isinstance(resources[0], str):
            resources = [r.id for r in resources]
        return self.conn.ec2.create_tags(resources, tags)

    def launch(self, **opts):
        opts['security_groups'] = [self.config['name']]
        if not 'placement' in opts:
            opts['placement'] = self.config['zones'][0]
        opts.update(self.config['instance'])
        runner = self.conn.ec2.run_instances
        if 'price' in opts:
            runner = self.conn.ec2.request_spot_instances
        instances = runner(**opts).instances
        self.tag(*instances, Name=self.config['name'])
        self['instances'].extend(instances)
        return instances

    def updateall(self):
        d = {}
        for ins in self['instances']:
            d[ins] = ins.update()
        return d

    def start(self):
        return self.conn.ec2.start_instances(self.ids)

    def stop(self, force=False):
        return self.conn.ec2.stop_instances(self.ids, force=force)

    def terminate(self):
        return self.conn.ec2.terminate_instances(self.ids)

    def ssh(self, instance):
        from subprocess import call

        ifile = self.config['identity_file']
        user = self.config['user']
        call(['ssh', '-i', ifile, '%s@%s' % (user, instance.public_dns_name)])
