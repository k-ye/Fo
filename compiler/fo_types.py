from __future__ import print_function


class NodeType(object):

  def __init__(self, t):
    self._type = t

  def __eq__(self, other):
    try:
      return self._type == other._type
    except:
      print('self: {}, other: {}'.format(str(self), str(other)))
      raise

  def __ne__(self, other):
    return self._type != other._type

  @property
  def type(self):
    return self._type

  def __str__(self):
    return str(self._type)


class TypeAlias(object):

  def __init__(self, alias, t):
    assert isinstance(alias, str)
    assert isinstance(t, NodeType)
    self._alias = alias
    self._type = t

_FUNC = 'func'
_void_type = NodeType('void')
_bool_type = NodeType('bool')
_int_type = NodeType('int64_t')
_float_type = NodeType('double')
_placeholder_type = NodeType('__placeholder__')


class TypeMismatchError(Exception):
  pass


def is_primitive_type(t):
  for it in [_void_type, _bool_type, _int_type, _float_type]:
    if t == it:
      return True
  return False


def make_type(type_name):
  if type_name == 'int':
    return _int_type
  return NodeType(type_name)


def make_func_type(param_types, ret_type):
  return NodeType((_FUNC, param_types, ret_type))


def is_func_type(t):
  try:
    return t.type[0] == _FUNC
  except:
    return False


def get_func_param_types(t):
  if not is_func_type(t):
    raise TypeMismatchError('{} is not a function type'.format(t))
  return t.type[1]


def get_func_ret_type(t):
  if not is_func_type(t):
    raise TypeMismatchError('{} is not a function type'.format(t))
  return t.type[2]


def make_placeholder_type():
  # assert False
  return _placeholder_type


def is_placeholder_type(t):
  return t == _placeholder_type


def make_void_type():
  return _void_type


def make_bool_type():
  return _bool_type


def make_int_type():
  return _int_type


def make_float_type():
  return _float_type
