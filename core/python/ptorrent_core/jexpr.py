"""j_expr — a researcher's methodology travels as arithmetic over column names,
never as code. No eval(), no dynamic import, no escape hatch.

Grammar (matches libptorrent src/pt_jexpr.c):

    expr    := term (('+' | '-') term)*
    term    := unary (('*' | '/') unary)*
    unary   := ('-' | '+') unary | power
    power   := primary ('**' unary)?          right-associative
    primary := NUMBER | IDENT | CALL | '(' expr ')'
    CALL    := IDENT '(' expr (',' expr)* ')'

Precedence follows Python: -2**2 == -4, 2**-1 == 0.5.

NaN discipline (deliberate, load-bearing): division by zero, sqrt of a negative,
log of a non-positive, and overflow all yield NaN and propagate. NaN is a
legitimate outcome, not a failure — it classifies as UNDEFINED, never INF. A
variable that was never bound at all is a *configuration* error (raises), as
opposed to a variable bound as null which is a *data* condition (NaN).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .errors import PtErr, PtError

_FUNCS_1 = {
    "sqrt": lambda x: math.sqrt(x) if x >= 0 else math.nan,
    "abs": abs,
    "log": lambda x: math.log(x) if x > 0 else math.nan,
    "log10": lambda x: math.log10(x) if x > 0 else math.nan,
    "exp": lambda x: _guard(math.exp, x),
}
_FUNCS_2 = {"max": max, "min": min}
_CONSTS = {"pi": math.pi, "e": math.e}

_TOKEN_RE = re.compile(r"""
      (?P<num>\d+\.\d+|\.\d+|\d+\.?)([eE][+-]?\d+)?
    | (?P<pow>\*\*)
    | (?P<op>[+\-*/(),])
    | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
    | (?P<ws>\s+)
""", re.VERBOSE)


def _guard(fn, *a):
    try:
        v = fn(*a)
    except (ValueError, OverflowError):
        return math.nan
    return v if isinstance(v, (int, float)) and math.isfinite(v) else (
        v if isinstance(v, (int, float)) else math.nan)


# ── AST ─────────────────────────────────────────────────────────────────────

@dataclass
class Num:
    v: float

@dataclass
class Var:
    name: str

@dataclass
class Unary:
    op: str
    x: object

@dataclass
class Bin:
    op: str
    a: object
    b: object

@dataclass
class Call:
    name: str
    args: list


class _Parser:
    def __init__(self, src: str):
        self.toks: list[tuple[str, str]] = []
        pos = 0
        for m in _TOKEN_RE.finditer(src):
            if m.start() != pos:
                raise PtError(PtErr.E_PARSE, f"col {pos}: unexpected character {src[pos]!r}")
            pos = m.end()
            if m.lastgroup == "ws":
                continue
            self.toks.append((m.lastgroup, m.group()))
        if pos != len(src):
            raise PtError(PtErr.E_PARSE, f"col {pos}: unexpected character {src[pos]!r}")
        self.i = 0

    def _peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def _next(self):
        t = self._peek()
        self.i += 1
        return t

    def _expect(self, val):
        k, v = self._next()
        if v != val:
            raise PtError(PtErr.E_PARSE, f"expected {val!r}, got {v!r}")

    def parse(self):
        node = self._expr()
        if self.i != len(self.toks):
            raise PtError(PtErr.E_PARSE, f"trailing tokens from {self._peek()[1]!r}")
        return node

    def _expr(self):
        node = self._term()
        while self._peek()[1] in ("+", "-"):
            op = self._next()[1]
            node = Bin(op, node, self._term())
        return node

    def _term(self):
        node = self._unary()
        while self._peek()[1] in ("*", "/"):
            op = self._next()[1]
            node = Bin(op, node, self._unary())
        return node

    def _unary(self):
        if self._peek()[1] in ("+", "-"):
            op = self._next()[1]
            return Unary(op, self._unary())
        return self._power()

    def _power(self):
        base = self._primary()
        if self._peek()[0] == "pow":
            self._next()
            return Bin("**", base, self._unary())   # right-assoc
        return base

    def _primary(self):
        k, v = self._next()
        if k == "num":
            return Num(float(v))
        if v == "(":
            node = self._expr()
            self._expect(")")
            return node
        if k == "ident":
            if self._peek()[1] == "(":
                self._next()
                args = []
                if self._peek()[1] != ")":
                    args.append(self._expr())
                    while self._peek()[1] == ",":
                        self._next()
                        args.append(self._expr())
                self._expect(")")
                return self._make_call(v, args)
            return Var(v)
        raise PtError(PtErr.E_PARSE, f"unexpected token {v!r}")

    @staticmethod
    def _make_call(name, args):
        if name in _FUNCS_1:
            if len(args) != 1:
                raise PtError(PtErr.E_PARSE, f"{name}() takes 1 argument, got {len(args)}")
        elif name in _FUNCS_2:
            if len(args) != 2:
                raise PtError(PtErr.E_PARSE, f"{name}() takes 2 arguments, got {len(args)}")
        else:
            raise PtError(PtErr.E_PARSE, f"unknown function {name!r}")
        return Call(name, args)


class JExpr:
    """A compiled expression. Reusable across rows."""

    def __init__(self, src: str):
        self.src = src
        self._ast = _Parser(src).parse()
        self._vars: set[str] = set()
        self._collect(self._ast)

    def _collect(self, n):
        match n:
            case Var(name):
                if name not in _CONSTS:
                    self._vars.add(name)
            case Unary(_, x):
                self._collect(x)
            case Bin(_, a, b):
                self._collect(a); self._collect(b)
            case Call(_, args):
                for a in args:
                    self._collect(a)

    @property
    def variables(self) -> list[str]:
        return sorted(self._vars)

    def eval(self, bindings: dict) -> float:
        """bindings maps a column name -> float or None (None == SQL NULL -> NaN).
        A referenced name absent from bindings raises E_NOTFOUND."""
        return self._ev(self._ast, bindings)

    def _ev(self, n, b) -> float:
        match n:
            case Num(v):
                return v
            case Var(name):
                if name in _CONSTS:
                    return _CONSTS[name]
                if name not in b:
                    raise PtError(PtErr.E_NOTFOUND, f"variable {name!r} was never bound")
                v = b[name]
                if v is None:
                    return math.nan
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return math.nan
            case Unary(op, x):
                v = self._ev(x, b)
                return -v if op == "-" else +v
            case Bin(op, a, bnode):
                x = self._ev(a, b)
                y = self._ev(bnode, b)
                if op == "+":
                    return _fin(x + y)
                if op == "-":
                    return _fin(x - y)
                if op == "*":
                    return _fin(x * y)
                if op == "/":
                    return math.nan if y == 0 else _fin(x / y)
                if op == "**":
                    try:
                        return _fin(x ** y)
                    except (ValueError, OverflowError, ZeroDivisionError):
                        return math.nan
            case Call(name, args):
                vals = [self._ev(a, b) for a in args]
                if any(not math.isfinite(v) for v in vals):
                    return math.nan
                fn = _FUNCS_1.get(name) or _FUNCS_2[name]
                return _fin(fn(*vals))
        raise PtError(PtErr.E_PARSE, "corrupt AST")


def _fin(v: float) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return math.nan
    return v if math.isfinite(v) else math.nan


def compile_expr(src: str) -> JExpr:
    return JExpr(src)


def eval_once(src: str, bindings: dict) -> float:
    return JExpr(src).eval(bindings)
