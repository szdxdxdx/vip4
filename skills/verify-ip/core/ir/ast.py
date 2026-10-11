
from dataclasses import dataclass
from typing import Literal


class Step:
    pass


@dataclass
class Case:
    steps: list[Step]


@dataclass
class Scope(Step):
    kind: Literal["assumption", "guarantee", "if-cond", "end"]


@dataclass
class Condition(Step):
    expr: str


@dataclass
class Text(Step):
    text: str


@dataclass
class Indent(Step):
    level: int


class ASTNode:
    def split_cases(self, ctx: dict) -> list[Case]:
        return [
            Case(steps=[
                Condition(expr=self.render(ctx))
            ])
        ]

    def render(self, ctx: dict) -> str:
        raise NotImplementedError()


class ValNode(ASTNode):
    def __init__(self, val: str):
        self.val = val

    @staticmethod
    def build_node(data: dict):
        val = data["val"]
        return ValNode(val)

    def render(self, ctx: dict) -> str:
        # NOTE 如果 val 是一个表达式，例如 1+2，则需要加括号，防止 C 运算符优先级问题
        #   mul(val(1+2), val(3)) -> ((1+2) * (3))
        # TODO 但如果 val 是一个元组怎么办？或者 val 是单独的一个数怎么办？加括号就太累赘了
        return f"({self.val})"


class VarNode(ASTNode):
    def __init__(self, name: str):
        self.name = name

    @staticmethod
    def build_node(data: dict):
        name = data["name"]
        return VarNode(name)

    def render(self, ctx: dict) -> str:
        return self.name


class UnaryOpNode(ASTNode):
    operator = ""

    def __init__(self, arg: ASTNode):
        self.arg = arg

    @classmethod
    def build_node(cls, data: dict):
        arg = build_node(data["arg"])
        return cls(arg)

    def render(self, ctx: dict) -> str:
        return f"( {self.operator}{self.arg.render(ctx)})"


class BinaryOpNode(ASTNode):
    operator: str
    allow_multi_args = False

    def __init__(self, args: list[ASTNode]):
        self.args = args

    @classmethod
    def build_node(cls, data: dict):
        if cls.allow_multi_args and "args" in data:
            assert len(data["args"]) >= 2
            args = [build_node(node) for node in data["args"]]
        else:
            lhs = build_node(data["lhs"])
            rhs = build_node(data["rhs"])
            args = [lhs, rhs]
        return cls(args)

    def render(self, ctx: dict) -> str:
        return "(" + (f" {self.operator} ".join(arg.render(ctx) for arg in self.args)) + ")"


class AndNode(BinaryOpNode):
    operator = "&&"
    allow_multi_args = True

    def split_cases(self, ctx: dict) -> list[Case]:
        combine_steps: list[Step] = []
        multi_cases: list[Case] = []

        for arg in self.args:
            cases = arg.split_cases(ctx)
            if len(cases) == 1:
                combine_steps.extend(cases[0].steps)
            else:
                multi_cases.extend(case for case in cases if case)

        cases = [Case(steps=combine_steps)] if combine_steps else []
        cases.extend(multi_cases)
        return cases


class OrNode(BinaryOpNode):
    operator = "||"
    allow_multi_args = True

    # tmp
    # 目前 CBMC 工作流不支持 guarantee 是一个析取式，因此暂不实现
    # 这里有一个初步想法：若 guarentee 是一个析取式，则拆分每一项对应一个 case
    def split_cases__(self, ctx: dict) -> list[Case]:
        raise NotImplementedError()
        if len(ctx["scope_stack"]) == 1 and ctx["scope_stack"][0] == "guarantee":
            ctx["scope_stack"].append("or")
            cases: list[Case] = []
            for arg in self.args:
                cases.extend(arg.split_cases(ctx))
            ctx["scope_stack"].pop()
            return cases
        else:
            return super().split_cases(ctx)


class NotNode(UnaryOpNode):
    operator = "!"


def build_implies_node(data: dict):
    lhs = build_node(data["lhs"])
    rhs = build_node(data["rhs"])
    return OrNode([NotNode(lhs), rhs])


class IfNode(ASTNode):
    def __init__(self, cond: ASTNode, then: ASTNode, else_: ASTNode | None):
        self.cond = cond
        self.then = then
        self.else_ = else_

    @staticmethod
    def build_node(data: dict):
        cond = build_node(data["cond"])
        then = build_node(data["then"])
        else_ = build_node(data["else"]) if "else" in data else None
        return IfNode(cond, then, else_)

    def split_cases(self, ctx: dict) -> list[Case]:
        cases: list[Case] = []
        cond = Condition(expr=self.cond.render(ctx))
        for case_ in self.then.split_cases(ctx):
            cases.append(
                Case(steps=[
                    Text(text="# if then-branch {"),
                    Indent(level=1),
                    Scope(kind="if-cond"),
                    cond,
                    Scope(kind="end"),
                    *case_.steps,
                    Indent(level=-1),
                    Text(text="}"),
                ])
            )
        if self.else_:
            neg_cond = Condition(expr=NotNode(self.cond).render(ctx))
            for case_ in self.else_.split_cases(ctx):
                cases.append(
                    Case(steps=[
                        Text(text="# if else-branch {"),
                        Indent(level=1),
                        Scope(kind="if-cond"),
                        neg_cond,
                        Scope(kind="end"),
                        *case_.steps,
                        Indent(level=-1),
                        Text(text="}"),
                    ])
                )
        return cases

    def render(self, ctx: dict) -> str:
        if self.else_:
            return f"( if( {self.cond.render(ctx)} )then{{ {self.then.render(ctx)} }}else{{ {self.else_.render(ctx)} }})"
        else:
            return f"( if( {self.cond.render(ctx)} )then{{ {self.then.render(ctx)} }})"
        if self.else_:
            expr = OrNode([
                AndNode([self.cond, self.then]),
                AndNode([NotNode(self.cond), self.else_])
            ])
        else:
            expr = OrNode([
                NotNode(self.cond),
                AndNode([self.cond, self.then])
            ])
        return expr.render(ctx)


class QuantifierNode(ASTNode):
    quantifier_name: str

    def __init__(self, vars: list[dict], body: ASTNode):
        self.vars = vars
        self.body = body

    @classmethod
    def build_node(cls, data: dict):
        vars_ = data["vars"]
        body = build_node(data["body"])
        return cls(vars_, body)

    def _vars_str(self) -> list[str]:
        # { var: x, type: T, range: ... }
        vars_str = []
        for var_ in self.vars:
            ss = [f'var: {var_["name"]}']
            if var_type := var_.get("type"):
                ss.append(f'type: {var_type}')
            if var_range := var_.get("range"):
                ss.append(f'range: "{var_range}"')
            vars_str.append("; ".join(ss))
        return vars_str

    def render(self, ctx: dict) -> str:
        vars_str = '. '.join(self._vars_str())
        return ("( "
            f"{self.quantifier_name}( {vars_str} )" + "{"
                f"{self.body.render(ctx)}"
            "}"
        " )")


class ForAllNode(QuantifierNode):
    quantifier_name = "forall"

    def split_cases(self, ctx: dict) -> list[Case]:
        vars_str = self._vars_str()

        if len(vars_str) == 1:
            begin = [
                Text(text=f"{self.quantifier_name} ( {vars_str[0]} ) " + "{"),
                Indent(level=1),
            ]
            end = [
                Indent(level=-1),
                Text(text="}"),
            ]
        else:
            begin = [
                Text(text=f"{self.quantifier_name} ("),
                Indent(level=1),
                *(Text(text=var_str) for var_str in vars_str),
                Indent(level=-1),
                Text(text=") {"),
                Indent(level=1),
            ]
            end = [
                Indent(level=-1),
                Text(text="}"),
            ]

        cases = []
        for body_case in self.body.split_cases(ctx):
            cases.append(
                Case(steps=[
                    *begin,
                    *body_case.steps,
                    *end
                ])
            )
        return cases


class ExistsNode(QuantifierNode):
    quantifier_name = "exists"

    def split_cases(self, ctx: dict) -> list[Case]:
        vars_str = self._vars_str()
        if len(vars_str) == 1:
            begin = [
                Text(text=f"{self.quantifier_name} ( {vars_str[0]} ) " + "{"),
                Indent(level=1),
            ]
        else:
            begin = [
                Text(text=f"{self.quantifier_name} ("),
                Indent(level=1),
                *(Text(text=var_str) for var_str in vars_str),
                Indent(level=-1),
                Text(text=") {"),
                Indent(level=1),
            ]
        end = [
            Indent(level=-1),
            Text(text="}"),
        ]

        return [Case(steps=[
            *begin,
            Condition(expr=self.body.render(ctx)),
            *end
        ])]


class AddNode(BinaryOpNode):
    operator = "+"
    allow_multi_args = True


class SubNode(BinaryOpNode):
    operator = "-"


class NegNode(UnaryOpNode):
    operator = "-"


class MulNode(BinaryOpNode):
    operator = "*"
    allow_multi_args = True


class DivNode(BinaryOpNode):
    operator = "/"


class ModNode(BinaryOpNode):
    operator = "%"


class GeNode(BinaryOpNode):
    operator = ">="
    allow_multi_args = True


class GtNode(BinaryOpNode):
    operator = ">"
    allow_multi_args = True


class LeNode(BinaryOpNode):
    operator = "<="
    allow_multi_args = True


class LtNode(BinaryOpNode):
    operator = "<"
    allow_multi_args = True


class EqNode(BinaryOpNode):
    operator = "=="
    allow_multi_args = True


class NeqNode(BinaryOpNode):
    operator = "!="


class BitAndNode(BinaryOpNode):
    operator = "&"


class BitOrNode(BinaryOpNode):
    operator = "|"


class BitNotNode(UnaryOpNode):
    operator = "~"


class BitXorNode(BinaryOpNode):
    operator = "^"


class BitShlNode(BinaryOpNode):
    operator = "<<"


class BitShrNode(BinaryOpNode):
    operator = ">>"


class CallNode(ASTNode):
    def __init__(self, fn: str, args: list[ASTNode], kwargs: dict[str, ASTNode]):
        self.fn = fn
        self.args = args 
        self.kwargs = kwargs

    @staticmethod
    def build_node(data: dict):
        fn = data["fn"]
        args = [build_node(arg) for arg in data.get("args", [])]
        kwargs = {key: build_node(kwarg) for key, kwarg in data.get("kwargs", {}).items()}
        return CallNode(fn, args, kwargs)

    def render(self, ctx: dict) -> str:
        parts = [arg.render(ctx) for arg in self.args]
        parts.extend(f"{key}={value.render(ctx)}" for key, value in self.kwargs.items())
        return f"{self.fn}({', '.join(parts)})"


class SubcheckNode(ASTNode):
    def __init__(self, name: str):
        self.name = name

    @staticmethod
    def build_node(data: dict):
        name = data["name"]
        return SubcheckNode(name)

    def split_cases(self, ctx: dict) -> list[Case]:
        subcheck: ASTNode = ctx["subchecks"][self.name]
        cases = []
        for case in subcheck.split_cases(ctx):
            cases.append(
                Case(steps=[
                    Text(text=f"# Subcheck {self.name}"),
                    *case.steps,
                ])
            )
        return cases

    def render(self, ctx: dict) -> str:
        subcheck: ASTNode = ctx["subchecks"][self.name]
        return subcheck.render(ctx)


class TextNode(ASTNode):
    def __init__(self, text: str):
        self.text = text

    @staticmethod
    def build_node(data: dict):
        text = data["text"]
        return TextNode(text)

    def render(self, ctx: dict) -> str:
        return f'("{self.text}")'


class LaTeXNode(TextNode):
    def __init__(self, text: str):
        self.text = text

    @staticmethod
    def build_node(data: dict):
        text = data["text"]
        return LaTeXNode(text)

    def render(self, ctx: dict) -> str:
        return f"(latex```{self.text}```)"


BUILDERS = {
    "val": ValNode.build_node,
    "var": VarNode.build_node,

    "and": AndNode.build_node,
    "or": OrNode.build_node,
    "not": NotNode.build_node,
    "implies": build_implies_node,

    "if": IfNode.build_node,

    "exists": ExistsNode.build_node,
    "forall": ForAllNode.build_node,

    "add": AddNode.build_node,
    "sub": SubNode.build_node,
    "neg": NegNode.build_node,
    "mul": MulNode.build_node,
    "div": DivNode.build_node,
    "mod": ModNode.build_node,

    "bit_and": BitAndNode.build_node,
    "bit_or": BitOrNode.build_node,
    "bit_not": BitNotNode.build_node,
    "bit_xor": BitXorNode.build_node,
    "bit_shl": BitShlNode.build_node,
    "bit_shr": BitShrNode.build_node,

    "ge": GeNode.build_node,
    "gt": GtNode.build_node,
    "le": LeNode.build_node,
    "lt": LtNode.build_node,
    "eq": EqNode.build_node,
    "neq": NeqNode.build_node,

    "call": CallNode.build_node,

    "subcheck": SubcheckNode.build_node,

    "text": TextNode.build_node,
    "latex": LaTeXNode.build_node,
}


def build_node(node_data: dict) -> ASTNode:
    kind = node_data["kind"]
    if kind not in BUILDERS:
        raise NotImplementedError(f"暂不支持节点类型 {kind}")
    else:
        node_builder = BUILDERS[kind]
        return node_builder(node_data)
