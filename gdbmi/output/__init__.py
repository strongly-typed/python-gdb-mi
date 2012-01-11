#!/usr/bin/python

class _Output(object):
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

class Result(_Output):
    TOKEN = '^'
    CANDS = ("done",
             "running",   # equivalent to 'done'
             "connected", # to remote target
             "error",
             "exit",
             )

class _OOB(_Output):
    TOKEN = None

class ExecAsync(_OOB):
    TOKEN = "*"

class StatusAsync(_OOB):
    TOKEN = "+"

class NotifyAsync(_OOB):
    TOKEN = "="

class _Stream(_OOB):
    pass

class ConsoleStream(_Stream):
    TOKEN = "~"

class TargetStream(_Stream):
    TOKEN = "@"

class LogStream(_Stream):
    TOKEN = "&"

class Terminator(_Output):
    is_terminator = True
    def __init__(self): pass
    def __repr__(self): return "<<Term>>"
