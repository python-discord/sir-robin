import ast
from collections.abc import Generator
from random import randrange

MAX_LINE_LENGTH = 50

op_strs = {
    ast.Add: "+",
    ast.Mult: "*",
    ast.Sub: "-",
    ast.Div: "/",
    ast.FloorDiv: "//",
    ast.Mod: "%",
    ast.Pow: "**",
    ast.BitXor: "^",
    ast.BitOr: "|",
    ast.BitAnd: "&",
    ast.LShift: "<<",
    ast.RShift: ">>",
    ast.Invert: "~",
    ast.Not: "not",
    ast.UAdd: "+",
    ast.USub: "-",
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Is: "is",
    ast.IsNot: "is not",
    ast.In: "in",
    ast.NotIn: "not in",
    ast.And: "and",
    ast.Or: "or",
}

# Operator precedence table
precedences = [
    {
        ast.Name,
        ast.Constant,
        ast.JoinedStr,
        ast.List,
        ast.ListComp,
        ast.Dict,
        ast.DictComp,
        ast.Set,
        ast.SetComp,
        ast.Tuple,
        ast.GeneratorExp,
    },
    {ast.Subscript, ast.Call, ast.Attribute},
    {ast.Await},
    {ast.Pow},
    {ast.UAdd, ast.USub, ast.Invert},
    {ast.Mult, ast.MatMult, ast.Div, ast.FloorDiv, ast.Mod},
    {ast.Add, ast.Sub},
    {ast.LShift, ast.RShift},
    {ast.BitAnd},
    {ast.BitXor},
    {ast.BitOr},
    {
        ast.In,
        ast.NotIn,
        ast.Is,
        ast.IsNot,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.NotEq,
        ast.Eq,
    },
    {ast.Not},
    {ast.And},
    {ast.Or},
    {ast.IfExp},
    {ast.Lambda},
    {ast.NamedExpr},
]
precedences = {op: i for i, ops in enumerate(precedences[::-1]) for op in ops}


# Right associative operators
r_assoc = {ast.Pow}

# Statements which can have a semicolon after them
semicolon_able = (
    ast.AnnAssign,
    ast.Assert,
    ast.Assign,
    ast.AugAssign,
    ast.Break,
    ast.Continue,
    ast.Delete,
    ast.Expr,
    ast.Global,
    ast.Import,
    ast.ImportFrom,
    ast.Nonlocal,
    ast.Pass,
    ast.Raise,
    ast.Return,
)

# Operators for which the newline goes before
nl_before_op = {ast.Add, ast.Mult}


_SINGLE_QUOTES = ("'", '"')
_MULTI_QUOTES = ('"""', "'''")
_ALL_QUOTES = (*_SINGLE_QUOTES, *_MULTI_QUOTES)


def get_precedence(node: ast.AST) -> int:
    """Get the precedence of the given node."""
    if isinstance(node, (ast.BoolOp, ast.BinOp, ast.UnaryOp)):
        return precedences[type(node.op)]
    if isinstance(node, ast.Compare):
        return precedences[type(node.ops[0])]
    return precedences.get(type(node), 0)


def space(a: int = 1, b: int = 3) -> str:
    """Randomly generate whitespace of length between the given bounds."""
    return " " * randrange(a, b)


def num_spaces(src: str) -> int:
    """Count the number of spaces at the beginning of the string."""
    return len(src) - len(src.lstrip())


def invert_indents(src: str) -> str:
    """
    Invert the indentation on each line of the given string.
    Lines with the maximum indentation become least indented, and vice versa.
    """
    lines = src.splitlines()
    max_spaces = max(num_spaces(line) for line in lines)
    return "\n".join(
        (max_spaces - num_spaces(line)) * " " + line.lstrip() for line in lines
    )


def parenthesize(node: ast.AST, _nl_able: bool = False) -> str:
    """Wrap the un-parsed node in parentheses."""
    return f"({space()}{unparse(node, True)}{space()})"


def indent(nodes: list[ast.AST], n: int) -> Generator[str, None, None]:
    """
    Indent each line of the un-parsed nodes by the given number of spaces.
    Multiple nodes are put on the same line, separated by semicolons, if possible
    until they hit the line length limit.
    """
    curr_chunk = []
    curr_len = 0
    for stmt in nodes:
        stmt_lines = unparse(stmt).splitlines()
        if isinstance(stmt, semicolon_able):
            for line in stmt_lines:
                curr_chunk.append(line)
                curr_len += len(line)
                if curr_len > MAX_LINE_LENGTH or curr_chunk[-1][-1] != ";":
                    yield n * " " + space().join(curr_chunk)
                    curr_len = 0
                    curr_chunk = []
        else:
            yield n * " " + space().join(curr_chunk)
            yield from (f"{n * ' '}{line}" for line in stmt_lines)
            curr_len = 0
            curr_chunk = []

    if curr_chunk:
        yield n * " " + space().join(curr_chunk)


def _str_literal_helper(
    string: str, *, quote_types: tuple = _ALL_QUOTES, escape_special_whitespace: bool = False
) -> tuple[str]:
    """
    Helper for writing string literals, minimizing escapes.
    Returns the tuple (string literal to write, possible quote types).
    Equivalent behaviour to ast._Unparser._str_literal_helper.
    """
    def escape_char(c: str) -> str:
        # \n and \t are non-printable, but we only escape them if
        # escape_special_whitespace is True
        if not escape_special_whitespace and c in "\n\t":
            return c
        # Always escape backslashes and other non-printable characters
        if c == "\\" or not c.isprintable():
            return c.encode("unicode_escape").decode("ascii")
        return c

    escaped_string = "".join(map(escape_char, string))
    possible_quotes = quote_types
    if "\n" in escaped_string:
        possible_quotes = [q for q in possible_quotes if q in _MULTI_QUOTES]
    possible_quotes = [q for q in possible_quotes if q not in escaped_string]
    if not possible_quotes:
        # If there aren't any possible_quotes, fallback to using repr
        # on the original string. Try to use a quote from quote_types,
        # e.g., so that we use triple quotes for docstrings.
        string = repr(string)
        quote = next((q for q in quote_types if string[0] in q), string[0])
        return string[1:-1], [quote]
    if escaped_string:
        # Sort so that we prefer '''"''' over """\""""
        possible_quotes.sort(key=lambda q: q[0] == escaped_string[-1])
        # If we're using triple quotes, escape the final quote if we need to
        if possible_quotes[0][0] == escaped_string[-1]:
            assert len(possible_quotes[0]) == 3
            escaped_string = escaped_string[:-1] + "\\" + escaped_string[-1]
    return escaped_string, possible_quotes


def _write_str_avoiding_backslashes(string: str, *, quote_types: tuple = _ALL_QUOTES) -> str:
    """
    Return string literal value with a best effort attempt to avoid backslashes.
    Equivalent behaviour to ast._Unparser._write_str_avoiding_backslashes.
    """
    string, quote_types = _str_literal_helper(string, quote_types=quote_types)
    quote_type = quote_types[0]
    return f"{quote_type}{space()}{string}{space()}{quote_type}"


def _write_fstring_inner(node: ast.AST) -> str:
    if isinstance(node, ast.JoinedStr):
        # for both the f-string itself, and format_spec
        return f"{space()}".join(map(_write_fstring_inner, node.values))
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        value = node.value.replace("{", "{{").replace("}", "}}")
        return value
    elif isinstance(node, ast.FormattedValue):
        return unparse(node)
    else:
        raise ValueError(f"Unexpected node inside ast.JoinedStr: {node!r}")


def unparse(node: ast.AST, nl_able: bool = False, avoid_backslashes: bool = True) -> str:
    """Convert the ast node to formatted(!) Python source code."""
    if isinstance(node, ast.AnnAssign):
        target, annotation, value = node.target, node.annotation, node.value

        return (
            f"{unparse(target)}{space()}:{space()}{unparse(annotation)}"
            + (f"{space()}={space()}{unparse(value)}" if value else "")
            + f"{space()};"
        )
    if isinstance(node, ast.Assert):
        test, msg = node.test, node.msg

        return (
            f"assert{space()}{test}"
            + (f",{space()}{unparse(msg)}" if msg else "")
            + f"{space()};"
        )
    if isinstance(node, ast.Assign):
        targets, value = node.targets, node.value

        return (
            f"{f'{space()}={space()}'.join(map(unparse, targets))}{space()}={space()}{unparse(value)}"
            + f"{space()};"
        )
    if isinstance(node, ast.AsyncFor):
        target, iter_, body, orelse = node.target, node.iter, node.body, node.orelse

        s = [
            f"async{space()}for{space()}{unparse(target)}{space()}in{space()}{unparse(iter_)}{space()}:",
            *indent(body, randrange(2, 5)),
        ]
        if orelse:
            s.append(f"else{space()}:")
            s.extend(indent(orelse, randrange(2, 5)))
        return "\n".join(s)
    if isinstance(node, ast.AsyncFunctionDef):
        name, args, body, decorator_list, returns = (
            node.name,
            node.args,
            node.body,
            node.decorator_list,
            node.returns,
        )

        return "\n".join(
            (
                *(f"@{space()}{unparse(decorator)}" for decorator in decorator_list),
                f"async{space()}def{space()}{name}{space()}({space()}{unparse(args, True)}{space()})"
                + (f"{space()}->{space()}{unparse(returns)}" if returns else "")
                + f"{space()}:",
                *indent(body, randrange(2, 5)),
            )
        )
    if isinstance(node, ast.AsyncWith):
        items, body = node.items, node.body

        return "\n".join(
            [
                f"async{space()}with{space()}{f',{space()}'.join(map(unparse, items))}{space()}:",
                *indent(body, randrange(2, 5)),
            ]
        )
    if isinstance(node, ast.Attribute):
        owner, attr = node.value, node.attr

        return f"{unparse(owner)}{space()}.{space()}{attr}"
    if isinstance(node, ast.AugAssign):
        target, op, value = node.target, node.op, node.value

        return (
            f"{unparse(target)}{space()}{op_strs[type(op)]}={space()}{unparse(value)}{space()};"
        )
    if isinstance(node, ast.Await):
        value = node.value

        return f"await{space()}{unparse(value)}"
    if isinstance(node, ast.BoolOp):
        op, values = node.op, node.values

        return f"{space()}{op_strs[type(op)]}{space()}".join(
            f"{(parenthesize if get_precedence(value) <= get_precedence(op) else unparse)(value)}"
            for value in values
        )
    if isinstance(node, ast.Break):

        return f"break{space()};"
    if isinstance(node, ast.BinOp):
        left, op, right = node.left, node.op, node.right

        op_type = type(op)

        par_left = (
            get_precedence(left) < get_precedence(op)
            if op_type not in r_assoc
            else get_precedence(left) <= get_precedence(op)
        )
        par_right = (
            get_precedence(right) <= get_precedence(op)
            if op_type not in r_assoc
            else get_precedence(right) < get_precedence(op)
        )
        nl_before = (op_type in nl_before_op) * "\n"
        nl_after = (op_type not in nl_before_op) * "\n"

        return (
            f"({space()}{(parenthesize if par_left else unparse)(left, True)}{space()}"
            + f"{nl_before}{op_strs[type(op)]}{space()}{nl_after}"
            + f"{(parenthesize if par_right else unparse)(right, True)}{space()})"
        )
    if isinstance(node, ast.Call):
        func, args, keywords = node.func, node.args, node.keywords

        return (
            f"{(parenthesize if get_precedence(func) < get_precedence(node) else unparse)(func)}{space()}"
            f"({space()}{f'{space()},{space()}'.join(unparse(arg, True) for arg in args)}"
            + (
                (f"{space()},{space()}" if args else "")
                + f"{space()},{space()}".join(unparse(kwarg, True) for kwarg in keywords)
                if keywords
                else ""
            )
            + space()
            + ")"
        )
    if isinstance(node, ast.ClassDef):
        name, bases, keywords, body, decorator_list = (
            node.name,
            node.bases,
            node.keywords,
            node.body,
            node.decorator_list,
        )

        args = bases + keywords
        return "\n".join(
            [
                *(f"@{space()}{unparse(decorator)}" for decorator in decorator_list),
                f"class{space()}{name}{space()}"
                + (
                    f"({space()}{f'{space()},{space()}'.join(unparse(arg, True) for arg in args)}{space()})"
                    if args
                    else ""
                )
                + f"{space()}:",
                *indent(body, randrange(2, 5)),
            ]
        )
    if isinstance(node, ast.Compare):
        left, ops, comparators = node.left, node.ops, node.comparators

        return (
            f"{(parenthesize if get_precedence(left) <= get_precedence(ops[0]) else unparse)(left)}"
            + f"{space()}".join(
                f"{space()}{op_strs[type(op)]}{space()}"
                f"{(parenthesize if get_precedence(left) <= get_precedence(op) else unparse)(comparator)}"
                for op, comparator in zip(ops, comparators)
            )
        )
    if isinstance(node, ast.Constant):
        value = node.value

        if avoid_backslashes and isinstance(value, str):
            return _write_str_avoiding_backslashes(value)

        return source[node.col_offset:node.end_col_offset]
    if isinstance(node, ast.Continue):

        return f"continue{space()};"
    if isinstance(node, ast.Delete):
        targets = node.targets

        return f"del{space()}{f'{space()},{space()}'.join(map(unparse, targets))};"
    if isinstance(node, ast.Dict):
        keys, values = node.keys, node.values

        return (
            "{"
            + space()
            + f"{space()},{space()}".join(
                f"{unparse(key)}{space()}:{space()}{unparse(value)}"
                if key
                else f"**{space()}{unparse(value)}"
                for key, value in zip(keys, values)
            )
            + space()
            + "}"
        )
    if isinstance(node, ast.DictComp):
        key, value, generators = node.key, node.value, node.generators

        return (
            "{"
            + space()
            + f"{unparse(key)}{space()}:{space()}{unparse(value)}{space()}"
            + f"{space()}".join(map(unparse, generators))
            + space()
            + "}"
        )
    if isinstance(node, ast.ExceptHandler):
        type_, name, body = node.type, node.name, node.body

        return "\n".join(
            [
                f"except{space()}"
                + (f"{unparse(type_)}" if type_ else "")
                + (f"{space()}as{space()}{name}" if name else "")
                + f"{space()}:",
                *indent(body, randrange(2, 5)),
            ]
        )
    if isinstance(node, ast.Expr):
        value = node.value

        return unparse(value) + f"{space()};"
    if isinstance(node, ast.For):
        target, iter_, body, orelse = node.target, node.iter, node.body, node.orelse

        s = [
            f"for{space()}{unparse(target)}{space()}in{space()}{unparse(iter_)}:",
            *indent(body, randrange(2, 5)),
        ]
        if orelse:
            s.append(f"else{space()}:")
            s.extend(indent(orelse, randrange(2, 5)))
        return "\n".join(s)
    if isinstance(node, ast.FormattedValue):
        value, conversion, format_spec = (
            node.value,
            node.conversion,
            node.format_spec
        )

        expr = unparse(value, avoid_backslashes=True)
        if "\\" in expr:
            raise ValueError(
                "Unable to avoid backslash in f-string expression part"
            )

        return (
            "{"
            + space()
            + expr
            + f"!{chr(conversion)}" * (conversion != -1)
            + f":{_write_fstring_inner(format_spec)}" * bool(format_spec)
            + space()
            + "}"
        )
    if isinstance(node, ast.FunctionDef):
        name, args, body, decorator_list, returns = (
            node.name,
            node.args,
            node.body,
            node.decorator_list,
            node.returns,
        )

        return "\n".join(
            [
                *(f"@{space()}{unparse(decorator)}" for decorator in decorator_list),
                f"sync{space()}def{space()}{name}{space()}"
                f"({space()}{unparse(args, True)}{space()})"
                + (f"{space()}->{space()}{unparse(returns)}" if returns else "")
                + f"{space()}:",
                *indent(body, randrange(2, 5)),
            ]
        )
    if isinstance(node, ast.GeneratorExp):
        elt, generators = node.elt, node.generators

        return (
            f"({space()}"
            + f"{unparse(elt)}{space()}"
            + f"{space()}".join(map(unparse, generators))
            + f"{space()})"
        )
    if isinstance(node, ast.Global):
        names = node.names

        return f"global{space()}{', '.join(map(unparse, names))}{space()};"
    if isinstance(node, ast.If):
        test, body, orelse = node.test, node.body, node.orelse

        s = [
            f"if{space()}{unparse(test)}{space()}:",
            *indent(body, randrange(2, 5)),
        ]
        if orelse:
            s.append(f"else{space()}:")
            s.extend(indent(orelse, randrange(2, 5)))
        return "\n".join(s)
    if isinstance(node, ast.IfExp):
        test, body, orelse = node.test, node.body, node.orelse

        return (
            f"{(parenthesize if get_precedence(body) < get_precedence(node) else unparse)(body)}{space()}"
            + f"if{space()}"
            + f"{(parenthesize if get_precedence(body) < get_precedence(node) else unparse)(test)}{space()}"
            + f"else{space()}{(parenthesize if get_precedence(body) < get_precedence(node) else unparse)(orelse)}"
        )
    if isinstance(node, ast.Import):
        names = node.names

        return (
            f"import{space()}"
            + f"{space()},{space()}".join(
                f"{name.name}"
                + (f"{space()}as{space()}{name.asname}" if name.asname else "")
                for name in names
            )
            + f"{space()};"
        )
    if isinstance(node, ast.ImportFrom):
        module, names, level = node.module, node.names, node.level

        return (
            f"from{space()}{'.'*level}{module}{space()}import{space()}"
            + f"{space()},{space()}".join(
                f"{name.name}"
                + (f"{space()}as{space()}{name.asname}" if name.asname else "")
                for name in names
            )
            + f"{space()};"
        )
    if isinstance(node, ast.JoinedStr):
        if avoid_backslashes:
            return _write_str_avoiding_backslashes(_write_fstring_inner(node))

        fstring_parts = []
        quote_types = _ALL_QUOTES

        for value in node.values:
            is_constant = isinstance(value, ast.Constant)
            value, quote_types = _str_literal_helper(
                _write_fstring_inner(value),
                quote_types=quote_types,
                escape_special_whitespace=is_constant,
            )
            fstring_parts.append(value)

        quote_type = quote_types[0]
        return f"f{space()}{quote_type}{space()}{''.join(fstring_parts)}{space()}{quote_type}"
    if isinstance(node, ast.Lambda):
        args, body = node.args, node.body

        return f"lambda{space()}{unparse(args)}{space()}:{space()}{unparse(body)}"
    if isinstance(node, ast.List):
        elts = node.elts

        return (
            f"[{space()}"
            + f"{space()},{space()}".join(unparse(elt, True) for elt in elts)
            + f"{space()}]"
        )
    if isinstance(node, ast.ListComp):
        elt, generators = node.elt, node.generators

        return (
            f"[{space()}"
            + f"{unparse(elt)} "
            + f"{space()}".join(map(unparse, generators))
            + f"{space()}]"
        )
    if isinstance(node, ast.Module):
        body = node.body

        return "\n".join(indent(body, 0))
    if isinstance(node, ast.Name):
        id_ = node.id

        return id_
    if isinstance(node, ast.NamedExpr):
        target, value = node.target, node.value

        return f"({unparse(target)}{space()}:={space()}{unparse(value)})"
    if isinstance(node, ast.Nonlocal):
        names = node.names

        return f"nonlocal{space()}{f'{space()},{space()}'.join(map(unparse, names))};{space()}"
    if isinstance(node, ast.Pass):

        return f"pass{space()};"
    if isinstance(node, ast.Raise):
        exc, cause = node.exc, node.cause

        if not exc:
            return f"raise{space()};"

        return (
            f"raise{space()}{unparse(exc)}"
            + (f"{space()}from{space()}{unparse(cause)}" if cause else "")
            + f"{space()};"
        )
    if isinstance(node, ast.Return):
        value = node.value

        if not value:
            return f"return{space()};"

        return f"return{space()}{unparse(value)}{space()};"
    if isinstance(node, ast.Set):
        elts = node.elts

        return (
            "{"
            + space()
            + f"{space()},{space()}".join(unparse(elt, True) for elt in elts)
            + space()
            + "}"
        )
    if isinstance(node, ast.SetComp):
        elt, generators = node.elt, node.generators

        return (
            "{"
            + space()
            + f"{unparse(elt)}{space()}"
            + f"{space()}".join(map(unparse, generators))
            + space()
            + "}"
        )
    if isinstance(node, ast.Slice):
        lower, upper, step = node.lower, node.upper, node.step
        lower = '' if lower is None else unparse(lower)
        upper = '' if upper is None else unparse(upper)
        step = '' if step is None else unparse(step)
        s = f"{lower}{space()}:{space()}{upper}{space()}:{space()}{step}"
        return ":" if s.replace(" ", "") == "::" else s
    if isinstance(node, ast.Starred):
        value = node.value

        return f"*{space()}{parenthesize(value)}"
    if isinstance(node, ast.Subscript):
        value, slice_ = node.value, node.slice

        return (
            f"{(parenthesize if get_precedence(value) < get_precedence(node) else unparse)(value)}{space()}"
            f"[{space()}{unparse(slice_, True)}{space()}]"
        )
    if isinstance(node, ast.Try):
        body, handlers, orelse, finalbody = (
            node.body,
            node.handlers,
            node.orelse,
            node.finalbody,
        )

        s = [f"try{space()}:", *indent(body, randrange(2, 5))]
        for handler in handlers:
            s.extend(unparse(handler).splitlines())
        if orelse:
            s.append(f"else{space()}:")
            s.extend(indent(orelse, randrange(2, 5)))
        if finalbody:
            s.append(f"finally{space()}:")
            s.extend(indent(finalbody, randrange(2, 5)))
        return "\n".join(s)
    if isinstance(node, ast.Tuple):
        elts = node.elts

        return (
            f"({space()}"
            + f"{space()},{space()}".join(unparse(elt, True) for elt in elts)
            + f"{space()}," * (len(elts) == 1)
            + f"{space()})"
        )
    if isinstance(node, ast.UnaryOp):
        op, operand = node.op, node.operand

        par_op = get_precedence(operand) < get_precedence(op)
        return f"{op_strs[type(op)]}{space()}{(parenthesize if par_op else unparse)(operand)}"
    if isinstance(node, ast.While):
        test, body, orelse = node.test, node.body, node.orelse

        s = [
            f"while{space()}{unparse(test)}{space()}:",
            *indent(body, randrange(2, 5)),
        ]
        if orelse:
            s.append(f"else{space()}:")
            s.extend(indent(orelse, randrange(2, 5)))
        return "\n".join(s)
    if isinstance(node, ast.With):
        items, body = node.items, node.body

        return "\n".join(
            [
                f"with{space()}{f'{space()},{space()}'.join(map(unparse, items))}{space()}:",
                *indent(body, randrange(2, 5)),
            ]
        )
    if isinstance(node, ast.Yield):
        value = node.value

        if not value:
            return f"yield{space()};"

        return f"yield{space()}{unparse(value)}"
    if isinstance(node, ast.YieldFrom):
        value = node.value

        return f"yield{space()}from{space()}{unparse(value)}"

    if isinstance(node, ast.arg):
        arg, annotation = node.arg, node.annotation

        return arg + (f"{space()}:{space()}{unparse(annotation)}" if annotation else "")
    if isinstance(node, ast.arguments):
        posonlyargs, args, vararg, kwonlyargs, kw_defaults, kwarg, defaults = (
            node.posonlyargs,
            node.args,
            node.vararg,
            node.kwonlyargs,
            node.kw_defaults,
            node.kwarg,
            node.defaults,
        )

        s = ""
        first = True
        all_args = posonlyargs + args
        defaults = [None] * (len(all_args) - len(defaults)) + defaults
        for index, elements in enumerate(zip(all_args, defaults), 1):
            a, d = elements
            if first:
                first = False
            else:
                s += f"{space()},{space()}"
            s += unparse(a, nl_able)
            if d:
                s += f"{space()}={space()}" + unparse(d, nl_able)
            if index == len(posonlyargs):
                s += f"{space()},{space()}/"

        if vararg or kwonlyargs:
            if first:
                first = False
            else:
                s += f"{space()},{space()}"
            s += f"{space()}*{space()}"
            if vararg:
                s += vararg.arg
                if vararg.annotation:
                    s += f"{space()}:{space()}" + unparse(vararg.annotation, nl_able)

        if kwonlyargs:
            for a, d in zip(kwonlyargs, kw_defaults):
                s += f"{space()},{space()}" + unparse(a, nl_able)
                if d:
                    s += f"{space()}={space()}{unparse(d, nl_able)}"
        if kwarg:
            if not first:
                s += f"{space()},{space()}"
            s += f"**{space()}{kwarg.arg}"
            if kwarg.annotation:
                s += f"{space()}:{space()}{unparse(kwarg.annotation, nl_able)}"
        return s
    if isinstance(node, ast.keyword):
        arg, value = node.arg, node.value

        return (f"{arg}{space()}={space()}" if arg else f"**{space()}") + unparse(value)
    if isinstance(node, ast.comprehension):
        target, iter_, ifs, is_async = node.target, node.iter, node.ifs, node.is_async

        return (
            f"async{space()}" if is_async else ""
            + f"for{space()}{unparse(target)}{space()}in{space()}{unparse(iter_)}"
            + (f"{space()}" if ifs else "")
            + f"{space()}".join(f"if{space()}{unparse(if_)}" for if_ in ifs)
        )
    if isinstance(node, ast.withitem):
        context_expr, optional_vars = node.context_expr, node.optional_vars

        return f"{unparse(context_expr)}" + (
            f"{space()}as{space()}{unparse(optional_vars)}" if optional_vars else ""
        )

    return ast.unparse(node)


def blurplify(src: str) -> str:
    """Format the given source code in accordance with PEP 9001."""
    global source  # use a global variable only to get the original source part of constants
    source = src
    src_ast = ast.parse(src)
    return "# coding=UTF-8-NOBOM\n" + invert_indents(unparse(src_ast))
