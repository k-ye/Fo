from contextlib import contextmanager


class ScopedEnvNode(object):
  '''Abstract class representing one scope in the environment
  '''

  def __init__(self):
    # scope stack is implemented as a single linked list
    self._parent = None

  @property
  def parent(self):
    return self._parent

  @parent.setter
  def parent(self, p):
    self._parent = p

  def contains(self, key):
    # returns a Boolean
    raise NotImplementedError("contains")

  def get(self, key):
    # returns the value associated with |key|
    raise NotImplementedError("get")

  def put(self, key, value):
    raise NotImplementedError("put")


class ScopedEnv(object):

  def __init__(self, top=None):
    self._top = top

  @property
  def top(self):
    return self._top

  def top_contains(self, key):
    return self._top.contains(key)

  def contains(self, key):
    return self.get_node(key) is not None

  def get(self, key):
    try:
      return self.get_node(key).get(key)
    except AttributeError:
      raise KeyError('Cannot find key: {}'.format(key))

  def get_node(self, key):
    cur = self._top
    while cur is not None:
      if cur.contains(key):
        return cur
      cur = cur.parent
    return None

  def put(self, key, value):
    # add to the top node
    self._top.put(key, value)

  def _push(self, node):
    assert isinstance(node, ScopedEnvNode)
    node.parent = self._top
    self._top = node

  def _pop(self):
    old_top = self._top.parent
    self._top = old_top

  @contextmanager
  def scope(self, node):
    self._push(node)
    try:
      yield
    finally:
      self._pop()
