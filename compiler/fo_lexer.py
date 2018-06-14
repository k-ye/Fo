from __future__ import print_function
import re
from contextlib import contextmanager

import ply.lex as lex
from ply.lex import TOKEN


class LexingError(Exception):
  pass

keywords = {
    'break': 'BREAK',
    'chan': 'CHAN',
    'continue': 'CONTINUE',
    'else': 'ELSE',
    'fo': 'FO',
    'for': 'FOR',
    'func': 'FUNC',
    'if': 'IF',
    'return': 'RETURN',
    'select': 'SELECT',
    'type': 'TYPE',
    'var': 'VAR'
}

tokens = [
    'LARROW',
    'LPAREN',
    'RPAREN',
    'LBRACE',
    'RBRACE',
    'COMMA',
    'SEMICOLON',
    'EQUAL',
    'ADD_OP',
    'MINUS_OP',
    'TIMES_OP',
    'DIVIDE_OP',
    'MODULO_OP',
    'AND_OP',
    'OR_OP',
    'NOT_OP',
    'REL_OP',
    'INT_LIT',
    'FLOAT_LIT',
    # 'STRING',
    'ID',
    'LINE_COMMENT',
] + list(set(keywords.values()))


def FoLexer(**kwargs):

  t_LARROW = r'<-'
  t_LPAREN = r'\('
  t_RPAREN = r'\)'
  t_LBRACE = r'\{'
  t_RBRACE = r'\}'
  t_COMMA = r','
  t_SEMICOLON = r';'
  t_EQUAL = r'='
  t_ADD_OP = r'\+'
  t_MINUS_OP = r'-'
  t_TIMES_OP = r'\*'
  t_DIVIDE_OP = r'/'
  t_MODULO_OP = r'%'
  t_AND_OP = r'&&'
  t_OR_OP = r'\|\|'
  t_NOT_OP = r'!'
  t_REL_OP = r'==|!=|<=|>=|<|>'
  # t_STRING = r'"(\\.|\\\n|[^"\\\n])*"'
  t_ANY_ignore = ' \t'

  def t_FLOAT_LIT(t):
    r'(\d+\.\d*)|(\.\d+)'
    t.value = float(t.value)
    return t

  def t_INT_LIT(t):
    r'0|([1-9]\d*)'
    t.value = int(t.value)
    return t

  def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = keywords.get(t.value, 'ID')
    return t

  def t_LINE_COMMENT(t):
    r'//.*'
    pass

  # Token lexers for all states
  def t_newline(t):
    r'\n+'
    # Could match more than one '\n'
    t.lexer.lineno += len(t.value)

  def t_ANY_error(t):
    raise LexingError("Unknown token={}".format(t.value))

  def input(source_code):
    self._lexer.input(source_code)

  def token(self):
    return self._lexer.token()

  return lex.lex(**kwargs)


def fo_lexer(source_code, **kwargs):
  l = FoLexer(**kwargs)
  l.input(source_code)
  while True:
    tok = l.token()
    if not tok:
      break
    yield tok


if __name__ == '__main__':
  test_data = '''
    // a test scheme program using R1 grammar
    type B = func(a int, b int) int;

    func add(a int, b int) int {
      return a + b;
    }

    func main() {
      var a = 20.04;
      var b = 2;
      if a < b {
        a = a * b;
      }
      var f B = add;
      f(a, b);
    }
    '''
  for tok in fo_lexer(test_data):
    print(tok)
