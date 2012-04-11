from fabric.api import sudo, run

def init():
    sudo('apt-get update')
    sudo('apt-get upgrade -y')

def r():
    run('whoami')
    run("python -c 'print 1+1'")
