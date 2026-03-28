from dataclasses import dataclass
from typing import List, Optional, Union, Any

@dataclass
class Node:
    pass

@dataclass
class Program(Node):
    imports: List['Import']
    functions: List['FunctionDef']
    statements: List['Statement']

@dataclass
class Import(Node):
    path: str

@dataclass
class FunctionDef(Node):
    name: str
    params: List['Param']
    return_type: Optional[str]
    body: List['Statement']
    pub: bool

@dataclass
class Param(Node):
    name: str
    type: str

@dataclass
class Statement(Node):
    pass

@dataclass
class LetStmt(Statement):
    name: str
    type: str
    value: 'Expr'

@dataclass
class LogStmt(Statement):
    value: 'Expr'

@dataclass
class UnsafeBlock(Statement):
    body: List[Statement]

@dataclass
class IfStmt(Statement):
    cond: 'Expr'
    then_body: List[Statement]
    else_body: Optional[List[Statement]]

@dataclass
class LoopStmt(Statement):
    body: List[Statement]

@dataclass
class ForStmt(Statement):
    var: str
    start: 'Expr'
    end: 'Expr'
    inclusive: bool
    body: List[Statement]

@dataclass
class BreakStmt(Statement):
    pass

@dataclass
class ContinueStmt(Statement):
    pass

@dataclass
class EndStmt(Statement):
    value: 'Expr'

@dataclass
class ExprStmt(Statement):
    expr: 'Expr'

@dataclass
class Expr(Node):
    pass

@dataclass
class BinOp(Expr):
    left: Expr
    op: str
    right: Expr

@dataclass
class UnaryOp(Expr):
    op: str
    operand: Expr

@dataclass
class IntLit(Expr):
    value: int

@dataclass
class FloatLit(Expr):
    value: float

@dataclass
class StringLit(Expr):
    value: str

@dataclass
class BoolLit(Expr):
    value: bool

@dataclass
class Var(Expr):
    name: str

@dataclass
class Call(Expr):
    func: str
    args: List[Expr]

@dataclass
class Propagate(Expr):  # operator '?'
    expr: Expr
