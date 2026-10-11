
from dataclasses import dataclass
import json
from pathlib import Path

from core.ir.ast import ASTNode, Case, Condition, Text, Indent, Scope, build_node


@dataclass
class ContractDoc:
    subchecks: dict[str, ASTNode]
    assumption: ASTNode
    guarantee: ASTNode


def _load_contract_doc(contract_json: dict) -> ContractDoc:
    return ContractDoc(
        subchecks={
            checkname: build_node(ast_node)
            for checkname, ast_node in contract_json["subchecks"].items()
        },
        assumption=build_node(contract_json["assumption"]),
        guarantee=build_node(contract_json["guarantee"]),
    )

# tmp
# 不拆解 case，直接输出 grarantee 整个式子
def _render_grarantee_case(doc: ContractDoc) -> str:
    assumption = doc.assumption.render(ctx={"subchecks": doc.subchecks})
    guarantee = doc.guarantee.render(ctx={"subchecks": doc.subchecks})
    return f"""
void case_0() {{
    // # Assumption
    // {assumption}
    // # Guarantee
    // {guarantee}
}}
"""


def _split_cases(doc: ContractDoc) -> list[Case]:

    assumption_cases = doc.assumption.split_cases(
        ctx={
        "subchecks": doc.subchecks,
            "scope_stack": ["assumption"]  # <- tmp
        }
    )

    if len(assumption_cases) != 1:
        raise NotImplementedError()
    assumption_case = assumption_cases[0]

    guarantee_cases = doc.guarantee.split_cases(
        ctx={
            "subchecks": doc.subchecks,
            "scope_stack": ["guarantee"]
        }
    )

    cases = []
    for guarantee_case in guarantee_cases:
        cases.append(
            Case(steps=[
                Scope(kind="assumption"),
                Text(text=f"# Assumption"),
                *assumption_case.steps,
                Scope(kind="end"),
                Scope(kind="guarantee"),
                Text(text=f"# Guarantee"),
                *guarantee_case.steps,
                Scope(kind="end"),
            ])
        )
    return cases


def _case_steps(case: Case) -> list[str]:
    lines = []
    indent_level = 0
    indent = ""
    scope_stack: list[str] = []
    for step in case.steps:
        match step:
            case Scope(kind="end"):
                scope_stack.pop()
            case Scope(kind=kind):
                scope_stack.append(kind)

            case Condition(expr=expr):
                match scope_stack[-1]:
                    case "assumption":
                        action = "assume"
                    case "guarantee":
                        action = "assert"
                    case "if-cond":
                        if scope_stack[0] == "guarantee":
                            action = "assume"
                        else:
                            raise NotImplementedError("Assumption 语境暂不支持 if-cond")
                    case _:
                        assert False
                lines.append(f"    // {indent}{action} {expr}")

            case Text(text=text):
                lines.append(f"    // {indent}{text}")

            case Indent(level=level):
                indent_level += level
                indent = "  " * indent_level
                assert indent_level >= 0

            case _:
                assert False

    assert not scope_stack
    return lines


def _make_template(cases: list[Case]) -> str:
    lines = [""]
    w = len(str(len(cases))) if cases else 1
    for i, case in enumerate(cases, start=1):
        lines.append(f"void case_{i:0{w}d}(void) " + "{")
        lines.extend(_case_steps(case))
        lines.append("}")
        lines.append("")
    lines.append("")
    lines.append("void case_nf(void) {")
    lines.append("")
    lines.append("}")
    lines.append("")

    tmpl_text = "\n".join(lines)
    return tmpl_text


def make_cases_tmpl(ir_dir: Path) -> str:
    with open(ir_dir / "contract.json", encoding="utf-8") as f:
        contract_json = json.load(f)
    contract_doc = _load_contract_doc(contract_json)
    cases = _split_cases(contract_doc)
    tmpl_text = _make_template(cases)
    return tmpl_text
