"""Transform literal typing calls without changing their string contents."""

import ast
import copy


def fix_less_than_typing(command: str) -> str:
    class RewriteTyping(ast.NodeTransformer):
        changed = False

        def visit_Expr(self, node):
            node = self.generic_visit(node)
            call = node.value
            if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name) and call.func.value.id == "pyautogui"
                    and call.args and isinstance(call.args[0], ast.Constant)
                    and isinstance(call.args[0].value, str)):
                return node
            text = call.args[0].value
            if call.func.attr == "press" and text == "<" and len(call.args) == 1 and not call.keywords:
                self.changed = True
                return self.hotkey(node)
            if call.func.attr not in ("typewrite", "write") or "<" not in text:
                return node
            # Splitting must not evaluate dynamic arguments more than once.
            if any(not isinstance(arg, ast.Constant) for arg in call.args[1:]) or any(
                keyword.arg is None or not isinstance(keyword.value, ast.Constant)
                for keyword in call.keywords
            ):
                return node
            self.changed = True
            statements = []
            for index, part in enumerate(text.split("<")):
                if index:
                    statements.append(self.hotkey(node))
                if part:
                    segment = copy.deepcopy(node)
                    segment.value.args[0] = ast.Constant(value=part)
                    statements.append(segment)
            return statements

        @staticmethod
        def hotkey(node):
            return ast.copy_location(ast.Expr(value=ast.Call(
                func=ast.Attribute(value=ast.Name(id="pyautogui", ctx=ast.Load()), attr="hotkey", ctx=ast.Load()),
                args=[ast.Constant(value="shift"), ast.Constant(value=",")], keywords=[],
            )), node)

    try:
        tree = ast.parse(command)
    except SyntaxError:
        return command
    transformer = RewriteTyping()
    tree = transformer.visit(tree)
    return ast.unparse(ast.fix_missing_locations(tree)) if transformer.changed else command
