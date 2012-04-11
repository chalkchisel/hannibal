Hannibal
=========

AWS Cluster Management Toolkit
-------------------------------

- Manages
    - EC2 Instances
    - Security Groups
    - Load Balancers
    - Auto Scaling Triggers
    - Instance Deployment/Provisioning w/ Fabric

Example
---------

    $ ./hannibal.py config.json
    >>> inst = s.launch()[0]
    >>> inst
    Instance:i-6cec5c0b
    >>> inst.update()
    'pending'
    >>> inst.update()
    'running'
    >>> inst.public_dns_name
    'ec2-107-22-90-34.compute-1.amazonaws.com'
    >>> s.ssh(inst)
