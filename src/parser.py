import os
from lark import Lark, Transformer
from .ast import *

class HyperLangTransformer(Transformer):
    def __init__(self):
        super().__init__()

    def program(self, items):
        imports = []
        functions = []
        statements = []
        for item in items:
            if isinstance(item, Import):
                imports.append(item)
            elif isinstance(item, FunctionDef):
                functions.append(item)
            else:
                statements.append(item)
        return Program(imports, functions, statements)

    def import_stmt(self, items):
        # items: [IMPORT, LANGLE, IMPORT_PATH, RANGLE]
        path = items[2].value
        return Import(path)

    def function_def(self, items):
        # items: [pub?] name, params, ret_type, body
        if len(items) == 5:  # pub, name, params, ret_type, body
            pub = True
            name = items[1].value
            params = items[2]
            ret_type = items[3].value if items[3] is not None else None
            body = items[4]
        elif len(items) == 4:  # name, params, ret_type, body
            pub = False
            name = items[0].value
            params = items[1]
            ret_type = items[2].value if items[2] is not None else None
            body = items[3]
        else:
            pub = False
            name = items[0].value
            params = items[1] if len(items) > 1 else []
            ret_type = items[2].value if len(items) > 2 and items[2] is not None else None
            body = items[-1]
        return FunctionDef(name, params, ret_type, body, pub)

    def param_list(self, items):
        return items

    def param(self, items):
        name = items[0].value
        typ = items[1].value
        return Param(name, typ)

    def block(self, items):
        return items

    def let_stmt(self, items):
        name = items[0].value
        typ = items[1].value
        value = items[2]
        return LetStmt(name, typ, value)

    def log_stmt(self, items):
        return LogStmt(items[0])

    def unsafe_block(self, items):
        return UnsafeBlock(items[0])

    def if_stmt(self, items):
        cond = items[0]
        then_body = items[1]
        else_body = items[2] if len(items) > 2 else None
        return IfStmt(cond, then_body, else_body)

    def loop_stmt(self, items):
        return LoopStmt(items[0])

    def for_stmt(self, items):
        var = items[0].value
        start = items[1]
        end = items[2]
        inclusive = items[3] if len(items) > 3 else False
        body = items[-1]
        return ForStmt(var, start, end, inclusive, body)

    def break_stmt(self, items):
        return BreakStmt()

    def continue_stmt(self, items):
        return ContinueStmt()

    def end_stmt(self, items):
        return EndStmt(items[0])

    def expr_stmt(self, items):
        return ExprStmt(items[0])

    def expr(self, items):
        if len(items) == 1:
            return items[0]
        left = items[0]
        for op, right in zip(items[1::2], items[2::2]):
            left = BinOp(left, op.value, right)
        return left

    def term(self, items):
        if len(items) == 1:
            return items[0]
        left = items[0]
        for op, right in zip(items[1::2], items[2::2]):
            left = BinOp(left, op.value, right)
        return left

    def factor(self, items):
        atom = items[0]
        if len(items) > 1 and items[1] == '?':
            return Propagate(atom)
        return atom

    def atom(self, items):
        token = items[0]
        if isinstance(token, Expr):
            return token
        if token.type == 'INT':
            return IntLit(int(token.value))
        elif token.type == 'FLOAT':
            return FloatLit(float(token.value))
        elif token.type == 'STRING':
            return StringLit(token.value[1:-1])
        elif token.type == 'TRUE':
            return BoolLit(True)
        elif token.type == 'FALSE':
            return BoolLit(False)
        elif token.type == 'ID':
            return Var(token.value)
        elif token.type == 'CALL':
            return token
        return token

    def call(self, items):
        name = items[0].value
        args = items[1] if len(items) > 1 else []
        return Call(name, args)

    def arg_list(self, items):
        return items

    def range(self, items):
        # items: [expr_start, DOTDOT, expr_end, (EQ)]
        start = items[0]
        end = items[2]
        inclusive = len(items) > 3 and items[3] == '='
        return (start, end, inclusive)

def parse(source: str) -> Program:
    grammar_file = os.path.join(os.path.dirname(__file__), 'grammar.lark')
    with open(grammar_file, 'r', encoding='utf-8') as f:
        grammar = f.read()
    parser = Lark(grammar, parser='lalr', transformer=HyperLangTransformer())
    tree = parser.parse(source)
    return tree
