class ServiceException(Exception):
    pass

def assert_(expr, msg):
    try:
        assert expr
    except AssertionError:
        raise ServiceException(msg)

