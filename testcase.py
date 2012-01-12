#!/usr/bin/python

import logging

import gdbmi
        
def test_lib(path):
    """
    >>> test_lib("/usr/lib/libcairo.so.2.11000.2")
    """
    logging.basicConfig(
        level=logging.INFO,
#        level=logging.DEBUG,
        format='%(asctime)s '\
            '%(levelname)s '\
            '%(pathname)s:%(lineno)s '\
            '%(message)s')

    p = gdbmi.Session(path)

    def dump(token, obj):
        for d in obj.args['symbols']:
            if (d.get('block', None) == 'static' and
                not d['name'].startswith('_')):
                logging.warn([d])
        return True
    token = p.send("-symbol-list-variables", dump)
    while not p.block(token): pass


def test_cpp(path):
    """
    >>> test_cpp("test/mangled")
    """

    logging.basicConfig(
        level=logging.INFO,
#        level=logging.DEBUG,
        format='%(asctime)s '\
            '%(levelname)s '\
            '%(pathname)s:%(lineno)s '\
            '%(message)s')

    p = gdbmi.Session(path).start()

    token = p.send("-enable-timings")
    token = p.send("-list-features")
    while not p.block(token): pass

    def dump(token, obj):
        for d in obj.args['symbols']:
            if d.get('file', '').endswith('cpp'):
                logging.warn([d])
        return True
    token = p.send("-symbol-list-variables", dump)
    while not p.block(token): pass

    token, pty = p.inferior_tty_set()
    while not p.block(token): pass


    token = p.send("-exec-run")
    while not p.block(token): pass

    token = p.send("-symbol-list-lines hello.c")
    token = p.send("-data-list-changed-registers")
    token = p.send("-data-list-register-names")
    token = p.send("-data-list-register-values x 0")
    while not p.block(token): pass

    token = p.send("-data-evaluate-expression main")
    token = p.send("-data-read-memory main x 8 1 1")
    while not p.block(token): pass

    token = p.send("-stack-list-variables --all-values")
    while not p.block(token): pass


    token = p.send("-exec-continue")
    while not p.block(token): pass

    token = p.send("-exec-continue")
    while not p.block(token): pass

def test(path):
    """
    >>> test("test/hello")

    >>> test("test/hello_nodebug")
    """
    logging.basicConfig(
        level=logging.INFO,
#        level=logging.DEBUG,
        format='%(asctime)s '\
            '%(levelname)s '\
            '%(pathname)s:%(lineno)s '\
            '%(message)s')

    p = gdbmi.Session(path).start()

#    pid = os.getpid()
#    (master, slave) = os.openpty()
#    slave_node = "/proc/%d/fd/%d" % (pid, slave)

#    token = p.send("-inferior-tty-set " + slave_node)
#    while not p.block(token): pass

    token = p.send("-enable-timings")
    token = p.send("-list-features")
    while not p.block(token): pass


    def dump(token, obj):
        for d in obj.args['symbols']:
            if (1 or d['name'].startswith('test_')):
                logging.warn(["    ", d])
        logging.warn([obj.args['time']])
        return True

    token = p.send("-symbol-list-variables", dump)
#    token = p.send("-symbol-list-variables")
    while not p.block(token): pass

    token = p.send("-exec-run")
    while not p.block(token): pass

    token = p.send("-rubbish")
    while not p.block(token): pass

    token = p.send("-list-thread-groups")
    while not p.block(token): pass

    token = p.send("-symbol-list-lines hello.c")
    token = p.send("-data-list-changed-registers")
    token = p.send("-data-list-register-names")
    token = p.send("-data-list-register-values x 0")
    while not p.block(token): pass

    token = p.send("-data-evaluate-expression main")
    token = p.send("-data-read-memory main x 8 1 1")
    while not p.block(token): pass

    token = p.send("-data-read-memory-bytes &test_i1 4")
    token = p.send('-data-write-memory-bytes &test_i1 "09080706"')
    while not p.block(token): pass

    token = p.send("-stack-list-variables --all-values")
    while not p.block(token): pass




    token = p.send('-var-create var2 * test_i2')
    token = p.send("-var-assign var2 3")
    token = p.send("-var-update *")
    while not p.block(token): pass

    token = p.send("-exec-continue")
    while not p.block(token): pass

    token = p.send("-exec-continue")
    while not p.block(token): pass

def test_vars(path):
    """
    #>>> test_vars("test/hello")
    """
    logging.basicConfig(
        level=logging.INFO,
#        level=logging.DEBUG,
        format='%(asctime)s '\
            '%(levelname)s '\
            '%(pathname)s:%(lineno)s '\
            '%(message)s')

    p = gdbmi.Session(path).start()

    def dump(token, obj):
        for d in obj.args['symbols']:
            logging.warn([d])
        return True
    token = p.send("-symbol-list-variables", dump)
#    token = p.send("-symbol-list-variables")
    while not p.block(token): pass

def test_simple(path):
    """
    >>> test_simple("test/hw")
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s '\
            '%(levelname)s '\
            '%(pathname)s:%(lineno)s '\
            '%(message)s')

    p = gdbmi.Session(path).start()

    def dump(token, obj):
        for d in obj.args['symbols']:
            logging.warn([d])
        return True
    token = p.send("-symbol-list-variables", dump)
    while not p.block(token): pass

if __name__ == "__main__":
    import doctest
    doctest.testmod()
