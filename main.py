#!/usr/bin/python

import logging

import gdbmi
        

def main():
    logging.basicConfig(
        #level=logging.INFO,
        level=logging.DEBUG,
        format='%(asctime)s '\
            '%(levelname)s '\
            '%(pathname)s:%(lineno)s '\
            '%(message)s')

    s = gdbmi.Session("test/loop")

    token = s.hijack_function('poll', None)
    while not s.wait_for(token): pass


    token = s.exec_run()
    while not s.wait_for(token): pass

    while not s.wait_for(None):
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
                    while not s.wait_for(token): pass

                token = s.send('-var-create - * (*' +d['name'] + ')',
                               got_var)
                while not s.wait_for(token): pass
        return True    
    token = s.send("-stack-list-arguments 1 0 0", tweak_args)
    while not s.wait_for(token): pass

    # skip dummy() and return '1234'
    token = s.exec_return(1234)
    token = s.exec_continue()
    while not s.wait_for():
        if s.exec_state == "stopped":
            break


    token = s.send("-stack-list-arguments 1 0 0")
    while not s.wait_for(token): pass

    while not s.wait_for(None): pass

if __name__ == "__main__":
    main()
