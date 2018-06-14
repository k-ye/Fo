from __future__ import print_function
from contextlib import contextmanager
from copy import deepcopy

from scoped_env import *
from fo_ast import *
from fo_types import *
from fo_type_analyzer import *
import fo_parser
from source_code_builder import *

_GLOBAL_ENV = 'global_'


class _ProgramContext(object):

  def __init__(self):
    self._functions = {}
    self._var_types = {}

  @property
  def functions(self):
    return self._functions

  @property
  def var_types(self):
    return self._var_types

  def add_var_type(self, var_name, t):
    assert isinstance(t, NodeType)
    assert not is_placeholder_type(t)
    if var_name in self._var_types:
      st = self._var_types[var_name]
      assert t == st, 't={}, stored={}'.format(t, st)
    else:
      self._var_types[var_name] = t

  def __str__(self):
    builder = SourceCodeBuilder()
    with builder.indent():
      for func_name, func in self._functions.iteritems():
        builder.new_line()
        num_free_vars = len(func.scope_varset.free_vars)
        num_captured_vars = len(func.scope_varset.captured_vars)
        builder.append(
            '{}, #free {}, #captured {}'.format(
                func_name,
                num_free_vars,
                num_captured_vars))
        if num_free_vars > 0:
          with builder.indent():
            builder.new_line()
            builder.append('free variables:')
            with builder.indent():
              for var in func.scope_varset.free_vars:
                builder.new_line()
                builder.append(var)
        if num_captured_vars > 0:
          with builder.indent():
            builder.new_line()
            builder.append('variables being captured:')
            with builder.indent():
              for var in func.scope_varset.captured_vars:
                builder.new_line()
                builder.append(var)

    return builder.build()

  def __repr__(self):
    return str(self)


class _FunctionNameScopeNode(ScopedEnvNode):

  def __init__(self, name):
    super(_FunctionNameScopeNode, self).__init__()
    self._name = name
    self._counter = 0

  def alloc_name(self):
    name = '{}_c{}'.format(self._name, self._counter)
    self._counter += 1
    return name


class _AssignFunctionLitNameVisitor(object):

  def __init__(self, program_context):
    self._program_context = program_context
    self._env = ScopedEnv()

  def _make_scope_node(self, name):
    return _FunctionNameScopeNode(name)

  def visit_program(self, node):
    for f in node.function_decls:
      f.visit(self)

  def visit_var_spec(self, node):
    if node.init_expr:
      node.init_expr.visit(self)

  def visit_block(self, node):
    for stmt in node.stmts:
      stmt.visit(self)

  def visit_assignment(self, node):
    node.expr.visit(self)

  def visit_return(self, node):
    if node.expr is not None:
      node.expr.visit(self)

  def visit_expression_stmt(self, node):
    node.expr.visit(self)

  def visit_unary_expr_with_op(self, node):
    node.expr.visit(self)

  def visit_binary_expr(self, node):
    node.lhs.visit(self)
    node.rhs.visit(self)

  def visit_int_lit(self, node):
    pass

  def visit_float_lit(self, node):
    pass

  def visit_identifier(self, node):
    pass

  def visit_function_decl(self, node):
    self._program_context.functions[node.name] = node
    with self._env.scope(self._make_scope_node(node.name)):
      for stmt in node.body:
        stmt.visit(self)

  def visit_function_lit(self, node):
    node.set_name(self._env.top.alloc_name())
    self._program_context.functions[node.name] = node
    with self._env.scope(self._make_scope_node(node.name)):
      for stmt in node.body:
        stmt.visit(self)

  def visit_function_call(self, node):
    for a in node.args:
      a.visit(self)
    node.func_expr.visit(self)


def assign_function_lit_name(ast, program_context):
  visitor = _AssignFunctionLitNameVisitor(program_context)
  ast.visit(visitor)


'''Flatten pass
'''


def _is_func_node(node):
  return isinstance(node, FunctionDeclNode) or isinstance(node, FunctionLitNode)


class _FlattenScopeNode(ScopedEnvNode):

  def __init__(self, assigned_var_name, scope_name, stmts):
    super(_FlattenScopeNode, self).__init__()
    self._assigned_var_name = assigned_var_name
    self._scope_name = scope_name
    self._stmts = stmts
    self._counter = 0

  @property
  def assigned_var_name(self):
    assert self.has_assigned_var_name()
    return self._assigned_var_name

  def has_assigned_var_name(self):
    return self._assigned_var_name is not None

  def set_assigned_var_name(self, name):
    self._assigned_var_name = name

  @property
  def scope_name(self):
    assert self._scope_name is not None
    return self._scope_name

  @property
  def stmts(self):
    assert self._stmts is not None
    return self._stmts

  def alloc_assigned_var_name(self, info=None):
    info = info or 'tmp'
    result = '{}_{}_flat{}'.format(self._scope_name, info, self._counter)
    self._counter += 1
    return result


# class _AssignFunctionNode(AstNode):

#   def __init__(self, var, function):
#     super(_AssignFunctionNode, self).__init__()
#     assert isinstance(var, IdentifierNode)
#     assert isinstance(
#         function, FunctionLitNode) or isinstance(
#         function, IdentifierNode)
#     self._var = var
#     self._function = function

#   @property
#   def var(self):
#     return self._var

#   @property
#   def function(self):
#     return self._function

#   @property
#   def expr(self):
#     # adaptor method
#     return self._function

#   def visit(self, visitor):
#     return visitor.visit_assign_function(self)


class _FlattenError(Exception):
  pass


class _FlattenVisitor(object):

  def __init__(self, program_context):
    self._env = ScopedEnv()
    self._program_context = program_context

  def _copy_top_scope_node(self):
    top = self._env.top
    assert top is not None
    return self._make_scope_node(
        top._assigned_var_name, top.scope_name, top.stmts)

  def _make_scope_node(self, assigned_var_name, scope_name, stmts):
    return _FlattenScopeNode(assigned_var_name, scope_name, stmts)

  def _is_primitve_arg(self, expr):
    basic_symbols = [IdentifierNode, IntLitNode, FloatLitNode]
    for s in basic_symbols:
      if isinstance(expr, s):
        return True
    return False

  def visit_program(self, node):
    for f in node.function_decls:
      f.visit(self)

  def visit_var_spec(self, node):
    # translation:
    # var foo T = init_expr();
    # into
    # var foo T;
    # foo = init_expr();
    var = IdentifierNode(node.var.name, node.var_spec_type)
    self._env.top.stmts.append(VarSpecNode(deepcopy(var), var.type))
    if node.init_expr is not None:
      fake_assignment = AssignmentNode(deepcopy(var), node.init_expr)
      fake_assignment.visit(self)

  def visit_block(self, node):
    new_stmts = []
    new_top = self._make_scope_node(None, self._env.top.scope_name, new_stmts)
    with self._env.scope(new_top):
      for stmt in node.stmts:
        stmt.visit(self)
    node.set_stmts(new_stmts)
    self._env.top.stmts.append(node)

  def visit_assignment(self, node):
    if self._is_primitve_arg(node.expr):
      # expr = node.expr
      # try:
      #   func = self._program_context.functions[expr.name]
      #   var = IdentifierNode(node.var.name, func.type)
      #   self._env.top.stmts.append(_AssignFunctionNode(var, expr))
      # except:
      self._env.top.stmts.append(node)
    else:
      new_top = self._copy_top_scope_node()
      new_top.set_assigned_var_name(node.var.name)

      with self._env.scope(new_top):
        node.expr.visit(self)

  def visit_return(self, node):
    if node.expr is None or self._is_primitve_arg(node.expr):
      self._env.top.stmts.append(node)
    else:
      return_arg = IdentifierNode(self._env.top.scope_name + '_retarg')
      fake_var_spec = VarSpecNode(
          return_arg, make_placeholder_type(), node.expr)
      fake_var_spec.visit(self)

      self._env.top.stmts.append(ReturnNode(return_arg))

  def visit_expression_stmt(self, node):
    if self._is_primitve_arg(node.expr):
      self._env.top.stmts.append(node)
    else:
      expr_arg = IdentifierNode(self._env.top.alloc_assigned_var_name())
      fake_var_spec = VarSpecNode(expr_arg, make_placeholder_type(), node.expr)
      fake_var_spec.visit(self)

  def visit_unary_expr_with_op(self, node):
    assigned_var_name = self._env.top.assigned_var_name
    # assert assigned_var_name is not None

    unary_arg = None
    if self._is_primitve_arg(node.expr):
      unary_arg = node.expr
    else:
      unary_arg = IdentifierNode(assigned_var_name + '_unary')
      fake_var_spec = VarSpecNode(unary_arg, make_placeholder_type(), node.expr)
      fake_var_spec.visit(self)

    expr = UnaryExprWithOpNode(node.op, unary_arg)
    self._env.top.stmts.append(AssignmentNode(
        IdentifierNode(assigned_var_name), expr))

  def visit_binary_expr(self, node):
    assigned_var_name = self._env.top.assigned_var_name
    # assert assigned_var_name is not None

    lhs_arg = None
    if self._is_primitve_arg(node.lhs):
      lhs_arg = node.lhs
    else:
      lhs_arg = IdentifierNode(assigned_var_name + '_lhs')
      fake_var_spec = VarSpecNode(lhs_arg, make_placeholder_type(), node.lhs)
      fake_var_spec.visit(self)

    rhs_arg = None
    if self._is_primitve_arg(node.rhs):
      rhs_arg = node.rhs
    else:
      rhs_arg = IdentifierNode(assigned_var_name + '_rhs')
      fake_var_spec = VarSpecNode(rhs_arg, make_placeholder_type(), node.rhs)
      fake_var_spec.visit(self)

    expr = BinaryExprNode(lhs_arg, node.op, rhs_arg)
    self._env.top.stmts.append(AssignmentNode(
        IdentifierNode(assigned_var_name), expr))

  def visit_int_lit(self, node):
    raise _FlattenError('Do not flatten int_lit')

  def visit_float_lit(self, node):
    raise _FlattenError('Do not flatten float_lit')

  def visit_identifier(self, node):
    raise _FlattenError('Do not flatten identifier')

  def visit_function_decl(self, node):
    new_stmts = []
    new_top = self._make_scope_node(None, node.name, new_stmts)
    with self._env.scope(new_top):
      for stmt in node.body:
        stmt.visit(self)
    # assert self._node_factory.assigned_var_name is None
    node.set_body(new_stmts)

    top_scope = self._env.top

  def visit_function_lit(self, node):
    new_stmts = []
    new_top = self._make_scope_node(None, node.name, new_stmts)

    with self._env.scope(new_top):
      for stmt in node.body:
        stmt.visit(self)
    node.set_body(new_stmts)

    assigned_var = IdentifierNode(self._env.top.assigned_var_name, node.type)
    self._env.top.stmts.append(AssignmentNode(
        assigned_var, node))
    # self._env.top.stmts.append(_AssignFunctionNode(assigned_var, node))

  def visit_function_call(self, node):
    new_args = []
    for a in node.args:
      if self._is_primitve_arg(a):
        new_args.append(a)
      else:
        new_arg = IdentifierNode(self._env.top.alloc_assigned_var_name('arg'))
        fake_var_spec = VarSpecNode(new_arg, make_placeholder_type(), a)
        fake_var_spec.visit(self)
        new_args.append(new_arg)

    if self._is_primitve_arg(node.func_expr):
      func_arg = node.func_expr
      assert isinstance(func_arg, IdentifierNode)
      # try:
      #   f = self._program_context.functions[func_arg.name]
      #   func_arg = f
      # except KeyError:
      #   print(
      #       'Except in {}, functions: {}'.format(
      #           func_arg.name,
      #           self._program_context.functions.keys()))
      #   pass
    else:
      func_arg = IdentifierNode(
          self._env.top.alloc_assigned_var_name('func_call'))
      fake_var_spec = VarSpecNode(
          func_arg, make_placeholder_type(), node.func_expr)
      fake_var_spec.visit(self)

    node.set_args(new_args)
    node.set_func_expr(func_arg)
    assigned_var_name = self._env.top.assigned_var_name
    # assert assigned_var_name is not None
    self._env.top.stmts.append(AssignmentNode(
        IdentifierNode(assigned_var_name), node))


def flatten(ast, program_context):
  visitor = _FlattenVisitor(program_context)
  ast.visit(visitor)
  return ast

'''Uniquify
'''


class _UniquifyScopeEnvNode(ScopedEnvNode):

  def __init__(self, global_key_count):
    super(_UniquifyScopeEnvNode, self).__init__()
    self._global_key_count = global_key_count
    self._local_kv = {}

  def contains(self, key):
    return key in self._local_kv

  def get(self, key):
    return self._local_kv[key]

  def put(self, key, value):
    assert key not in self._local_kv
    self._local_kv[key] = value

  def put_var(self, key):
    count = self._global_key_count.get(key, 0)
    self._global_key_count[key] = count + 1
    value = '{}_uniq{}'.format(key, count)
    self.put(key, value)


class _UniquifyVisitor(object):

  def __init__(self, program_context):
    self._global_key_count = {}
    self._env = ScopedEnv(self._make_scope_node())
    for func_name in program_context.functions:
      # |func_name| is mapped to its own name.
      self._env.top.put(func_name, func_name)

  def _make_scope_node(self):
    return _UniquifyScopeEnvNode(self._global_key_count)

  def visit_program(self, node):
    for f in node.function_decls:
      f.visit(self)

  def visit_var_spec(self, node):
    if node.init_expr:
      node.init_expr.visit(self)
    self._env.top.put_var(node.var.name)
    node.var.visit(self)

  def visit_block(self, node):
    with self._env.scope(self._make_scope_node()):
      for stmt in node.stmts:
        stmt.visit(self)

  def visit_assignment(self, node):
    node.expr.visit(self)
    node.var.visit(self)

  def visit_return(self, node):
    if node.expr is not None:
      node.expr.visit(self)

  def visit_expression_stmt(self, node):
    node.expr.visit(self)

  def visit_unary_expr_with_op(self, node):
    node.expr.visit(self)

  def visit_binary_expr(self, node):
    node.lhs.visit(self)
    node.rhs.visit(self)

  def visit_int_lit(self, node):
    pass

  def visit_float_lit(self, node):
    pass

  def visit_identifier(self, node):
    node.set_name(self._env.get(node.name))

  def visit_function_decl(self, node):
    with self._env.scope(self._make_scope_node()):
      for p, t in node.parameters:
        self._env.top.put_var(p.name)
        p.visit(self)

      for stmt in node.body:
        stmt.visit(self)

  def visit_function_lit(self, node):
    with self._env.scope(self._make_scope_node()):
      for p, t in node.parameters:
        self._env.top.put_var(p.name)
        p.visit(self)

      for stmt in node.body:
        stmt.visit(self)

  def visit_function_call(self, node):
    for a in node.args:
      a.visit(self)
    node.func_expr.visit(self)


def uniquify_vars(ast, program_context):
  visitor = _UniquifyVisitor(program_context)
  ast.visit(visitor)


'''Reveal free variables
'''


class _RevealVarsScopeNode(ScopedEnvNode):

  def __init__(self, func_name, node):
    super(_RevealVarsScopeNode, self).__init__()
    assert _is_func_node(node) or isinstance(node, BlockNode)
    self._func_name = func_name
    self._ast_node = node
    self._var_names = set()

  @property
  def func_name(self):
    return self._func_name

  @property
  def ast_node(self):
    return self._ast_node

  def contains(self, key):
    # returns a Boolean
    return key in self._var_names

  def put(self, key, value):
    # |value| is not used
    assert key not in self._var_names
    self._var_names.add(key)


class _RevealVarsVisitor(object):

  def __init__(self, program_context):
    self._program_context = program_context
    self._env = ScopedEnv()

  def visit_program(self, node):
    for f in node.function_decls:
      f.visit(self)

  def visit_var_spec(self, node):
    if node.init_expr:
      node.init_expr.visit(self)
    self._env.put(node.var.name, None)
    self._env.top.ast_node.scope_varset.add_declared_var(node.var.name)
    node.var.visit(self)

  def visit_block(self, node):
    scope = _RevealVarsScopeNode(self._env.top.func_name, node)
    with self._env.scope(scope):
      for stmt in node.stmts:
        stmt.visit(self)

  def visit_assignment(self, node):
    node.expr.visit(self)
    node.var.visit(self)

  # def visit_assign_function(self, node):
  #   return self.visit_assignment(node)

  def visit_return(self, node):
    if node.expr is not None:
      node.expr.visit(self)

  def visit_expression_stmt(self, node):
    node.expr.visit(self)

  def visit_unary_expr_with_op(self, node):
    node.expr.visit(self)

  def visit_binary_expr(self, node):
    node.lhs.visit(self)
    node.rhs.visit(self)

  def visit_int_lit(self, node):
    pass

  def visit_float_lit(self, node):
    pass

  def visit_identifier(self, node):
    name = node.name
    if name in self._program_context.functions:
      return

    in_func_name = self._env.top.func_name
    if in_func_name == self._env.get_node(name).func_name:
      return

    try:
      scope = self._env.top
      while scope is not None:
        ast_node = scope.ast_node
        if scope.contains(name):
          ast_node.scope_varset.add_captured_var(name)
          if isinstance(ast_node, BlockNode):
            assert name in ast_node.scope_varset.declared_vars
          else:
            assert name in ast_node.scope_varset.declared_vars or name in ast_node.parameter_names
          break
        elif _is_func_node(ast_node):
          ast_node.scope_varset.add_free_var(name)
        scope = scope.parent
      assert scope is not None
      assert scope.func_name != in_func_name
    except ScopeVarsetError:
      pass

  def visit_function_decl(self, node):
    # self._node_factory.set_node_name(node.name)
    with self._env.scope(_RevealVarsScopeNode(node.name, node)):
      for p, t in node.parameters:
        self._env.put(p.name, None)
        p.visit(self)

      for stmt in node.body:
        stmt.visit(self)

  def visit_function_lit(self, node):
    # self._node_factory.set_node_name(node.name)
    with self._env.scope(_RevealVarsScopeNode(node.name, node)):
      for p, t in node.parameters:
        self._env.put(p.name, None)
        p.visit(self)

      for stmt in node.body:
        stmt.visit(self)

  def visit_function_call(self, node):
    for a in node.args:
      a.visit(self)
    node.func_expr.visit(self)


def reveal_vars(ast, program_context):
  visitor = _RevealVarsVisitor(program_context)
  ast.visit(visitor)

'''
'''


class _FixAstScopeNode(ScopedEnvNode):

  def __init__(self, func_name, node):
    super(_RevealVarsScopeNode, self).__init__()
    assert _is_func_node(node) or isinstance(node, BlockNode)
    self._func_name = func_name
    self._ast_node = node
    self._var_names = set()

  @property
  def func_name(self):
    return self._func_name

  @property
  def ast_node(self):
    return self._ast_node

  def contains(self, key):
    # returns a Boolean
    return key in self._var_names

  def put(self, key, value):
    # |value| is not used
    assert key not in self._var_names
    self._var_names.add(key)


class _FixAstVisitor(object):

  def __init__(self):
    pass

  def visit_program(self, node):
    for f in node.function_decls:
      f.visit(self)

  def visit_var_spec(self, node):
    if node.init_expr:
      node.init_expr.visit(self)
    node.var.visit(self)

  def visit_block(self, node):
    for stmt in node.stmts:
      stmt.visit(self)

  def visit_assignment(self, node):
    node.expr.visit(self)
    node.var.visit(self)

  # def visit_assign_function(self, node):
  #   return self.visit_assignment(node)

  def visit_return(self, node):
    if node.expr is not None:
      node.expr.visit(self)

  def visit_expression_stmt(self, node):
    node.expr.visit(self)

  def visit_unary_expr_with_op(self, node):
    node.expr.visit(self)

  def visit_binary_expr(self, node):
    node.lhs.visit(self)
    node.rhs.visit(self)

  def visit_int_lit(self, node):
    pass

  def visit_float_lit(self, node):
    pass

  def visit_identifier(self, node):
    pass

  def _visit_function(self, node):
    new_body = []
    for p, t in node.parameters:
      assert isinstance(p, IdentifierNode)
      if p.name in node.scope_varset.captured_vars:
        captured_var = IdentifierNode(p.name, t)
        p.set_name(captured_var.name + '_raw')
        new_body.append(VarSpecNode(captured_var, t))
        new_body.append(AssignmentNode(captured_var, IdentifierNode(p.name, t)))

        p.visit(self)
    for stmt in node.body:
      stmt.visit(self)
    new_body += node.body
    node.set_body(new_body)

  def visit_function_decl(self, node):
    return self._visit_function(node)

  def visit_function_lit(self, node):
    return self._visit_function(node)

  def visit_function_call(self, node):
    for a in node.args:
      a.visit(self)
    node.func_expr.visit(self)


def fix_ast(ast):
  visitor = _FixAstVisitor()
  ast.visit(visitor)


'''Check/Assign type pass
'''


# class _CheckOrAssignTypeScopeEnvNode(ScopedEnvNode):

#   def __init__(self):
#     super(_CheckOrAssignTypeScopeEnvNode, self).__init__()
#     self._local_var_types = {}

#   def contains(self, key):
#     return key in self._local_var_types

#   def get(self, key):
#     return self._local_var_types[key]

#   def put(self, key, t):
#     # assert key not in self._local_kv
#     assert not is_placeholder_type(t)
#     if key not in self._local_var_types:
#       self._local_var_types[key] = t
#     else:
#       assert t == self._local_var_types[key]

def _is_valid_type(t):
  return t is not None and not is_placeholder_type(t)


class _IterAssignTypeVisitor(object):

  def __init__(self, program_context):
    self._program_context = program_context
    self._num_untyped = 0

  @property
  def num_untyped(self):
    return self._num_untyped

  def visit_program(self, node):
    for f in node.function_decls:
      f.visit(self)

  def visit_var_spec(self, node):
    var = node.var
    # if self._check_mode:
    #   assert self._var_has_valid_type(var)
    #   if node.init_expr:
    #     assert var.type == node.init_expr.type
    #   return
    if node.init_expr is not None:
      node.init_expr.visit(self)
      if _is_valid_type(node.init_expr.type):
        self._program_context.add_var_type(var.name, node.init_expr.type)
      # else:
      #   self._num_untyped += 1
    var.visit(self)
    # if not _is_valid_type(var.type):
    #   self._num_untyped += 1

  def visit_block(self, node):
    for stmt in node.stmts:
      stmt.visit(self)

  def visit_assignment(self, node):
    var = node.var
    node.expr.visit(self)
    if _is_valid_type(node.expr.type):
      self._program_context.add_var_type(var.name, node.expr.type)
    # else:
    #   self._num_untyped += 1
    var.visit(self)
    # if not _is_valid_type(var.type):
    #   self._num_untyped += 1

  def visit_return(self, node):
    if node.expr is not None:
      node.expr.visit(self)

  def visit_expression_stmt(self, node):
    node.expr.visit(self)

  def visit_unary_expr_with_op(self, node):
    node.expr.visit(self)
    if _is_valid_type(node.expr.type):
      node.set_type(node.expr.type)
    else:
      self._num_untyped += 1

  def visit_binary_expr(self, node):
    lhs, rhs = node.lhs, node.rhs
    lhs.visit(self)
    rhs.visit(self)
    if _is_valid_type(lhs.type) and _is_valid_type(rhs.type):
      assert lhs.type == rhs.type
      node.set_type(lhs.type)
    else:
      self._num_untyped += 1

  def visit_int_lit(self, node):
    pass

  def visit_float_lit(self, node):
    pass

  def visit_identifier(self, node):
    # node.set_name(self._env.get(node.name))
    stored_type = self._program_context.var_types.get(node.name, None)
    var_type = node.type
    if _is_valid_type(var_type):
      self._program_context.add_var_type(node.name, var_type)
      if stored_type is not None:
        assert stored_type == var_type
    else:
      if stored_type is not None:
        node.set_type(stored_type)
      else:
        self._num_untyped += 1

  def visit_function_decl(self, node):
    for p, t in node.parameters:
      self._program_context.add_var_type(p.name, t)
      p.visit(self)

    for stmt in node.body:
      stmt.visit(self)

  def visit_function_lit(self, node):
    for p, t in node.parameters:
      self._program_context.add_var_type(p.name, t)
      p.visit(self)

    for stmt in node.body:
      stmt.visit(self)

  def visit_function_call(self, node):
    for a in node.args:
      a.visit(self)
    # if not isinstance(node.func_expr, FunctionDeclNode):
    # assert node.func_expr.name in self._program_context.functions
    func_expr = node.func_expr
    assert isinstance(node.func_expr, IdentifierNode)
    try:
      f = self._program_context.functions[func_expr.name]
      func_expr.set_type(f.type)
      # func_expr.visit(self)
    except KeyError:
      pass
    func_expr.visit(self)


def assign_check_types(ast, program_context):
  program_context._var_types = {}
  done = False
  while not done:
    visitor = _IterAssignTypeVisitor(program_context)
    ast.visit(visitor)
    done = visitor.num_untyped == 0
    print(visitor.num_untyped)


'''
'''

_GC_HEADER_T = 'gc_header_t*'


class _CodeGenScopeNode(ScopedEnvNode):

  def __init__(self, node):
    super(_CodeGenScopeNode, self).__init__()
    assert _is_func_node(node) or isinstance(node, BlockNode)
    self._ast_node = node

  @property
  def ast_node(self):
    return self._ast_node


def _strfy_type(t):
  if is_primitive_type(t):
    return str(t)
  return _GC_HEADER_T


def _strfy_to_c_func_ptr_type(t):
  assert is_func_type(t)
  result = _strfy_type(get_func_ret_type(t))
  result += '(*)(' + _GC_HEADER_T
  for pt in get_func_param_types(t):
    result += ', ' + _strfy_type(pt)
  result += ')'
  return result


class _CodeGenVisitor(object):

  def __init__(self, program_context):
    self._program_context = program_context
    self._env = ScopedEnv()
    self._builder = SourceCodeBuilder()

  def build(self):
    return self._builder.build()

  def visit_program(self, node):
    headers = [
        '#include "runtime/base.h"',
        '#include "runtime/gc.h"',
        '#include "runtime/gc_header.h"',
        '#include "runtime/memory.h"',
        '#include "runtime/tuple.h"',
    ]
    for h in headers:
      self._builder.append(h)
      self._builder.new_line()

    for func_name, func_node in self._program_context.functions.iteritems():
      self._builder.new_line()
      self._define_function(func_node)

  def _declare_function(self, node):
    # if we define all the functions in topological sorted order, then this
    # is no longer necessary.
    assert _is_func_node(node)
    self._builder.new_line()
    self._builder.append(_strfy_type(node.return_type))
    self._builder.append(node.name)
    self._builder.append('(')

  def _define_function(self, node):
    assert _is_func_node(node)
    self._builder.new_line()
    self._builder.append(_strfy_type(node.return_type))
    self._builder.append(node.name)
    self._builder.append('(')

    # if isinstance(node, FunctionLitNode):
    self._builder.append(_GC_HEADER_T + ' context_tuple')
    # is_first_param = False

    for p, t in node.parameters:
      # if is_first_param:
      #   is_first_param = False
      # else:
      self._builder.append(',')
      self._builder.append('{} {}'.format(_strfy_type(t), p.name))
    self._builder.append(')')
    self._builder.append('{')
    with self._builder.indent():
      with self._env.scope(_CodeGenScopeNode(node)):
        for i, var_name in enumerate(node.scope_varset.free_vars):
          self._builder.new_line()
          # context_tuple[0] stores the function pointer
          self._builder.append(
              '{0} {1} = ({0})get_tuple_at(context_tuple, {2});'.format(
                  _GC_HEADER_T, var_name, i + 1))
        for stmt in node.body:
          self._builder.new_line()
          stmt.visit(self)
    self._builder.new_line()
    self._builder.append('}')

  def _get_id_cexpr(self, name):
    scope_varset = self._env.top.ast_node.scope_varset
    if name in scope_varset.captured_vars or name in scope_varset.free_vars:
      return '*GC_TO_OBJ(FAKE_TYPE, {})'.format(name)
    return name

  def visit_var_spec(self, node):
    name = node.var.name
    if name in self._env.top.ast_node.scope_varset.captured_vars:
      l = '{} {} = gc_alloc_trivial(sizeof(val_t), get_trivial_obj_operators());'.format(
          _GC_HEADER_T, name)
      self._builder.append(l)
    else:
      self._builder.append(
          '{0} {1} = ({0})0;'.format(_strfy_type(node.var_spec_type), node.var.name))
    assert node.init_expr is None
    # if node.init_expr:
    #   self._builder.append('=')
    #   node.init_expr.visit(self)
    # self._builder.append(';')

  def visit_block(self, node):
    self._builder.append('{')
    with self._builder.indent():
      with self._env.scope(_CodeGenScopeNode(node)):
        for stmt in node.stmts:
          self._builder.new_line()
          stmt.visit(self)
    self._builder.new_line()
    self._builder.append('}')

  def visit_assignment(self, node):
    # name = node.var.name
    # if name in self._env.top.ast_node.scope_varset.captured_vars:
    #   self._builder.append('*GC_TO_OBJ(FAKE_TYPE, {}) ='.format(name))
    # else:
    #   self._builder.append(name + ' =')
    def is_func_ref():
      e = node.expr
      if isinstance(e, FunctionLitNode):
        return True
      if isinstance(e, IdentifierNode):
        if e.name in self._program_context.functions:
          return True
      return False

    if is_func_ref():
      self.visit_assign_function(node)
      return
    node.var.visit(self)
    self._builder.append('=')
    node.expr.visit(self)
    self._builder.append(';')

  def visit_assign_function(self, node):

    var_cexpr = self._get_id_cexpr(node.var.name)
    # node.var.visit(self)
    self._builder.append(var_cexpr + ' =')
    func = node.expr
    if isinstance(func, IdentifierNode):
      func = self._program_context.functions[func.name]
    free_vars = func.scope_varset.free_vars
    num_slots = 1 + len(free_vars)
    # TODO: consider the case where |node.var| is captured
    self._builder.append('alloc_tuple({});'.format(num_slots))
    self._builder.append(
        'set_tuple_at({}, 0, (val_t){}, false);'.format(
            var_cexpr, func.name))

    self._builder.new_line()
    for i, fvar in enumerate(free_vars):
      self._builder.new_line()
      self._builder.append(
          'set_tuple_at({}, {}, (val_t){}, /*needs_gc=*/false);'.format(
              var_cexpr, i + 1, fvar))
    # return self.visit_assignment(node)

  def visit_return(self, node):
    self._builder.append('return')
    if node.expr is not None:
      node.expr.visit(self)
    self._builder.append(';')

  def visit_expression_stmt(self, node):
    self._builder.append('(')
    node.expr.visit(self)
    self._builder.append(')')

  def visit_unary_expr_with_op(self, node):
    self._builder.append(node.op + ' (')
    node.expr.visit(self)
    self._builder.append(')')

  def visit_binary_expr(self, node):
    self._builder.append('(')
    node.lhs.visit(self)
    self._builder.append(') {} ('.format(node.op))
    node.rhs.visit(self)
    self._builder.append(')')

  def visit_int_lit(self, node):
    self._builder.append(str(node.val))

  def visit_float_lit(self, node):
    self._builder.append(str(node.val))

  def visit_identifier(self, node):
    name = node.name
    self._builder.append(self._get_id_cexpr(name))

  def visit_function_decl(self, node):
    raise NotImplementedError(node.name)

  def visit_function_lit(self, node):
    # return self._visit_function(node)
    pass

  def visit_function_call(self, node):
    func_expr = node.func_expr
    is_plain_function = False
    try:
      is_plain_function = isinstance(
          self._program_context.functions[
              func_expr.name], FunctionDeclNode)
    except:
      is_plain_function = False

    if is_plain_function:
      self._builder.append(func_expr.name)
    else:
      self._builder.append(
          '(({})get_tuple_at('.format(
              _strfy_to_c_func_ptr_type(
                  func_expr.type)))
      func_expr.visit(self)
      self._builder.append(', 0))')

    self._builder.append('(')
    if is_plain_function:
      self._builder.append('NULL')
    else:
      func_expr.visit(self)

    for a in node.args:
      self._builder.append(',')
      a.visit(self)
    self._builder.append(');')


def code_gen(ast, program_context):
  visitor = _CodeGenVisitor(program_context)
  ast.visit(visitor)
  return visitor.build()

if __name__ == '__main__':
  test_data = '''
  func makeClosure(i int) func() {
    return func() func() {
      {
        var j int = 2;
        return func() {
          i = i + j;
        };
      }
    }();
  }

  func main() {
    var i int = -2;
    var j int = -22;
    var k int = func(i int, j int) int {
      return i + j * -2;
    }(i, j);

    var f func() = makeClosure(i);
    f();
  }
  '''

  # test_data = '''
  # func main() {
  #   var k int = func(i int, j int) int {
  #     return i + j * -2;
  #   }(2, 22);
  #   func() { return 42; }();
  # }
  # '''

  parser = fo_parser.FoParser()
  ast = parser.parse(test_data)

  program_context = _ProgramContext()
  assign_function_lit_name(ast, program_context)
  # print(program_context.functions.keys())
  # fix_function_call(ast, program_context)
  flatten(ast, program_context)
  uniquify_vars(ast, program_context)
  reveal_vars(ast, program_context)
  fix_ast(ast)
  assign_check_types(ast, program_context)

  # print(program_context)
  # print()
  # print(gen_source_code(ast))

  print('/********** Fo Generated C Code **********/')
  print(code_gen(ast, program_context))
