import json
from pathlib import Path

_MAX_ERRORS = 50


class _ErrorLimitReached(Exception):
    pass

_UNARY_KINDS  = frozenset({"not", "neg", "bit_not"})
_CHAIN_KINDS  = frozenset({"and", "or", "le", "ge", "lt", "gt", "eq", "add", "mul"})
_BINARY_KINDS = frozenset({"sub", "div", "mod", "bit_and", "bit_or", "bit_xor", "bit_shl", "bit_shr", "neq", "implies"})
_ALL_KINDS    = _UNARY_KINDS | _CHAIN_KINDS | _BINARY_KINDS | frozenset(
                {"val", "var", "if", "forall", "exists", "call", "subcheck", "text", "latex"})


class Checker:
    def __init__(self, s: str):
        self.s = s
        self.max_errors = _MAX_ERRORS
        self.errors: list[str] = []
        self.subcheck_names: set[str] = set()
        self.path: list[str | int] = []

    def err(self, msg: str):
        ss = []
        path = "$"
        for p in self.path:
            if isinstance(p, int):
                path += f"[{p}]"
            else:
                path += f".{p}"
        ss.append(path)
        ss.append(':')
        ss.append(msg)
        self.errors.append(' '.join(ss))
        if len(self.errors) >= self.max_errors:
            self.errors.append(f"JSON AST 发现多处错误，中止检查")
            raise _ErrorLimitReached

    def enter_node(self, node):
        self.path.append("<AST-node:?>")
        try:
            if not isinstance(node, dict):
                self.err(f"应是 object，但实际是 {type(node).__name__}")
                return
            if not self.check_field(node, "kind", check_type=str):
                return
            kind = node["kind"]
            self.path.pop()
            self.path.append(f"<AST-node:{kind}>")
            if kind not in _ALL_KINDS:
                self.err(f"不支持节点类型 {kind!r}")
                return
            yield kind
        finally:
            self.path.pop()

    def check_type(self, value, *, check_type: type | tuple[type]) -> bool:
        types = check_type if isinstance(check_type, tuple) else (check_type,)
        if isinstance(value, types):
            return True
        T = {int: "int", float: "float", bool: "bool", str: "str", dict: "object", list: "array", type(None): "null"}
        self.err(f"应是 {' 或 '.join(T.get(t, t.__name__) for t in types)}，但实际是 {T.get(type(value), type(value).__name__)}")
        return False

    def check_field(self, d: dict, field: str, *, check_type: type | tuple[type], missing_ok: bool = False) -> bool:
        if field not in d:
            if not missing_ok:
                self.err(f"缺少字段：{field}")
            return False
        self.path.append(field)
        try:
            return self.check_type(d[field], check_type=check_type)
        finally:
            self.path.pop()

    def enter_field(self, d: dict, fields: str | list[str], *, check_type: type | tuple[type], missing_ok: bool = False):
        if isinstance(fields, str):
            fields = [fields]
        for field in fields:
            if field not in d:
                if not missing_ok:
                    self.err(f"缺少字段：{field}")
                continue
            self.path.append(field)
            try:
                if self.check_type(d[field], check_type=check_type):
                    yield d[field]
            finally:
                self.path.pop()

    def enter_items(self, collection: dict | list):
        if isinstance(collection, dict):
            iter_ = collection.items()
        elif isinstance(collection, list):
            iter_ = enumerate(collection)
        else:
            assert False

        for key_or_idx, val in iter_:
            self.path.append(key_or_idx)
            try:
                yield key_or_idx, val
            finally:
                self.path.pop()


    def check(self) -> list[str]:
        try:
            self._check()
        except _ErrorLimitReached:
            pass

        return self.errors

    def _check(self):
        try:
            root = json.loads(self.s)
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON 解析失败：{e}")
            return
        if not isinstance(root, dict):
            self.errors.append("根节点必须是 JSON Object")
            return

        self.check_field(root, "version", check_type=str)

        for subchecks in self.enter_field(root, "subchecks", check_type=dict):
            self.subcheck_names = set(subchecks.keys())
            for _, node in self.enter_items(subchecks):
                self.check_node(node)

        for assumption in self.enter_field(root, "assumption", check_type=dict):
            self.check_node(assumption)
        for guarantee in self.enter_field(root, "guarantee", check_type=dict):
            self.check_node(guarantee)

    def check_node(self, node):
        for kind in self.enter_node(node):
            if kind in _UNARY_KINDS:
                self.check_unary_node(node)
            elif kind in _BINARY_KINDS:
                self.check_binary_node(node)
            elif kind in _CHAIN_KINDS:
                self.check_binary_node(node, allow_multi_args=True)
            else:
                {
                    "val":      self.check_val_node,
                    "var":      self.check_var_node,
                    "if":       self.check_if_node,
                    "forall":   self.check_quantifier_node,
                    "exists":   self.check_quantifier_node,
                    "call":     self.check_call_node,
                    "subcheck": self.check_subcheck_node,
                    "text":     self.check_text_node,
                    "latex":    self.check_text_node,
                }[kind](node)

    def check_val_node(self, node: dict):
        self.check_field(node, "val", check_type=str)
        self.check_field(node, "type", check_type=str, missing_ok=True)

    def check_var_node(self, node: dict):
        self.check_field(node, "name", check_type=str)

    def check_unary_node(self, node: dict):
        for arg in self.enter_field(node, "arg", check_type=dict):
            self.check_node(arg)

    def check_binary_node(self, node: dict, *, allow_multi_args: bool = False):
        if allow_multi_args and "args" in node:
            if "lhs" in node or "rhs" in node:
                self.err("不允许同时含有 'args' 和 'lhs'/'rhs'")
                return

            for args in self.enter_field(node, "args", check_type=list):
                if len(args) < 2:
                    self.err("'args' 长度必须 >= 2")
                else:
                    for _, arg in self.enter_items(args):
                        self.check_node(arg)
        else:
            for val in self.enter_field(node, ["lhs", "rhs"], check_type=dict):
                self.check_node(val)

    def check_if_node(self, node: dict):
        for val in self.enter_field(node, ["cond", "then"], check_type=dict):
            self.check_node(val)
        for val in self.enter_field(node, "else", check_type=dict, missing_ok=True):
            self.check_node(val)

    def check_quantifier_node(self, node: dict):
        for vars_ in self.enter_field(node, "vars", check_type=list):
            if len(vars_) == 0:
                self.err("必须是非空列表")
            else:
                for _, v in self.enter_items(vars_):
                    if not self.check_type(v, check_type=dict):
                        continue
                    self.check_field(v, "name", check_type=str)
                    self.check_field(v, "type", check_type=str, missing_ok=True)
                    self.check_field(v, "range", check_type=str, missing_ok=True)
        for body in self.enter_field(node, "body", check_type=dict):
            self.check_node(body)

    def check_call_node(self, node: dict):
        self.check_field(node, "fn", check_type=str)
        for args in self.enter_field(node, "args", check_type=list, missing_ok=True):
            for _, arg in self.enter_items(args):
                self.check_node(arg)
        for kwargs in self.enter_field(node, "kwargs", check_type=dict, missing_ok=True):
            for _, val in self.enter_items(kwargs):
                self.check_node(val)

    def check_subcheck_node(self, node: dict):
        for name in self.enter_field(node, "name", check_type=str):
            if name not in self.subcheck_names:
                self.err(f"引用了未定义的 subcheck `{name}`")

    def check_text_node(self, node: dict):
        self.check_field(node, "text", check_type=str)


def check_ast(ir_dir: Path) -> list[str]:
    ast_path = ir_dir / "contract.json"
    if not ast_path.is_file():
        return ["contract.json 文件不存在"]

    try:
        text = ast_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as e:
        return [f"contract.json 读取失败：{e}"]

    return Checker(text).check()
