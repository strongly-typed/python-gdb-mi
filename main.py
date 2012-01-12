#!/usr/bin/python

import logging

import gdbmi
        

def main():
    logging.basicConfig(
        level=logging.INFO,
        #level=logging.DEBUG,
        format='%(asctime)s '\
            '%(levelname)s '\
            '%(pathname)s:%(lineno)s '\
            '%(message)s')

    s = gdbmi.Session("test/loop")

    def dump_syms(token, obj):
        for d in obj.args['symbols']:
            logging.warn([d])
        return True
    token = s.send("-symbol-list-variables", dump_syms)
    while not s.block(token): pass


    s.insert_break('dummy')
    s.insert_break('poll')
    token = s.exec_run()
    while not s.block(token): pass

    while not s.block(None):
        if s.exec_state == "stopped":
            break

    def tweak_args(token, obj):
        stack = obj.args['stack-args'][0]
        frame = stack['frame']
        for d in frame['args']:
            logging.warn([d['name'], d['value']])
            if d['name'] == 'src':
                addr = int(d['value'], 16)

                def got_var(token, obj):
                    name = obj.args['name']
                    logging.error(name)
                    # set value of arg (*var) = 99
                    s.send('-var-assign ' + name + " 99")
                    s.send('-var-update ' + name )
                    token = s.send('-var-delete ' + name)
                    while not s.block(token): pass

                token = s.send('-var-create - * (*' +d['name'] + ')',
                               got_var)
                while not s.block(token): pass
        return True    
    token = s.send("-stack-list-arguments 1 0 0", tweak_args)
    while not s.block(token): pass

    # skip dummy() and return '1234'
    token = s.send("-exec-return 1234")
    token = s.send("-exec-continue")
    while not s.block():
        if s.exec_state == "stopped":
            break

    def hijack_pool(token, obj):
        stack = obj.args['stack-args'][0]
        frame = stack['frame']
        for d in frame['args']:
            logging.warn([d['name'], d['value']])
            if d['name'] == 'fds':
                addr = int(d['value'], 16)

                def got_var(token, obj):
                    name = obj.args['name']
                    logging.error(name)
                    s.send('-var-assign ' + name + " 1")
                    s.send('-var-update ' + name )
                    token = s.send('-var-delete ' + name)
                    while not s.block(token): pass

                token = s.send('-var-create - * fds[0].fd',
                               got_var)
                while not s.block(token): pass
        return True    


    token = s.send("-stack-list-arguments 1 0 0", hijack_pool)
    while not s.block(token): pass

    token = s.send("-exec-return 1")
    while not s.block(token): pass

    token = s.send("-exec-continue")
    while not s.block(token): pass

if __name__ == "__main__":
    main()
