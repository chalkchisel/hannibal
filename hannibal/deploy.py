from fabric.state import env
from fabric.main import load_fabfile
from fabric.tasks import execute


class Deployment(object):
    def __init__(self, service):
        self._service = service

    def setup(self):
        conf = self._service.config
        env.user = conf['user']
        env.key_filename = conf['identity_file']
        if 'fabric' in conf:
            env.update(conf['fabric'])
        for name, func in load_fabfile(conf['fabfile'])[1].items():
            setattr(self, name, lambda *a,**kw: execute(
                func, hosts=self._service.hosts,
                *a, **kw
            ))


