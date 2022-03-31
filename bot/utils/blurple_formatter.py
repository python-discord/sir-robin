import ast
import random
from collections.abc import Generator
from random import randrange

max_line_length = 50

op_strs = {
    ast.Add: "+",
    ast.Mult: "*",
    ast.Sub: "-",
    ast.Div: "/",
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

# operator precedence table
precedences = [
    {
        ast.Name,
        ast.Constant,
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
    {ast.BinOp},
    {
        ast.Compare,
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


# right associative operators
r_assoc = {ast.Pow}

# statements which can have a semicolon after them
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

# operators which the newline goes before
nl_before_op = {ast.Add, ast.Mult}


def space(a: int = 0, b: int = 3) -> str:
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
    return "\n".join((max_spaces - num_spaces(line)) * " " + line.lstrip() for line in lines)


def parenthesize(node: ast.AST, _nl_able: bool = False) -> str:
    """Wrap the un-parsed node in parentheses."""
    return f"({unparse(node, True)})"


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
                if curr_len > max_line_length or curr_chunk[-1][-1] != ";":
                    yield f"{n * ' '}{f'{space()}'.join(curr_chunk)}"
                    curr_len = 0
                    curr_chunk = []
        else:
            yield f"{n * ' '}{f'{space()}'.join(curr_chunk)}"
            yield from (f"{n * ' '}{line}" for line in stmt_lines)
            curr_len = 0
            curr_chunk = []
    yield f"{n * ' '}{f'{space()}'.join(curr_chunk)}"


def unparse(node: ast.AST, nl_able: bool = False) -> str:
    """
    Convert the ast node to formatted(!) Python source code.
    """
    match node:
        case ast.AnnAssign(target=target, annotation=annotation, value=value):
            return (
                f"{unparse(target)}{space()}:{space()}{unparse(annotation)}"
                + (f"{space()}={space()}{unparse(value)}" if value else "")
                + f"{space()};"
            )
        case ast.Assert(test=test, msg=msg):
            return (
                f"assert{space(1)}{test}"
                + (f",{space()}{unparse(msg)}" if msg else "")
                + f"{space()};"
            )
        case ast.Assign(targets=targets, value=value):
            return (
                f"{f'{space()}={space()}'.join(map(unparse, targets))}{space()}={space()}{unparse(value)}"
                + f"{space()};"
            )
        case ast.AsyncFor(target=target, iter=iter_, body=body, orelse=orelse):
            s = [
                f"async{space()}for{space()}{unparse(target)}{space()}in{space()}{unparse(iter_)}{space()}:",
                *indent(body, randrange(2, 5)),
            ]
            if orelse:
                s.append(f"else{space()}:")
                s.extend(indent(orelse, randrange(2, 5)))
            return "\n".join(s)
        case ast.AsyncFunctionDef(
            name=name,
            args=args,
            body=body,
            decorator_list=decorator_list,
            returns=returns,
        ):
            return "\n".join(
                (
                    *(
                        f"@{space()}{unparse(decorator)}"
                        for decorator in decorator_list
                    ),
                    f"async{space(1)}def{space(1)}{name}{space()}({space()}{unparse(args, True)}{space()})"
                    + (f"{space()}->{space()}{unparse(returns)}" if returns else "")
                    + f"{space()}:",
                    *indent(body, randrange(2, 5)),
                )
            )
        case ast.AsyncWith(items=items, body=body):
            return "\n".join(
                [
                    f"async{space(1)}with {f',{space()}'.join(map(unparse, items))}{space()}:",
                    *indent(body, randrange(2, 5)),
                ]
            )
        case ast.Attribute(value=owner, attr=attr):
            return f"{unparse(owner)}{space()}.{space()}{attr}"
        case ast.AugAssign(target=target, op=op, value=value):
            return f"{unparse(target)}{space()}{op_strs[type(op)]}={space()}{unparse(value)};"
        case ast.Await(value=value):
            return f"await{space(1)}{unparse(value)}"
        case ast.BoolOp(op=op, values=values):
            return f"{space(1)}{op_strs[type(op)]}{space(1)}".join(
                f"{(parenthesize if precedences[type(value)] <= precedences[type(op)] else unparse)(value)}"
                for value in values
            )
        case ast.Break():
            return f"break{space()};"
        case ast.BinOp(left=left, op=op, right=right):
            left_type = type(left)
            right_type = type(right)
            op_type = type(op)
            if isinstance(left, (ast.BoolOp, ast.BinOp)):
                left_type = type(left.op)
            if isinstance(right, (ast.BoolOp, ast.BinOp)):
                right_type = type(right.op)

            par_left = (
                precedences[left_type] < precedences[op_type]
                if op_type not in r_assoc
                else precedences[left_type] <= precedences[op_type]
            )
            par_right = (
                precedences[right_type] <= precedences[op_type]
                if op_type not in r_assoc
                else precedences[right_type] < precedences[op_type]
            )
            nl_before = (op_type in nl_before_op) * "\n"
            nl_after = (op_type not in nl_before_op) * "\n"
            if nl_able:
                return (
                    f"{(parenthesize if par_left else unparse)(left, nl_able)}{space()}"
                    + f"{nl_before}{op_strs[type(op)]}{space()}{nl_after}"
                    + f"{(parenthesize if par_right else unparse)(right, nl_able)}"
                )
            else:
                return (
                    f"({(parenthesize if par_left else unparse)(left, True)}{space()}"
                    + f"{nl_before}{op_strs[type(op)]}{space()}{nl_after}"
                    + f"{(parenthesize if par_right else unparse)(right, True)})"
                )
        case ast.Call(func=func, args=args, keywords=keywords):
            return (
                f"{(parenthesize if precedences[type(func)] < precedences[ast.Call] else unparse)(func)}{space()}"
                f"({space()}{f',{space()}'.join(unparse(arg, True) for arg in args)}"
                + (
                    (f",{space()}" if args else "") + f",{space()}".join(unparse(kwarg, True) for kwarg in keywords)
                    if keywords
                    else ""
                )
                + space()
                + ")"
            )
        case ast.ClassDef(
            name=name,
            bases=bases,
            keywords=keywords,
            body=body,
            decorator_list=decorator_list,
        ):
            args = bases + keywords
            return "\n".join(
                [
                    *(
                        f"@{space()}{unparse(decorator)}"
                        for decorator in decorator_list
                    ),
                    f"class{space(1)}{name}{space()}"
                    + (
                        f"({space()}{f',{space()}'.join(unparse(arg, True) for arg in args)}{space()})"
                        if args
                        else ""
                    )
                    + f"{space()}:",
                    *indent(body, randrange(2, 5)),
                ]
            )
        case ast.Compare(left=left, ops=ops, comparators=comparators):
            return (
                f"{(parenthesize if precedences[type(left)] <= precedences[ast.Compare] else unparse)(left)}"
                + f"{space()}".join(
                    f"{space()}{op_strs[type(op)]}{space()}"
                    f"{(parenthesize if precedences[type(left)] <= precedences[ast.Compare] else unparse)(comparator)}"
                    for op, comparator in zip(ops, comparators)
                )
            )
        case ast.Constant(value=value):
            return repr(value) if value != Ellipsis else "..."
        case ast.Continue():
            return f"continue{space()};"
        case ast.Delete(targets=targets):
            return f"del{space(1)}{f',{space()}'.join(map(unparse, targets))};"
        case ast.Dict(keys=keys, values=values):
            return (
                "{"
                + space()
                + f",{space()}".join(
                    f"{unparse(key)}{space()}:{space()}{unparse(value)}"
                    if key
                    else f"**{space()}{unparse(value)}"
                    for key, value in zip(keys, values)
                )
                + space()
                + "}"
            )
        case ast.DictComp(key=key, value=value, generators=generators):
            return (
                "{"
                + space()
                + f"{unparse(key)}{space()}:{space()}{unparse(value)}{space(1)}"
                + f"{space(1)}".join(map(unparse, generators))
                + space()
                + "}"
            )
        case ast.ExceptHandler(type=type_, name=name, body=body):
            return "\n".join(
                [
                    f"except{space(1)}"
                    + (f" {unparse(type_)}" if type_ else "")
                    + (f"{space(1)}as{space(1)}{name}" if name else "")
                    + f"{space()}:",
                    *indent(body, randrange(2, 5)),
                ]
            )
        case ast.Expr(value=value):
            return unparse(value) + f"{space()};"
        case ast.For(target=target, iter=iter_, body=body, orelse=orelse):
            s = [
                f"for {unparse(target)} in {unparse(iter_)}:",
                *indent(body, randrange(2, 5)),
            ]
            if orelse:
                s.append(f"else{space()}:")
                s.extend(indent(orelse, randrange(2, 5)))
            return "\n".join(s)
        case ast.FormattedValue():
            return ast.unparse(node)
        case ast.FunctionDef(
            name=name,
            args=args,
            body=body,
            decorator_list=decorator_list,
            returns=returns,
        ):
            return "\n".join(
                [
                    *(
                        f"@{space()}{unparse(decorator)}"
                        for decorator in decorator_list
                    ),
                    f"{f'sync{space(1)}'*(random.random()>.5)}def{space(1)}{name}{space()}"
                    f"({space()}{unparse(args, True)}{space()})"
                    + (f"{space()}->{space()}{unparse(returns)}" if returns else "")
                    + f"{space()}:",
                    *indent(body, randrange(2, 5)),
                ]
            )
        case ast.GeneratorExp(elt=elt, generators=generators):
            return (
                f"({space()}"
                + f"{unparse(elt)}{space()}"
                + f"{space()}".join(map(unparse, generators))
                + f"{space()})"
            )
        case ast.Global(names=names):
            return f"global{space(1)}{', '.join(map(unparse, names))}{space()};"
        case ast.If(test=test, body=body, orelse=orelse):
            s = [
                f"if{space(1)}{unparse(test)}{space()}:",
                *indent(body, randrange(2, 5)),
            ]
            if orelse:
                s.append(f"else{space()}:")
                s.extend(indent(orelse, randrange(2, 5)))
            return "\n".join(s)
        case ast.IfExp(test=test, body=body, orelse=orelse):
            return (
                f"{(parenthesize if precedences[type(body)] < precedences[ast.IfExp] else unparse)(body)}{space(1)}"
                + f"if{space(1)}{(parenthesize if precedences[type(body)] < precedences[ast.IfExp] else unparse)(test)}{space(1)}"
                + f"else{space(1)}{(parenthesize if precedences[type(body)] < precedences[ast.IfExp] else unparse)(orelse)}"
            )
        case ast.Import(names=names):
            return (
                f"import{space(1)}"
                + f",{space()}".join(
                    f"{name.name}"
                    + (f"{space(1)}as{space(1)}{name.asname}" if name.asname else "")
                    for name in names
                )
                + f"{space()};"
            )
        case ast.ImportFrom(module=module, names=names, level=level):
            return (
                f"from{space(1)}{'.'*level}{module}{space(1)}import{space(1)}"
                + f",{space()}".join(
                    f"{name.name}"
                    + (f"{space(1)}as{space(1)}{name.asname}" if name.asname else "")
                    for name in names
                )
                + f"{space()};"
            )
        case ast.JoinedStr():
            return ast.unparse(node)
        case ast.Lambda(args=args, body=body):
            return f"lambda{space(1)}{unparse(args)}{space(1)}:{space()}{unparse(body)}"
        case ast.List(elts=elts):
            return (
                f"[{space()}" + f",{space()}".join(unparse(elt, True) for elt in elts) + f"{space()}]"
            )
        case ast.ListComp(elt=elt, generators=generators):
            return (
                f"[{space()}"
                + f"{unparse(elt)} "
                + f"{space(1)}".join(map(unparse, generators))
                + f"{space()}]"
            )
        case ast.Match(subject=subject, cases=cases):
            return "\n".join([f"match {unparse(subject)}:", *indent(cases, randrange(2, 5))])
        case ast.Module(body=body):
            return "\n".join(indent(body, 0))
        case ast.Name(id=id_):
            return id_
        case ast.NamedExpr(target=target, value=value):
            return f"({unparse(target)}{space()}:={space()}{unparse(value)})"
        case ast.Nonlocal(names=names):
            return f"nonlocal{space(1)}{f',{space()}'.join(map(unparse, names))};"
        case ast.Pass():
            return f"pass{space()};"
        case ast.Raise(exc=exc, cause=cause):
            return (
                f"raise{space(1)}{unparse(exc)}"
                + (f"{space(1)}from{space(1)}{unparse(cause)}" if cause else "")
                + f"{space()};"
            )
        case ast.Return(value=value):
            return f"return{space(1)}{unparse(value)};"
        case ast.Set(elts=elts):
            return "{" + space() + ", ".join(unparse(elt, True) for elt in elts) + space() + "}"
        case ast.SetComp(elt=elt, generators=generators):
            return (
                "{"
                + space()
                + f"{unparse(elt)}{space(1)}"
                + f"{space(1)}".join(map(unparse, generators))
                + space()
                + "}"
            )
        case ast.Slice(lower=lower, upper=upper, step=step):
            s = f"{lower or ''}{space()}:{space()}{upper or ''}{space()}:{space()}{step or ''}"
            return ":" if s.replace(" ", "") == "::" else s
        case ast.Starred(value=value):
            return f"*{space()}{parenthesize(value)}"
        case ast.Subscript(value=value, slice=slice_):
            return (
                f"{(parenthesize if precedences[type(value)] < precedences[ast.Subscript] else unparse)(value)}{space()}"
                f"[{space()}{unparse(slice_, True)}{space()}]"
            )
        case ast.Try(body=body, handlers=handlers, orelse=orelse, finalbody=finalbody):
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
        case ast.Tuple(elts=elts):
            return (
                f"({space()}" + f",{space()}".join(unparse(elt, True) for elt in elts) + f"{space()})"
            )
        case ast.UnaryOp(op=op, operand=operand):
            par_op = (
                precedences[type(operand.op)]
                if isinstance(operand, (ast.BinOp, ast.BoolOp))
                else (precedences[type(operand)])
            ) < precedences[op]
            return f"{op_strs[type(op)]}{space()}{(parenthesize if par_op else unparse)(operand)}"
        case ast.While(test=test, body=body, orelse=orelse):
            s = [
                f"while{space(1)}{unparse(test)}{space()}:",
                *indent(body, randrange(2, 5)),
            ]
            if orelse:
                s.append(f"else{space()}:")
                s.extend(indent(orelse, randrange(2, 5)))
            return "\n".join(s)
        case ast.With(items=items, body=body):
            return "\n".join(
                [
                    f"with{space(1)}{', '.join(map(unparse, items))}{space()}:",
                    *indent(body, randrange(2, 5)),
                ]
            )
        case ast.Yield(value=value):
            return f"yield{space(1)}{unparse(value)}"
        case ast.YieldFrom(value=value):
            return f"yield{space(1)}from{space(1)}{unparse(value)}"

        case ast.arg(arg=arg, annotation=annotation):
            return arg + (f":{space()}{unparse(annotation)}" if annotation else "")
        case ast.arguments(
            posonlyargs=posonlyargs,  # type: ignore
            args=args,
            vararg=vararg,
            kwonlyargs=kwonlyargs,
            kw_defaults=kw_defaults,
            kwarg=kwarg,
            defaults=defaults,
        ):
            s = ""
            first = True
            all_args = posonlyargs + args
            defaults = [None] * (len(all_args) - len(defaults)) + defaults
            for index, elements in enumerate(zip(all_args, defaults), 1):
                a, d = elements
                if first:
                    first = False
                else:
                    s += f",{space()}"
                s += unparse(a, nl_able)
                if d:
                    s += "=" + unparse(d, nl_able)
                if index == len(posonlyargs):
                    s += f",{space()}/"

            if vararg or kwonlyargs:
                if first:
                    first = False
                else:
                    s += f",{space()}"
                s += "*"
                if vararg:
                    s += unparse(vararg.arg, nl_able)
                    if vararg.annotation:
                        s += f":{space()}" + unparse(vararg.annotation, nl_able)

            if kwonlyargs:
                for a, d in zip(kwonlyargs, kw_defaults):
                    s += f",{space()}" + unparse(a, nl_able)
                    if d:
                        s += f"{space()}={space()}{unparse(d, nl_able)}"
            if kwarg:
                if not first:
                    s += f",{space()}"
                s += f"**{space()}{unparse(kwarg.arg, nl_able)}"
                if kwarg.annotation:
                    s += f":{space()}{unparse(kwarg.annotation, nl_able)}"
            return s
        case ast.keyword(arg=arg, value=value):
            return (f"{arg}{space()}={space()}" if arg else f"**{space()}") + unparse(
                value
            )
        case ast.comprehension(target=target, iter=iter_, ifs=ifs, is_async=is_async):
            return (
                ["", f"async{space(1)}"][is_async]
                + f"for{space(1)}{unparse(target)}{space(1)}in{space(1)}{unparse(iter_)}"
                + (f"{space(1)}" if ifs else "")
                + f"{space(1)}".join(f"if {unparse(if_)}" for if_ in ifs)
            )
        case ast.match_case(pattern=pattern, body=body):
            return "\n".join([
                f"case{space(1)}{unparse(pattern)}{space()}:",
                *indent(body, randrange(2, 5)),
            ])
        case ast.withitem(context_expr=context_expr, optional_vars=optional_vars):
            return f"{unparse(context_expr)}" + (
                f"{space(1)}as{space(1)}{unparse(optional_vars)}"
                if optional_vars
                else ""
            )
        case _:
            print(f"failed to format {ast.dump(node)}, falling back to ast.unparse")
            return ast.unparse(node)


def blurplify(src: str) -> str:
    """Format the given source code in accordance with PEP 9001."""
    src_ast = ast.parse(src)
    return invert_indents("# coding=UTF-8-NOBOM\n" + unparse(src_ast))
