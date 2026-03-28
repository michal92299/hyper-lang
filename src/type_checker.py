# hyperlang/type_checker.py

from typing import Dict, List, Optional
from .ast import *


class TypeError(Exception):
    pass


class TypeChecker:
    def __init__(self):
        self.symbols: Dict[str, str] = {}            # zmienne -> typ
        self.functions: Dict[str, FunctionDef] = {}  # funkcje zdefiniowane w programie
        self.current_func: Optional[FunctionDef] = None
        self.errors: List[str] = []

    def check(self, node):
        if isinstance(node, Program):
            for func in node.functions:
                self.functions[func.name] = func
            for imp in node.imports:
                pass  # importy nie są sprawdzane typowo
            for func in node.functions:
                self.visit_function(func)
            for stmt in node.statements:
                self.visit_statement(stmt)
        elif isinstance(node, FunctionDef):
            self.visit_function(node)
        elif isinstance(node, Statement):
            self.visit_statement(node)
        else:
            raise TypeError(f"Unknown node type: {type(node)}")

        if self.errors:
            raise TypeError("\n".join(self.errors))

    def error(self, msg: str, node=None):
        loc = f" at {node}" if node else ""
        self.errors.append(f"Type error{loc}: {msg}")

    def visit_function(self, func: FunctionDef):
        old_syms = self.symbols.copy()
        self.symbols = {}
        for param in func.params:
            self.symbols[param.name] = param.type
        self.current_func = func
        for stmt in func.body:
            self.visit_statement(stmt)
        self.current_func = None
        self.symbols = old_syms

    def visit_statement(self, stmt):
        if isinstance(stmt, LetStmt):
            self.visit_let(stmt)
        elif isinstance(stmt, LogStmt):
            self.visit_log(stmt)
        elif isinstance(stmt, UnsafeBlock):
            self.visit_unsafe(stmt)
        elif isinstance(stmt, IfStmt):
            self.visit_if(stmt)
        elif isinstance(stmt, LoopStmt):
            self.visit_loop(stmt)
        elif isinstance(stmt, ForStmt):
            self.visit_for(stmt)
        elif isinstance(stmt, BreakStmt):
            pass
        elif isinstance(stmt, ContinueStmt):
            pass
        elif isinstance(stmt, EndStmt):
            self.visit_end(stmt)
        elif isinstance(stmt, ExprStmt):
            self.visit_expr(stmt.expr)
        else:
            self.error(f"Unknown statement: {type(stmt)}", stmt)

    def visit_let(self, stmt: LetStmt):
        val_type = self.visit_expr(stmt.value)
        if val_type is None:
            self.error(f"Cannot infer type for {stmt.name}", stmt)
            return
        if stmt.type != val_type:
            self.error(f"Type mismatch for {stmt.name}: expected {stmt.type}, got {val_type}", stmt)
        self.symbols[stmt.name] = stmt.type

    def visit_log(self, stmt: LogStmt):
        self.visit_expr(stmt.value)   # log przyjmuje dowolny typ

    def visit_unsafe(self, stmt: UnsafeBlock):
        for s in stmt.body:
            self.visit_statement(s)

    def visit_if(self, stmt: IfStmt):
        cond_type = self.visit_expr(stmt.cond)
        if cond_type != "bool":
            self.error(f"If condition must be bool, got {cond_type}", stmt.cond)
        for s in stmt.then_body:
            self.visit_statement(s)
        if stmt.else_body:
            for s in stmt.else_body:
                self.visit_statement(s)

    def visit_loop(self, stmt: LoopStmt):
        for s in stmt.body:
            self.visit_statement(s)

    def visit_for(self, stmt: ForStmt):
        start_type = self.visit_expr(stmt.start)
        end_type = self.visit_expr(stmt.end)
        if start_type != "i32" or end_type != "i32":
            self.error(f"For loop bounds must be i32, got {start_type} and {end_type}", stmt)
        old = self.symbols.get(stmt.var)
        self.symbols[stmt.var] = "i32"
        for s in stmt.body:
            self.visit_statement(s)
        if old is None:
            del self.symbols[stmt.var]
        else:
            self.symbols[stmt.var] = old

    def visit_end(self, stmt: EndStmt):
        val_type = self.visit_expr(stmt.value)
        if self.current_func:
            expected = self.current_func.return_type
            if expected is None:
                if val_type is not None:
                    self.error(f"Function {self.current_func.name} does not declare return type, "
                               f"but returns {val_type}", stmt)
            elif expected == "void":
                self.error(f"Function {self.current_func.name} declared void, but returns a value", stmt)
            elif val_type != expected:
                self.error(f"Return type mismatch: expected {expected}, got {val_type}", stmt)

    def visit_expr(self, expr) -> Optional[str]:
        if isinstance(expr, BinOp):
            return self.visit_binop(expr)
        if isinstance(expr, UnaryOp):
            return self.visit_unary(expr)
        if isinstance(expr, IntLit):
            return "i32"
        if isinstance(expr, FloatLit):
            return "f64"
        if isinstance(expr, StringLit):
            return "str"
        if isinstance(expr, BoolLit):
            return "bool"
        if isinstance(expr, Var):
            typ = self.symbols.get(expr.name)
            if typ is None:
                self.error(f"Variable '{expr.name}' not defined", expr)
                return None
            return typ
        if isinstance(expr, Call):
            return self.visit_call(expr)
        if isinstance(expr, Propagate):
            return self.visit_expr(expr.expr)
        self.error(f"Unknown expression type: {type(expr)}", expr)
        return None

    def visit_binop(self, binop: BinOp) -> Optional[str]:
        left = self.visit_expr(binop.left)
        right = self.visit_expr(binop.right)
        if left is None or right is None:
            return None

        op = binop.op
        if op in ('+', '-', '*', '/'):
            if left == "i32" and right == "i32":
                return "i32"
            if left == "f64" and right == "f64":
                return "f64"
            if left == "str" and op == '+' and right == "str":
                return "str"
            self.error(f"Invalid operand types for {op}: {left} and {right}", binop)
            return None
        if op in ('==', '!=', '<', '>', '<=', '>='):
            if left != right:
                self.error(f"Cannot compare {left} and {right}", binop)
                return None
            return "bool"
        if op in ('&&', '||'):
            if left != "bool" or right != "bool":
                self.error(f"Logical operator {op} requires bool operands", binop)
                return None
            return "bool"
        self.error(f"Unknown binary operator: {op}", binop)
        return None

    def visit_unary(self, unary: UnaryOp) -> Optional[str]:
        operand = self.visit_expr(unary.operand)
        if operand is None:
            return None
        op = unary.op
        if op == '-':
            if operand in ("i32", "f64"):
                return operand
            self.error(f"Unary minus not allowed on {operand}", unary)
            return None
        if op == '!':
            if operand == "bool":
                return "bool"
            self.error(f"Logical not requires bool, got {operand}", unary)
            return None
        self.error(f"Unknown unary operator: {op}", unary)
        return None

    def visit_call(self, call: Call) -> Optional[str]:
        func = self.functions.get(call.func)
        if func is None:
            self.error(f"Function '{call.func}' not defined", call)
            return None
        if len(call.args) != len(func.params):
            self.error(f"Function '{call.func}' expects {len(func.params)} arguments, "
                       f"got {len(call.args)}", call)
            return None
        for i, arg in enumerate(call.args):
            arg_type = self.visit_expr(arg)
            expected = func.params[i].type
            if arg_type != expected:
                self.error(f"Argument {i+1} of '{call.func}' expected {expected}, "
                           f"got {arg_type}", call)
                return None
        return func.return_type if func.return_type else "void"
