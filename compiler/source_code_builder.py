from contextlib import contextmanager


class SourceCodeBuilder(object):

  def __init__(self):
    self.reset()

  @property
  def cur_line_length(self):
    return len(self._lines[-1])

  def reset(self):
    self._indent_lv = 0
    self._lines = []
    self.new_line()

  def new_line(self):
    self._lines.append(self._make_indent())

  def append(self, s, append_whitespace=True):
    ws = ' ' if append_whitespace else ''
    self._lines[-1] = '{}{}{}'.format(self._lines[-1], s, ws)

  def clear_indent(self):
    assert self._lines[-1] == self._make_indent()
    self._lines[-1] = ''

  @contextmanager
  def indent(self, sz=2):
    self._indent_lv += sz
    try:
      yield
    finally:
      self._indent_lv -= sz

  def build(self):
    result = '\n'.join(self._lines)
    return result

  def _make_indent(self):
    return ''.join([' '] * self._indent_lv)
