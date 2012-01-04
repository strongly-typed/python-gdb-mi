#!/usr/bin/python

import os
import sys
import select
import subprocess
import fcntl
import time
import logging


class MiFrame(object):
    def __init__(self):
        self.level = None # level  from 0
        self.func = None # function corresponding to the frame.
        self.addr = None # code address
        self.file = None # name of the source file
        self.line = None # source line
        self.binary = None # name of the binary file
 
class MiCommand(object):
    def __init__(self, op, opts, params = None):
        self.op = op
        self.opts = opts
        self.params = params

    def encode(self):
        """
        >>> MiCommand("test", []).encode()
        '-test\\n'
        """
        if self.params is None:
            param_str = ""
        else:
            param_str = " -- " + " ".join(self.params)
        return ("-" +
                " ".join([self.op] + self.opts) +
                param_str + "\n")

class MiOutput(object):
    TOKEN = None # should be overridden
    is_terminator = False
    def __init__(self, src):
        if src[0] != self.TOKEN:
            raise ValueError(src)
        src = src[1:]
        self.what, sep, src = src.partition(',')
        self.args = {}
        while src:
            pair, left =  self.parse_result(src)
            if pair:
                (k, v) = pair
                self.args[k] = v
            else:
                break
            src = left[1:]
            if not src:
                break
            if left[0] != ',':
                raise ValueError(src)

    def __repr__(self):
        return "<< %s [%s]: %s>>" % (self.__class__.__name__[8:],
                                  self.what, self.args)

    @classmethod
    def parse_tuple(self, src):
        """
        >>> MiOutput.parse_tuple("{}")
        ({}, '')
        """
        ret = {}
        src = src[1:]
        if src[0] == "}":
            return ret, src[1:]
        while src:
            ((k, v), left) = self.parse_result(src)
            ret[k] = v
            src = left[1:]
            if left[0] == "}":
                break
            if not left.startswith(','):
                raise ValueError(left)
        return ret, src

    @classmethod
    def parse_const(self, src):
        """
        >>> MiOutput.parse_const('""')
        ('', '')
        >>> MiOutput.parse_const('"abc"')
        ('abc', '')
        >>> MiOutput.parse_const('"abc","123"')
        ('abc', ',"123"')
        >>> MiOutput.parse_const('"abc\\\\"1"')
        ('abc\\\\"1', '')
        """
        limit = len(src)
        tail = 1
        while src[tail] != '"':
            if src[tail] == "\\": #escape
                tail += 1
            tail += 1
            if tail >= limit:
                raise ValueError(src)
        return (src[1:tail], src[tail+1:])

    @classmethod
    def parse_list(self, src):
        """
        >>> MiOutput.parse_list("[]")
        ([], '')
        >>> MiOutput.parse_list("[],123")
        ([], ',123')
        >>> MiOutput.parse_list('["a","b","c"]')
        (['a', 'b', 'c'], '')
        >>> MiOutput.parse_list("[[]],123")
        ([[]], ',123')
        >>> MiOutput.parse_list("[[],[]],123")
        ([[], []], ',123')
        >>> MiOutput.parse_list('[[["a"]],["b"]],123')
        ([[['a']], ['b']], ',123')
        """
        ret = []
        src = src[1:]
        if src[0] == ']':
            return ret, src[1:]
        while src:
            value, left = self.parse_value(src)
            ret.append(value)
            src = left[1:]
            if left.startswith(']'):
                break
            if not left.startswith(','):
                raise ValueError(left)
        return ret, src

    @classmethod
    def parse_value(self, src):
        if src.startswith('{'):
            return self.parse_tuple(src)
        if src.startswith('['):
            return self.parse_list(src)
        if src.startswith('"'):
            return self.parse_const(src)
        raise ValueError(src)

    @classmethod
    def parse_result(self, src):
        """ key-value pair
        >>> MiOutput.parse_result('a="1"')
        (('a', '1'), '')
        >>> MiOutput.parse_result('a="1",foo')
        (('a', '1'), ',foo')
        """
        (variable, sep, value_str) = src.partition('=')
        value, left = self.parse_value(value_str)
        return ((variable, value), left)

class MiOutputResult(MiOutput):
    TOKEN = '^'
    CANDS = ("done",
             "running",   # equivalent to 'done'
             "connected", # to remote target
             "error",
             "exit",
             )

class MiOutputOOB(MiOutput):
    TOKEN = None

class MiOutputExecAsync(MiOutputOOB):
    TOKEN = "*"

class MiOutputStatusAsync(MiOutputOOB):
    TOKEN = "+"

class MiOutputNotifyAsync(MiOutputOOB):
    TOKEN = "="

class MiOutputStream(MiOutputOOB): pass

class MiOutputConsoleStream(MiOutputStream):
    TOKEN = "~"

class MiOutputTargetStream(MiOutputStream):
    TOKEN = "@"

class MiOutputLogStream(MiOutputStream):
    TOKEN = "&"

class MiOutputTerminator(MiOutput):
    is_terminator = True
    def __init__(self): pass
    def __repr__(self): return "<<Term>>"

class Session(object):
    def __init__(self, debugee):
        """
        >>> p = Session("test/hello")
        """
        self.debugee = debugee
        p = subprocess.Popen(
            bufsize = 0,
            args = ["gdb", '--quiet', '--nw', '--nx', '--interpreter=mi2',
                    self.debugee],
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
        self.exec_state = None
        self.token = 0

    def start(self, token = ""):
        if self.is_attached:
            raise ValueError()

        self.send("-break-insert main")
        return self

    def send(self, cmd, handler = None):
        self.token += 1
        token = "%04d" % self.token
        p = self.process
        p.stdin.write(token + cmd + "\n")
        p.stdin.flush()
        logging.warn(["SENT:", cmd, token])
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

        if line.startswith('(gdb)'):
            # terminator
            yield (token, MiOutputTerminator())
            return

        while line[0] in "0123456789":
            token = token + line[0]
            line = line[1:]
        for klass in (MiOutputResult,
                      MiOutputExecAsync,
                      MiOutputStatusAsync,
                      MiOutputNotifyAsync,
                      MiOutputConsoleStream,
                      MiOutputTargetStream,
                      MiOutputLogStream,
                      ):
            if line.startswith(klass.TOKEN):
                yield (token, klass(line))
                return

        logging.warn([line])
        #raise ValueError((token, line))

    def _handle_exec(self, token, obj):
        if obj.what == "stopped":
            self.exec_state = obj.what
        
    def _handle_result(self, token, obj):
        if obj.what == "done" or obj.what == "running":
            self.commands[token]['state'] = obj.what
            if 'bkpt' in obj.args:
                self._update_breakpoint(obj.args['bkpt'])
                return True

    def _handle_notify(self, token, obj):
        if obj.what == "thread-group-added":
            tg = self._add_thread_group(obj.args)
            logging.info(tg)
            return True

        if obj.what == "thread-group-started":
            tg = self.thread_groups[obj.args['id']]
            tg['pid'] = obj.args['pid']
            logging.info(tg)
            return True

        if obj.what == "thread-created":
            tg = self.thread_groups[obj.args['group-id']]
            tg['threads'].add(obj.args['id'])
            logging.info(tg)
            return True

        if obj.what == "library-loaded":
            tg = self.thread_groups[obj.args['thread-group']]
            tg['dl'][obj.args['id']] = obj.args
            logging.info(tg)
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
        logging.info(tg)

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

    def _handle(self, token, obj):
        handler = {
            MiOutputNotifyAsync.TOKEN   : self._handle_notify,
            MiOutputExecAsync.TOKEN     : self._handle_exec,
            MiOutputResult.TOKEN        : self._handle_result,
            MiOutputConsoleStream.TOKEN : (lambda t,o:True),
            MiOutputTerminator.TOKEN    : (lambda t,o:True),
            }.get(obj.TOKEN, None)

        if not (handler and handler(token, obj)):
            logging.warn([token, obj])

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

    def block(self, stop_token = None):
        for token, obj in self.read(1):
            if token == stop_token:
                return True
        return False
        
def test():
    """
    >>> test()
    """
    logging.basicConfig(
        level=logging.INFO,
#        level=logging.DEBUG,
        format='%(asctime)s '\
            '%(levelname)s '\
            '%(pathname)s:%(lineno)s '\
            '%(message)s')

    p = Session("test/hello").start()

#    pid = os.getpid()
#    (master, slave) = os.openpty()
#    slave_node = "/proc/%d/fd/%d" % (pid, slave)

#    token = p.send("-inferior-tty-set " + slave_node)
#    while not p.block(token): pass

    token = p.send("-enable-timings")
    token = p.send("-list-features")
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

    token = p.send("-data-read-memory-bytes &i1 4")
    token = p.send('-data-write-memory-bytes &i1 "09080706"')
    while not p.block(token): pass

    token = p.send("-stack-list-variables --all-values")
    while not p.block(token): pass


    token = p.send('-var-create var2 * i2')
    token = p.send("-var-assign var2 3")
    token = p.send("-var-update *")
    while not p.block(token): pass

    token = p.send("-exec-continue")
    while not p.block(token): pass

    token = p.send("-exec-continue")
    while not p.block(token): pass

if __name__ == "__main__":
    import doctest
    doctest.testmod()
