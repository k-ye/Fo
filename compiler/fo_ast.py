from contextlib import contextmanager

from fo_symbols import *
from fo_types import *
from source_code_builder import *


class AstNode(object):

  def __init__(self, symbol_chain=None):
    self._symbol_chain = symbol_chain

  @property
  def lang(self):
    return 'Fo'

  @property
  def symbol(self):
    return self._symbol_chain.symbol

  def is_symbol(self, symbol):
    return self._symbol_chain.is_symbol(symbol)

  def visit(self, visitor):
    raise NotImplementedError()


class ProgramNode(AstNode):

  def __init__(self, var_decls, type_decls, function_decls):
    self._var_decls = var_decls
    self._type_decls = type_decls
    self._function_decls = function_decls

  @property
  def var_decls(self):
    return self._var_decls

  @property
  def type_decls(self):
    return self._type_decls

  @property
  def function_decls(self):
    return self._function_decls

  def visit(self, visitor):
    return visitor.visit_program(self)


class ScopeVarsetError(Exception):
  pass


class ScopeVarset(object):

  def __init__(self):
    self._declared_vars = []
    self._captured_vars = []
    self._free_vars = []

  def _add_var(self, var_name, vars):
    if var_name in vars:
      raise ScopeVarsetError('Cannot re-add {}'.format(var_name))
    vars.append(var_name)

  @property
  def declared_vars(self):
    return self._declared_vars

  def add_declared_var(self, var_name):
    self._add_var(var_name, self._declared_vars)

  @property
  def captured_vars(self):
    return self._captured_vars

  def add_captured_var(self, var_name):
    self._add_var(var_name, self._captured_vars)

  @property
  def free_vars(self):
    return self._free_vars

  def add_free_var(self, var_name):
    self._add_var(var_name, self._free_vars)


class BlockNode(AstNode):

  def __init__(self, stmts):
    iter(stmts)
    self._stmts = stmts

    self._scope_varset = ScopeVarset()

  @property
  def stmts(self):
    return self._stmts

  def set_stmts(self, stmts):
    iter(stmts)
    self._stmts = stmts

  @property
  def scope_varset(self):
    return self._scope_varset

  def visit(self, visitor):
    return visitor.visit_block(self)


class VarSpecNode(AstNode):

  def __init__(self, var, type, init_expr=None):
    assert isinstance(var, IdentifierNode)
    assert isinstance(type, NodeType)
    assert init_expr is None or isinstance(init_expr, AstNode)
    self._var = var
    self._var._type = type
    # self._type = type
    self._init_expr = init_expr

  @property
  def var(self):
    return self._var

  @property
  def var_spec_type(self):
    return self._var.type

  @property
  def init_expr(self):
    return self._init_expr

  def visit(self, visitor):
    return visitor.visit_var_spec(self)


class AssignmentNode(AstNode):

  def __init__(self, var, expr):
    self._var = var
    self._expr = expr

  @property
  def var(self):
    return self._var

  @property
  def expr(self):
    return self._expr

  def visit(self, visitor):
    visitor.visit_assignment(self)


class ReturnNode(AstNode):

  def __init__(self, expr):
    super(ReturnNode, self).__init__()
    self._expr = expr

  @property
  def expr(self):
    return self._expr

  def visit(self, visitor):
    return visitor.visit_return(self)


class ExpressionStmtNode(AstNode):

  def __init__(self, expr):
    self._expr = expr

  @property
  def expr(self):
    return self._expr

  def visit(self, visitor):
    return visitor.visit_expression_stmt(self)


class UnaryExprWithOpNode(AstNode):

  def __init__(self, op, expr):
    self._op = op
    self._expr = expr

  @property
  def expr(self):
    return self._expr

  @property
  def op(self):
    return self._op

  @property
  def type(self):
    return self._expr.type

  def set_type(self, t):
    self._type = t

  def visit(self, visitor):
    return visitor.visit_unary_expr_with_op(self)


class BinaryExprNode(AstNode):

  def __init__(self, lhs, op, rhs):
    self._lhs = lhs
    self._rhs = rhs
    self._op = op
    self._type = None

  @property
  def lhs(self):
    return self._lhs

  @property
  def rhs(self):
    return self._rhs

  @property
  def op(self):
    return self._op

  @property
  def type(self):
    return self._type

  def set_type(self, t):
    self._type = t

  def visit(self, visitor):
    return visitor.visit_binary_expr(self)


class IntLitNode(AstNode):

  def __init__(self, val):
    self._val = val

  @property
  def val(self):
    return self._val

  @property
  def type(self):
    return make_int_type()

  def visit(self, visitor):
    return visitor.visit_int_lit(self)


class FloatLitNode(AstNode):

  def __init__(self, val):
    self._val = val

  @property
  def val(self):
    return self._val

  @property
  def type(self):
    return make_float_type()

  def visit(self, visitor):
    return visitor.visit_float_lit(self)


class IdentifierNode(AstNode):

  def __init__(self, name, type=None):
    assert isinstance(name, str)
    self._name = name
    self._type = type

  @property
  def name(self):
    return self._name

  def set_name(self, name):
    self._name = name

  @property
  def type(self):
    return self._type

  def set_type(self, t):
    self._type = t

  def visit(self, visitor):
    return visitor.visit_identifier(self)


class FunctionCallNode(AstNode):

  def __init__(self, func_expr, args):
    iter(args)
    self._func_expr = func_expr
    self._args = args

  @property
  def func_expr(self):
    return self._func_expr

  def set_func_expr(self, func_expr):
    self._func_expr = func_expr

  @property
  def args(self):
    return self._args

  def set_args(self, args):
    iter(args)
    self._args = args

  @property
  def type(self):
    # return self._type
    try:
      return get_func_ret_type(self._func_expr.type)
    except TypeMismatchError:
      return make_placeholder_type()
      # raise

  def visit(self, visitor):
    visitor.visit_function_call(self)


class FunctionDeclNode(AstNode):

  def __init__(self, name, signature, body):
    assert isinstance(name, str)
    # signature is a 2-tuple of (params, return_type)
    assert len(signature) == 2
    iter(body)

    self._name = name
    self._signature = signature
    self._body = body

    param_types = [t for _, t in self.parameters]
    self._type = make_func_type(param_types, self.return_type)

    self._scope_varset = ScopeVarset()

  @property
  def name(self):
    return self._name

  @property
  def signature(self):
    return self._signature

  @property
  def parameters(self):
    return self._signature[0]

  @property
  def parameter_names(self):
    return [p.name for p, _ in self.parameters]

  @property
  def type(self):
    return self._type

  @property
  def return_type(self):
    return self._signature[1]

  @property
  def body(self):
    return self._body

  def set_body(self, body):
    iter(body)
    self._body = body

  @property
  def scope_varset(self):
    return self._scope_varset

  def visit(self, visitor):
    return visitor.visit_function_decl(self)


# closure
class FunctionLitNode(AstNode):

  def __init__(self, signature, body):
    # signature is a 2-tuple of (params, return_type)
    assert len(signature) == 2
    iter(body)

    self._name = None
    self._signature = signature
    self._body = body

    param_types = [t for _, t in self.parameters]
    self._type = make_func_type(param_types, self.return_type)

    self._scope_varset = ScopeVarset()

  @property
  def name(self):
    return self._name

  def set_name(self, name):
    assert isinstance(name, str)
    self._name = name

  @property
  def signature(self):
    return self._signature

  @property
  def parameters(self):
    return self._signature[0]

  @property
  def parameter_names(self):
    return [p.name for p, _ in self.parameters]

  @property
  def type(self):
    return self._type

  @property
  def return_type(self):
    return self._signature[1]

  @property
  def body(self):
    return self._body

  def set_body(self, body):
    iter(body)
    self._body = body

  @property
  def scope_varset(self):
    return self._scope_varset

  def visit(self, visitor):
    return visitor.visit_function_lit(self)


class _SourceCodeVisitor(object):

  def __init__(self):
    self._builder = SourceCodeBuilder()

  def build(self):
    return self._builder.build()

  def visit_program(self, node):
    for func in node.function_decls:
      self._builder.new_line()
      func.visit(self)
      self._builder.new_line()

  def visit_var_spec(self, node):
    self._builder.append('var')
    node.var.visit(self)
    self._builder.append(node.type)
    if node.init_expr is not None:
      self._builder.append('=')
      node.init_expr.visit(self)

  def visit_block(self, node):
    self._builder.append('{')
    with self._builder.indent():
      for stmt in node.stmts:
        self._builder.new_line()
        stmt.visit(self)
    self._builder.new_line()
    self._builder.append('}')

  def visit_assignment(self, node):
    node.var.visit(self)
    self._builder.append('=')
    node.expr.visit(self)

  def visit_assign_function(self, node):
    return self.visit_assignment(node)

  def visit_return(self, node):
    self._builder.append('return')
    if node.expr is not None:
      node.expr.visit(self)

  def visit_expression_stmt(self, node):
    node.expr.visit(self)

  def visit_unary_expr_with_op(self, node):
    self._builder.append('({}'.format(node.op))
    node.expr.visit(self)
    self._builder.append(')')

  def visit_binary_expr(self, node):
    self._builder.append('(')
    node.lhs.visit(self)
    self._builder.append(node.op)
    node.rhs.visit(self)
    self._builder.append(')')

  def visit_int_lit(self, node):
    self._builder.append('{}'.format(node.val))

  def visit_float_lit(self, node):
    self._builder.append('{}'.format(node.val))

  def visit_identifier(self, node):
    self._builder.append(node.name)

  def _visit_function_common(self, node):
    self._builder.append('(')

    parameters, ret = node.signature
    first = True
    for p, t in parameters:
      if first:
        first = False
      else:
        self._builder.append(',')
      p.visit(self)
      self._builder.append(t)
    self._builder.append(') {} {{'.format(ret))
    with self._builder.indent():
      for stmt in node.body:
        self._builder.new_line()
        stmt.visit(self)
    self._builder.new_line()
    self._builder.append('}')

  def visit_function_decl(self, node):
    self._builder.append('func {}'.format(node.name))
    self._visit_function_common(node)

  def visit_function_lit(self, node):
    name = node.name or '<unknown>'
    self._builder.append('func_lit {}'.format(name))
    self._visit_function_common(node)

  def visit_function_call(self, node):
    self._builder.append('/*call*/')
    node.func_expr.visit(self)
    self._builder.append('(')
    first = True
    for a in node.args:
      if first:
        first = False
      else:
        self._builder.append(',')
      a.visit(self)
    self._builder.append(')')


def gen_source_code(ast):
  visitor = _SourceCodeVisitor()
  ast.visit(visitor)
  return visitor.build()
