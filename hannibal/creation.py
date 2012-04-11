from boto import connect_autoscale
from boto.exception import EC2ResponseError, BotoServerError
from boto.ec2.connection import EC2Connection
from boto.ec2.elb import ELBConnection, HealthCheck
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.autoscale import LaunchConfiguration, \
                                    AutoScalingGroup, ScalingPolicy
from boto.mturk.connection import MTurkConnection



class Creator(dict):
    def __init__(self, conn, config):
        self.conn = conn
        self.config = config
        self.update(security_group=None, load_balancer=None, launch_config=None,
                    auto_scaling_group=None, health_checks=[], alarms=[])
        self.sync()

    def __repr__(self):
        return '<Creator for: %s>' % self.conn

    def delete(self):
        for func,args in (
            (self.conn.autoscale.delete_auto_scaling_group, (True,)),
            (self.conn.autoscale.delete_launch_configuration, ()),
            (self.conn.elb.delete_load_balancer, ()),
            (self.conn.ec2.delete_security_group, ()),
        ):
            func(self.config['name'], *args)

    def sync(self):
        for attr,func in (
                ('security_group', self.conn.ec2.get_all_security_groups),
                ('load_balancer', self.conn.elb.get_all_load_balancers),
                ('launch_config', self.conn.autoscale.get_all_launch_configurations),
                ('auto_scaling_group', self.conn.autoscale.get_all_groups)
        ):
            name = 'names'
            if attr == 'security_group':
                name = 'groupnames'
            elif attr == 'load_balancer':
                if not attr in self.config:
                    continue
                name = 'load_balancer_names'
            elif attr == 'auto_scaling_group' and not 'autoscale' in self.config:
                continue

            try:
                self[attr] = func(**{name: [self.config['name']]})[0]
            except IndexError:
                getattr(self, attr)()
            except (BotoServerError, EC2ResponseError) as e:
                if e.status/100 != 4:
                    raise
                getattr(self, attr)()

    def load_balancer(self):
        conf = self.config['load_balancer']
        self['load_balancer'] = lb = self.conn.elb.create_load_balancer(
                            name=self.config['name'], zones=self.config['zones'],
                            listeners=conf['listeners'])
                            #security_groups=[self.config['name']])
        for check in conf['health_checks']:
            self['health_checks'].append(lb.configure_health_check(
                                        HealthCheck(**check)))

    def security_group(self):
        self['security_group'] = self.conn.ec2.create_security_group(name=self.config['name'],
                                            description=self.config['name'])
        for rule in self.config['rules']:
            rule['group_name'] = self.config['name']
            assert_(self.conn.ec2.authorize_security_group(**rule),
                'Failed to authorize security group rule: %r' % rule)

    def launch_config(self):
        self['launch_config'] = lc = LaunchConfiguration(
                    connection=self.conn.autoscale,
                    name=self.config['name'],
                    image_id=self.config['instance']['image_id'],
                    key_name=self.config['instance']['key_name'],
                    instance_type=self.config['instance']['instance_type'],
                    security_groups=[self.config['name']])
        self.conn.autoscale.create_launch_configuration(lc)

    def auto_scaling_group(self):
        if not self['launch_config']:
            self.launch_config()

        opts = self.config['autoscale']
        policies = opts.pop('scaling_policies', [])
        opts.update(group_name=self.config['name'],
                    load_balancers=[self['load_balancer'].name],
                    availability_zones=self.config['zones'],
                    launch_config=self['launch_config'])
        self['auto_scaling_group'] = ag = AutoScalingGroup(**opts)
        self.conn.autoscale.create_auto_scaling_group(ag)
        for policy in policies:
            policy['name'] = '%s-%s' % (self.config['name'], policy['name'])
            if not 'adjustment_type' in policy:
                policy['adjustment_type'] = 'ChangeInCapacity'
            policy['as_name'] = self.config['name']
            alarms = policy.pop('alarms', [])
            policy = ScalingPolicy(**policy)
            self.conn.autoscale.create_scaling_policy(policy)
            for alarm in alarms:
                alarm = {
                    'namespace': 'AWS/EC2',
                    'metric': 'CPUUtilization' ,
                    'statistic': 'Average',
                    'period': '60',
                    'evaluation_periods': '2',
                    'actions_enabled': True
                }.update(alarm)
                alarm['name'] = '%s-%s' % (policy.name, alarm['name'])
                alarm['alarm_action'] = [self.config['name']]
                alarm['dimensions'] = {'AutoScalingGroupName': self.config['name']}
                alarm = MetricAlarm(**alarm)
                self.conn.cw.create_alarm(alarm)
                self['alarms'].append(alarm)
