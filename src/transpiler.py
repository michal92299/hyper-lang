# hyperlang/transpiler.py

from .ast import *
from .extern import ExternManager


class Transpiler:
    def __init__(self):
        self.indent = 0
        self.code = []
        self.unsafe = False
        self.extern_manager = ExternManager()   # do generowania importów zewnętrznych

    def emit(self, line: str):
        self.code.append(" " * self.indent + line)

    def transpile(self, node: Node):
        if isinstance(node, Program):
            self.emit("# Generated from Hyper Lang")
            self.emit("import sys")
            self.emit("import numba as nb")
            # Dodajemy importy z extern (jeśli jakieś są)
            extern_imports = self.extern_manager.generate_imports()
            for line in extern_imports:
                self.emit(line)

            # Importy z kodu źródłowego
            for imp in node.imports:
                self.visit_import(imp)

            # Funkcje
            for func in node.functions:
                self.visit_function(func)

            # Instrukcje globalne (poza funkcjami)
            for stmt in node.statements:
                self.visit_statement(stmt)
        else:
            raise ValueError(f"Unknown node: {type(node)}")

    def visit_import(self, imp: Import):
        """Generuje kod importu dla różnych ekosystemów."""
        path = imp.path
        if path.startswith("python:"):
            module = path.split(":", 1)[1]
            self.emit(f"import {module}")
        elif path.startswith("pyhy:"):
            # Tutaj można dodać mechanizm ładowania modułów z ekosystemu pyhy
            # Na razie generujemy komentarz
            self.emit(f"# pyhy import: {path}")
        else:
            self.emit(f"# unknown import: {path}")

    def visit_function(self, func: FunctionDef):
        """Generuje definicję funkcji z dekoratorem @nb.jit."""
        # Dekorator numba – pomijamy w bloku unsafe (można dodać opcję)
        if not self.unsafe:
            self.emit("@nb.jit(nopython=True)")

        params = ", ".join(p.name for p in func.params)
        ret_annotation = f" -> {self._py_type(func.return_type)}" if func.return_type else ""
        self.emit(f"def {func.name}({params}){ret_annotation}:")
        self.indent += 1

        # Adnotacje typów parametrów w komentarzach (dla czytelności)
        for p in func.params:
            self.emit(f"# type: {p.name}: {self._py_type(p.type)}")

        for stmt in func.body:
            self.visit_statement(stmt)

        # Jeśli funkcja nie ma żadnego `end`, domyślnie zwracamy None
        if not any(isinstance(s, EndStmt) for s in func.body):
            self.emit("return None")

        self.indent -= 1
        self.emit("")

    def _py_type(self, hyper_type: str) -> str:
        mapping = {
            "i32": "int",
            "f64": "float",
            "str": "str",
            "bool": "bool",
            "void": "None"
        }
        return mapping.get(hyper_type, hyper_type)

    def visit_statement(self, stmt: Statement):
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
            self.emit("break")
        elif isinstance(stmt, ContinueStmt):
            self.emit("continue")
        elif isinstance(stmt, EndStmt):
            self.visit_end(stmt)
        elif isinstance(stmt, ExprStmt):
            self.emit(self._expr_to_str(stmt.expr))
        else:
            raise ValueError(f"Unknown statement: {type(stmt)}")

    def visit_let(self, stmt: LetStmt):
        val = self._expr_to_str(stmt.value)
        self.emit(f"{stmt.name} = {val}  # type: {self._py_type(stmt.type)}")

    def visit_log(self, stmt: LogStmt):
        val = self._expr_to_str(stmt.value)
        self.emit(f"print({val})")

    def visit_unsafe(self, stmt: UnsafeBlock):
        old_unsafe = self.unsafe
        self.unsafe = True
        self.emit("# unsafe block")
        for s in stmt.body:
            self.visit_statement(s)
        self.unsafe = old_unsafe

    def visit_if(self, stmt: IfStmt):
        cond = self._expr_to_str(stmt.cond)
        self.emit(f"if {cond}:")
        self.indent += 1
        for s in stmt.then_body:
            self.visit_statement(s)
        self.indent -= 1
        if stmt.else_body:
            self.emit("else:")
            self.indent += 1
            for s in stmt.else_body:
                self.visit_statement(s)
            self.indent -= 1

    def visit_loop(self, stmt: LoopStmt):
        self.emit("while True:")
        self.indent += 1
        for s in stmt.body:
            self.visit_statement(s)
        self.indent -= 1

    def visit_for(self, stmt: ForStmt):
        if stmt.inclusive:
            range_str = f"range({self._expr_to_str(stmt.start)}, {self._expr_to_str(stmt.end)} + 1)"
        else:
            range_str = f"range({self._expr_to_str(stmt.start)}, {self._expr_to_str(stmt.end)})"
        self.emit(f"for {stmt.var} in {range_str}:")
        self.indent += 1
        for s in stmt.body:
            self.visit_statement(s)
        self.indent -= 1

    def visit_end(self, stmt: EndStmt):
        val = self._expr_to_str(stmt.value)
        self.emit(f"return {val}")

    def _expr_to_str(self, expr: Expr) -> str:
        """Konwertuje wyrażenie AST na kod Pythona, z obsługą operatora ?."""
        if isinstance(expr, BinOp):
            left = self._expr_to_str(expr.left)
            right = self._expr_to_str(expr.right)
            return f"({left} {expr.op} {right})"
        if isinstance(expr, UnaryOp):
            operand = self._expr_to_str(expr.operand)
            return f"{expr.op}{operand}"
        if isinstance(expr, IntLit):
            return str(expr.value)
        if isinstance(expr, FloatLit):
            return str(expr.value)
        if isinstance(expr, StringLit):
            return f'"{expr.value}"'
        if isinstance(expr, BoolLit):
            return str(expr.value).lower()
        if isinstance(expr, Var):
            return expr.name
        if isinstance(expr, Call):
            args = ", ".join(self._expr_to_str(arg) for arg in expr.args)
            return f"{expr.func}({args})"
        if isinstance(expr, Propagate):
            # Operator ? - generujemy kod z próbą i propagacją błędu
            # Dla uproszczenia zakładamy, że funkcje mogą rzucać wyjątek,
            # a operator ? przekształca go w wyjątek wyżej.
            inner = self._expr_to_str(expr.expr)
            # Generujemy inline try-except:
            #   _tmp = inner
            #   if _tmp is None: raise SomeError
            # ale bardziej elegancko: użyjemy __hyper_try
            # W praktyce najprościej: wywołanie funkcji i natychmiastowe sprawdzenie.
            # Ponieważ Numba nie lubi try/except, lepiej użyć specjalnej funkcji pomocniczej.
            # Użyjemy tutaj prostego podejścia: zdefiniujemy funkcję `__hyper_try` na górze kodu.
            # Ale żeby nie komplikować, dla Numbowego kodu lepiej unikać wyjątków.
            # Dlatego zamiast tego możemy po prostu wywołać funkcję i jeśli zwróci None, przerwać.
            # W specyfikacji Hyper Lang operator ? przerywa działanie i przesyła błąd wyżej.
            # W Pythonie możemy to zrobić rzucając wyjątek:
            return f"(__hyper_try({inner}))"

        raise ValueError(f"Unknown expression: {type(expr)}")
