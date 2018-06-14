from __future__ import print_function
import ply.yacc as yacc

import fo_lexer
from fo_ast import *
from fo_types import *

'''
Rules:

https://golang.org/ref/spec
'''


class ParsingError(Exception):
  pass


def FoParser(**kwargs):
  tokens = fo_lexer.tokens
  precedence = [
      ('left', 'EQUAL'),
      ('nonassoc', 'OR_OP'),
      ('nonassoc', 'AND_OP'),
      ('nonassoc', 'REL_OP'),
      ('left', 'ADD_OP', 'MINUS_OP'),
      ('left', 'TIMES_OP', 'DIVIDE_OP', 'MODULO_OP'),
  ]

  def p_program(p):
    '''program : program_component_list
    '''
    var_decls = []
    type_decls = []
    function_decls = []
    for c in p[1]:
      if isinstance(c, VarSpecNode):
        var_decls.append(c)
      elif isinstance(c, TypeAlias):
        type_decls.append(c)
      elif isinstance(c, FunctionDeclNode):
        function_decls.append(c)
      else:
        raise ParsingError('Unknown program object {}'.format(c))
    p[0] = ProgramNode(var_decls, type_decls, function_decls)

  def p_program_component_list(p):
    '''program_component_list : program_component
                              | program_component program_component_list
    '''
    p[0] = p[1]
    if len(p) > 2:
      p[0].extend(p[2])

  def p_program_component(p):
    '''program_component : declaration
                         | function_decl
    '''
    try:
      iter(p[1])
      p[0] = p[1]
    except TypeError:
      p[0] = [p[1]]

  def p_statement(p):
    '''statement : block
                 | declaration
                 | simple_stmt
                 | return_stmt
    '''
    # TODO: add the following stmts back
    #            | break_stmt
    #            | continue_stmt
    #            | if_stmt
    #            | for_stmt
    #            | select_stmt
    p[0] = p[1]

  def p_block(p):
    'block : LBRACE statement_list RBRACE'
    p[0] = BlockNode(p[2])

  def p_statement_list(p):
    '''statement_list : empty
                      | statement statement_list
    '''
    if len(p) > 2:
      l = None
      try:
        iter(p[1])
        # p[1] could be a list of variable declarations
        l = p[1] + p[2]
      except TypeError:
        l = [p[1]] + p[2]
      p[0] = filter(lambda s: s is not None, l)
    else:
      p[0] = []

  def p_declaration(p):
    '''declaration : var_decl
                   | type_decl
    '''
    p[0] = p[1]

  def p_var_decl(p):
    '''var_decl : VAR var_spec
                | VAR LPAREN var_spec_list RPAREN
    '''
    if len(p) > 3:
      p[0] = p[3]
    else:
      p[0] = [p[2]]

  def p_var_spec(p):
    'var_spec : identifier type maybe_initializer SEMICOLON'
    p[0] = VarSpecNode(p[1], p[2], p[3])

  def p_maybe_initializer(p):
    '''maybe_initializer : empty
                         | EQUAL expression
    '''
    if len(p) > 2:
      p[0] = p[2]
    else:
      p[0] = None

  def p_var_spec_list(p):
    '''var_spec_list : var_spec
                     | var_spec var_spec_list
    '''
    p[0] = [p[1]]
    if len(p) > 2:
      p[0].extend(p[2])

  def p_type_decl(p):
    '''type_decl : TYPE type_spec
                 | TYPE LPAREN type_spec_list RPAREN
    '''
    if len(p) > 3:
      p[0] = p[3]
    else:
      p[0] = [p[2]]

  def p_type_spec(p):
    'type_spec : ID EQUAL type SEMICOLON'
    # It is AliasDecl | TypeDef, however, we only support type alias.
    p[0] = TypeAlias(p[1], p[3])

  def p_type_spec_list(p):
    '''type_spec_list : type_spec
                      | type_spec type_spec_list
    '''
    p[0] = [p[1]]
    if len(p) > 2:
      p[0].extend(p[2])

  def p_simple_stmt(p):
    '''simple_stmt : empty SEMICOLON
                   | expression_stmt
                   | assignment
    '''
    # TODO: add 'send_stmt'
    if len(p) > 2:
      p[0] = None
    else:
      p[0] = p[1]

  def p_expression_stmt(p):
    'expression_stmt : expression SEMICOLON'
    p[0] = ExpressionStmtNode(p[1])

  def p_expression(p):
    '''expression : unary_expr
                  | expression binary_op expression
    '''
    if len(p) > 2:
      p[0] = BinaryExprNode(p[1], p[2], p[3])
    else:
      p[0] = p[1]

  def p_unary_expr(p):
    '''unary_expr : primary_expr
                  | unary_op unary_expr
    '''
    if len(p) > 2:
      p[0] = UnaryExprWithOpNode(p[1], p[2])
    else:
      p[0] = p[1]

  def p_unary_op(p):
    '''unary_op : ADD_OP
                | MINUS_OP
                | NOT_OP
                | LARROW
    '''
    p[0] = p[1]

  def p_binary_op(p):
    '''binary_op : ADD_OP
                 | MINUS_OP
                 | TIMES_OP
                 | DIVIDE_OP
                 | MODULO_OP
                 | AND_OP
                 | OR_OP
                 | REL_OP
    '''
    p[0] = p[1]

  def p_primary_expr(p):
    '''primary_expr : operand
                    | primary_expr arguments
    '''
    if len(p) > 2:
      p[0] = FunctionCallNode(p[1], p[2])
    else:
      p[0] = p[1]

  def p_operand(p):
    '''operand : literal
               | identifier
               | LPAREN expression RPAREN
    '''
    if len(p) > 2:
      p[0] = p[2]
    else:
      p[0] = p[1]

  def p_identifier(p):
    'identifier : ID'
    p[0] = IdentifierNode(p[1])

  def p_literal(p):
    '''literal : int_lit
               | float_lit
               | function_lit
    '''
    # TODO: add STRING_LIT and TUPLE_LIT
    p[0] = p[1]

  def p_int_lit(p):
    'int_lit : INT_LIT'
    p[0] = IntLitNode(p[1])

  def p_float_lit(p):
    'float_lit : FLOAT_LIT'
    p[0] = FloatLitNode(p[1])

  def p_function_decl(p):
    'function_decl : FUNC ID signature function_body'
    p[0] = FunctionDeclNode(p[2], p[3], p[4])

  def p_function_lit(p):
    'function_lit : FUNC signature function_body'
    p[0] = FunctionLitNode(p[2], p[3])

  def p_function_body(p):
    'function_body : LBRACE statement_list RBRACE'
    p[0] = p[2]

  def p_signature(p):
    '''signature : parameters
                 | parameters result_type
    '''
    if len(p) > 2:
      p[0] = (p[1], p[2])
    else:
      p[0] = (p[1], make_void_type())

  def p_result_type(p):
    'result_type : type'
    p[0] = p[1]

  def p_paramters(p):
    'parameters : LPAREN parameter_list RPAREN'
    p[0] = p[2]

  def p_parameter_list(p):
    '''parameter_list : empty
                      | parameter_decl parameter_list1
    '''
    if len(p) > 2:
      p[0] = [p[1]] + p[2]
    else:
      p[0] = []

  def p_parameter_list1(p):
    '''parameter_list1 : empty
                       | COMMA parameter_decl parameter_list1
    '''
    if len(p) > 2:
      p[0] = [p[2]] + p[3]
    else:
      p[0] = []

  def p_parameter_decl(p):
    'parameter_decl : identifier type'
    p[1].set_type(p[2])
    p[0] = (p[1], p[2])

  def p_arguments(p):
    '''arguments : LPAREN RPAREN
                 | LPAREN expression maybe_arg_list RPAREN
    '''
    if len(p) > 3:
      p[0] = [p[2]] + p[3]
    else:
      p[0] = []

  def p_maybe_arg_list(p):
    '''maybe_arg_list : empty
                      | COMMA expression maybe_arg_list
    '''
    if len(p) > 2:
      p[0] = [p[2]] + p[3]
    else:
      p[0] = []

  def p_assignment(p):
    'assignment : identifier EQUAL expression SEMICOLON'
    # TODO: replace identifier with expression. e.g. a[1] = 42
    p[0] = AssignmentNode(p[1], p[3])

  def p_return_stmt(p):
    '''return_stmt : RETURN SEMICOLON
                   | RETURN expression SEMICOLON
    '''
    ret = None
    if len(p) > 3:
      ret = p[2]
    p[0] = ReturnNode(ret)

  # def p_break_stmt(p):
  #   'break_stmt : BREAK SEMICOLON'
  #   pass

  # def p_continue_stmt(p):
  #   'continue_stmt : CONTINUE SEMICOLON'
  #   pass

  # def p_if_stmt(p):
  #   'if_stmt : IF expression block ELSE else_stmt'
  #   pass

  # def p_else_stmt(p):
  #   '''else_stmt : if_stmt
  #                | block
  #   '''
  #   pass

  # def p_for_stmt(p):
  #   'for_stmt : FOR for_clause block'
  #   pass

  # def p_for_clause(p):
  #   '''for_clause : expression
  #                 | simple_stmt SEMICOLON expression SEMICOLON simple_stmt
  #   '''
  #   pass

  def p_type(p):
    '''type : type_name
            | function_type
    '''
    p[0] = p[1]

  def p_type_name(p):
    'type_name : ID'
    p[0] = make_type(p[1])

  def p_function_type(p):
    'function_type : FUNC signature'
    params, ret_type = p[2]
    param_types = [t for _, t in params]
    p[0] = make_func_type(param_types, ret_type)

  def p_empty(p):
    'empty :'
    p[0] = None

  def p_error(p):
    raise ParsingError('Error syntax, p={}'.format(p))

  class ParserImpl(object):

    def __init__(self, yacc):
      self._yacc = yacc

    def parse(self, source, lexer=None):
      lexer = lexer or fo_lexer.FoLexer()
      ast = self._yacc.parse(input=source, lexer=lexer)
      return ast

  return ParserImpl(yacc.yacc(**kwargs))

if __name__ == '__main__':
  test_data = '''

  func makeClosure(i int) {
    return func() {
      i = i - 1;
    };
  }

  func main() {
    var a int = -2;
    var b int = -22;
    var c int = func(a int, b int) {
      return a + b * (-2);
    }(a, b);

  }
  '''

  parser = FoParser()
  ast = parser.parse(test_data)
  print(gen_source_code(ast))
