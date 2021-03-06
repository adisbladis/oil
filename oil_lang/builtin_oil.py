#!/usr/bin/env python2
"""
builtin_oil.py - Oil builtins.

See rfc/0024-oil-builtins.md for notes.

env: Should be in builtin_compat.py?

It's sort of like xargs too.
"""
from __future__ import print_function

import sys

from _devbuild.gen.runtime_asdl import value_e

from core.util import log
from frontend import args
from frontend import match


class Repr(object):
  """Given a list of variable names, print their values.

  'repr a' is a lot easier to type than 'argv.py "${a[@]}"'.
  """
  def __init__(self, mem, errfmt):
    self.mem = mem
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    status = 0
    for i in xrange(1, len(arg_vec.strs)):
      name = arg_vec.strs[i]
      if not match.IsValidVarName(name):
        raise args.UsageError('got invalid variable name %r' % name,
                              span_id=arg_vec.spids[i])

      cell = self.mem.GetCell(name)
      if cell is None:
        print('%r is not defined' % name)
        status = 1
      else:
        sys.stdout.write('%s = ' % name)
        cell.PrettyPrint()  # may be color
        sys.stdout.write('\n')
    return status


class Push(object):
  """Push args onto an array.

  Note: this could also be in builtins_pure.py?
  """
  def __init__(self, mem, errfmt):
    self.mem = mem
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    arg_r = args.Reader(arg_vec.strs, spids=arg_vec.spids)
    arg_r.Next()  # skip 'push'

    var_name, var_spid = arg_r.ReadRequired2(
        'requires a variable name')

    if var_name.startswith(':'):  # optional : sigil
      var_name = var_name[1:]

    if not match.IsValidVarName(var_name):
      raise args.UsageError('got invalid variable name %r' % var_name,
                            span_id=var_spid)

    val = self.mem.GetVar(var_name)
    # TODO: value.Obj too
    if val.tag != value_e.MaybeStrArray:
      self.errfmt.Print("%r isn't an array", var_name, span_id=var_spid)
      return 1

    val.strs.extend(arg_r.Rest())
    return 0


class Use(object):
  """use lib, bin, env.  Respects namespaces.

  use lib foo.sh {  # "punning" on block syntax.  1 or 3 words.
    func1
    func2 as myalias
  }
  """

  def __init__(self, mem, errfmt):
    self.mem = mem
    self.errfmt = errfmt

  def __call__(self, cmd_val):
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip 'use'

    # TODO:
    # - Does shopt -s namespaces have to be on?
    #   - I don't think so?  It only affects 'procs', not funcs.

    arg = arg_r.Peek()

    # 'use bin' and 'use env' are for static analysis.  No-ops at runtime.
    if arg in ('bin', 'env'):
      return 0

    if arg == 'lib':  # OPTIONAL lib
      arg_r.Next()

    # Cosmetic: separator for 'use bin __ grep sed'.  Allowed for 'lib' to be
    # consistent.
    arg = arg_r.Peek()
    if arg == '__':  # OPTIONAL __
      arg_r.Next()

    # Now import everything.
    rest = arg_r.Rest()
    for path in rest:
      log('path %s', path)

    return 0


class Env(object):
  """env {} blocks are preferred over 'export'."""
  pass


class Fork(object):
  """Replaces &.  Takes a block.

  Similar to Wait, which is in osh/builtin_process.py.
  """
  pass


class Opts(object):
  """getopts replacement.

  opts :grep_opts {
    flag -v --invert Bool "Invert"
    flag -A --after Int "Lines after"
    flag -t --timeout Float "Seconds to wait" { default = 1.0 }

    # / pattern file* /
    arg 1 pattern "Regular expression"
    arg 2- file "Regular expression"
  }
  var opt = grep_opts.Parse(ARGV)
  opt.invert
  opt.after
  opt.pattern
  opt.file
  """
  def __init__(self, mem, errfmt):
    self.mem = mem
    self.errfmt = errfmt

  def __call__(self, cmd_val):
    raise NotImplementedError


class Json(object):
  """Json I/O.

  -indent pretty prints it.  Is the default indent 2?  -pretty=0 can turn it
  off.

  json echo -indent 2 :var1 :var2 {
    x = 1
    d = {name: 'andy'}
  }

  json read :x < foo.tsv2
  """
  def __init__(self, mem, ex, errfmt):
    self.mem = mem
    self.ex = ex
    self.errfmt = errfmt

  def __call__(self, cmd_val):
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    #arg_r.Next()  # skip 'use'

    # TODO: GetVar() and print them

    if cmd_val.block:
      # TODO: flatten value.{Str,Obj} into a flat dict?
      namespace = self.ex.EvalBlock(cmd_val.block)

      # TODO: Use JSON library
      from pprint import pprint
      pprint(namespace, indent=2)

    return 0


class Tsv2(object):
  """TSV2 I/O.

  # Takes a block.
  tsv2 echo :var1 :var2 {
    # Does this make sense?
    x = @(a b c)
    age = @[1 2 3]
  }

  tsv2 read :x < foo.tsv2
  """
  pass
