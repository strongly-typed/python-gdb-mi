#!/usr/bin/python

import subprocess
import fcntl
import os
import logging
import select

import output

class Session(object):
    def __init__(self, debuggee, gdb="gdb"):
        """
        >>> p = Session("test/hello")
        """
        self.debuggee = debuggee

        p = subprocess.Popen(
            bufsize = 0,
            args = [gdb,
                    '--return-child-result',
                    '--quiet', # inhibit dumping info at start-up
                    '--nx', # inhibit window interface
                    '--nw', # ignore .gdbinit
                    '--interpreter=mi2', # use GDB/MI v2
                    #'--write', # to-do: allow to modify executable/cores? 
                    self.debuggee],
            stdin = subprocess.PIPE, stdout = subprocess.PIPE,
            close_fds = True
            )
        fl = fcntl.fcntl(p.stdout, fcntl.F_GETFL)
        fcntl.fcntl(p.stdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        self.process = p
        self.buf = ""
        self.is_attached = False

        self.thread_groups = {}
        self.breakpoints = {}

        self.commands = {}
        self._callbacks = {}
        self._hijacked = {}

        self.exec_state = None
        self.token = 0
        logging.debug(['session', debuggee, 'gdb', gdb])


    def dump_obj(self, token, obj):
        logging.error(['##### DUMP:', token, obj])

    def hijack_function(self, name, replacement):
        def thunk(token, obj):
            replacement(obj)
        def register_replacement(token, obj):
            self.dump_obj(token, obj)
        
        return self.break_insert(name, register_replacement)

    def start(self, token = ""):
        if self.is_attached:
            raise ValueError()

        self.send("-break-insert main")
        return self

    def break_insert(self, location, handler = None):
        return self.send("-break-insert " + location,
                         handler)

    def target_select_remote(self, handler = None):
        return self.send("-target-select remote :3333")
    def monitor_reset_halt(self, handler = None):
        return self.send('-interpreter-exec console "monitor reset halt"')
    def exec_advance(self, target, handler = None):
        return self.send('-interpreter-exec console "advance %s"' % target)
    def exec_continue(self, handler = None):
        return self.send("-exec-continue", handler)
    def exec_run(self, handler = None):
        return self.send("-exec-run", handler)
    def exec_return(self, value = None, handler = None):
        if value is None:
            return self.send("-exec-return", handler)
        return self.send("-exec-return " + str(value), handler)

    def send(self, cmd, handler = None):
        self.token += 1
        token = "%04d" % self.token
        p = self.process
        p.stdin.write(token + cmd + "\n")
        p.stdin.flush()
        logging.debug(["SENT[" + token +"]:", cmd])
        self.commands[token] = {'cmd': cmd,
                                'handler': handler,
                                }
        return token

    def _read(self, blocking = 0):
        p = self.process
        while select.select([p.stdout], [], [], blocking)[0]:
            try:
                yield p.stdout.read()
                blocking = 0
            except IOError:
                break

    def _parse_line(self, line):
        token = ""
        logging.debug(["RAW:", line])

        if not line:
            return

        if line.startswith('(gdb)'):
            # terminator
            yield (token, output.Terminator())
            return
        logging.debug(line)
        while line[0] in "0123456789":
            token = token + line[0]
            line = line[1:]
        for klass in output.PARSERS:
            if line.startswith(klass.TOKEN):
                line = line.replace('debug-request, current', 'debug-request. current')
                yield (token, klass(line))
                return

        logging.debug([line])
        #raise ValueError((token, line))

    def _handle_exec(self, token, obj):
        if obj.what in ("stopped", "running"):
            self.exec_state = obj.what
        
    def _handle_result(self, token, obj):
        handled = False
        if obj.what == "done" or obj.what == "running":
            self.commands[token]['state'] = obj.what
            # lookup handler for the token
            if self.commands[token]['handler']:
                handled = self.commands[token]['handler'](token, obj)

            if 'bkpt' in obj.args:
                self._update_breakpoint(obj.args['bkpt'])
                handled = True
        return handled

    def _handle_notify(self, token, obj):
        if obj.what == "thread-group-added":
            tg = self._add_thread_group(obj.args)
            logging.debug(tg)
            return True

        if obj.what == "thread-group-started":
            tg = self.thread_groups[obj.args['id']]
            tg['pid'] = obj.args['pid']
            logging.debug(tg)
            return True

        if obj.what == "thread-created":
            tg = self.thread_groups[obj.args['group-id']]
            tg['threads'].add(obj.args['id'])
            logging.debug(tg)
            return True

        if obj.what == "library-loaded":
            tg = self.thread_groups[obj.args['thread-group']]
            tg['dl'][obj.args['id']] = obj.args
            logging.debug(tg)
            return True

        if obj.what == "breakpoint-modified":
            self._update_breakpoint(obj.args['bkpt'])
            return True
        
    def _add_thread_group(self, info, group_id = None):
        if group_id is None:
            group_id = info['id']
        tg = {
            'id': group_id,
            "pid": None,
            "threads": set(),
            "dl": {},
            }
        self.thread_groups[group_id] = tg
        logging.debug(tg)

    def add_callback(self, target, proc, filter = None, *kwds):
        to_add = {
            'proc': proc,
            'kwds': kwds,
            'filter': filter,
            }
        self._callbacks.setdefault(target, []).append(to_add)

    def _callback(self, target, **kwds):
        for to_call in self._callbacks.get(target, []):
            if ('filter' in to_call) and (not to_call['filter'](kwds)):
                continue
            tmp_kwds = dict(kwds)
            tmp_kwds.update(to_call)
            to_call['proc'](tmp_kwds)
    
    def _update_breakpoint(self, info, number = None):
        if number is None:
            number = info['number']
        if number in self.breakpoints:
            self.breakpoints[number].update(info)
        else:
            self.breakpoints[number] = dict(info)

        logging.debug(['updated BREAKPOINT', self.breakpoints[number]])
        self._callback('bkpt')

    def _handle(self, token, obj):
        handler = {
            output.NotifyAsync.TOKEN   : self._handle_notify,
            output.ExecAsync.TOKEN     : self._handle_exec,
            output.Result.TOKEN        : self._handle_result,
            output.ConsoleStream.TOKEN : (lambda t,o:True),
            output.Terminator.TOKEN    : (lambda t,o:True),
            }.get(obj.TOKEN, None)

        if not (handler and handler(token, obj)):
            logging.debug(["IGN:", token, obj])

    def read(self, blocking = 0):
        for src in self._read(blocking):            
            self.buf += src
            while True:
                (line, sep, self.buf) = self.buf.partition('\n')
                if sep:
                    for token, obj in self._parse_line(line):
                        self._handle(token, obj)
                        yield (token, obj)
                else:
                    self.buf = line
                    break

    def is_running(self):
        return (self.process.poll() is None)

    def wait_for(self, stop_token = None):
        for token, obj in self.read(1):
            if token == stop_token:
                return True
        return False


    def inferior_tty_set(self):
        pid = os.getpid()
        (master, slave) = os.openpty()
        slave_node = "/proc/%d/fd/%d" % (pid, slave)
        
        return (self.send("-inferior-tty-set " + slave_node), master)
