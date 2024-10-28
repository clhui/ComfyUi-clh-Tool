import ast
import math
import random
import operator as op
from typing import Dict, List, Optional, Tuple, Any

from comfy_execution.graph_utils import GraphBuilder


# Hack: string type that is always equal in not equal comparisons
class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False


# Our any instance wants to be a wildcard string
any = AnyType("*")

operators = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Pow: op.pow,
    ast.BitXor: op.xor,
    ast.USub: op.neg,
    ast.Mod: op.mod,
    ast.BitAnd: op.and_,
    ast.BitOr: op.or_,
    ast.Invert: op.invert,
    ast.And: lambda a, b: 1 if a and b else 0,
    ast.Or: lambda a, b: 1 if a or b else 0,
    ast.Not: lambda a: 0 if a else 1,
    ast.RShift: op.rshift,
    ast.LShift: op.lshift
}

# TODO: restructure args to provide more info, generate hint based on args to save duplication
functions = {
    "round": {
        "args": (1, 2),
        "call": lambda a, b=None: round(a, b),
        "hint": "number, dp? = 0"
    },
    "ceil": {
        "args": (1, 1),
        "call": lambda a: math.ceil(a),
        "hint": "number"
    },
    "floor": {
        "args": (1, 1),
        "call": lambda a: math.floor(a),
        "hint": "number"
    },
    "min": {
        "args": (2, None),
        "call": lambda *args: min(*args),
        "hint": "...numbers"
    },
    "max": {
        "args": (2, None),
        "call": lambda *args: max(*args),
        "hint": "...numbers"
    },
    "randomint": {
        "args": (2, 2),
        "call": lambda a, b: random.randint(a, b),
        "hint": "min, max"
    },
    "randomchoice": {
        "args": (2, None),
        "call": lambda *args: random.choice(args),
        "hint": "...numbers"
    },
    "sqrt": {
        "args": (1, 1),
        "call": lambda a: math.sqrt(a),
        "hint": "number"
    },
    "int": {
        "args": (1, 1),
        "call": lambda a=None: int(a),
        "hint": "number"
    },
    "iif": {
        "args": (3, 3),
        "call": lambda a, b, c=None: b if a else c,
        "hint": "value, truepart, falsepart"
    },
}

autocompleteWords = list({
                             "text": x,
                             "value": f"{x}()",
                             "showValue": False,
                             "hint": f"{functions[x]['hint']}",
                             "caretOffset": -1
                         } for x in functions.keys())


def validate_list_args(args: Dict[str, List[Any]]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Checks that if there are multiple arguments, they are all the same length or 1
    :param args:
    :return: Tuple (Status, mismatched_key_1, mismatched_key_2)
    """
    # Only have 1 arg
    if len(args) == 1:
        return True, None, None

    len_to_match = None
    matched_arg_name = None
    for arg_name, arg in args.items():
        if arg_name == 'self':
            # self is in locals()
            continue

        if len(arg) != 1:
            if len_to_match is None:
                len_to_match = len(arg)
                matched_arg_name = arg_name
            elif len(arg) != len_to_match:
                return False, arg_name, matched_arg_name

    return True, None, None


MAX_FLOW_NUM = 5

lazy_options = {"lazy": True}


class MathExpression_clh:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "expression": ("STRING", {"multiline": True, "dynamicPrompts": False, "pysssss.autocomplete": {
                    "words": autocompleteWords,
                    "separator": "",
                    "default": "aram0+param1+param2",
                    "height": 40
                }}),
                "result_to_label": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                # "a": (any, ),
                # "b": (any,),
                # "c": (any, ),
                # "initial_value%d" % i: (any, {"rawLink": True,"lazy": True}) for i in range(1, MAX_FLOW_NUM)
            },
            "hidden": {
                "extra_pnginfo": "EXTRA_PNGINFO",
                "prompt": "PROMPT"},
        }

        for i in range(MAX_FLOW_NUM):
            inputs["optional"]["param%d" % i] = (any, {"default": 0})
        return inputs

    RETURN_TYPES = ("INT", "FLOAT","STRING",)
    FUNCTION = "evaluate"
    CATEGORY = "simpleTool_clh"
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(s, expression, prompt, extra_pnginfo, **kwargs):
        if "random" in expression:
            return float("nan")
        return expression

    def get_widget_value(self, extra_pnginfo, prompt, node_name, widget_name):
        workflow = extra_pnginfo["workflow"] if "workflow" in extra_pnginfo else {"nodes": []}
        node_id = None
        for node in workflow["nodes"]:
            name = node["type"]
            if "properties" in node:
                if "Node name for S&R" in node["properties"]:
                    name = node["properties"]["Node name for S&R"]
            if name == node_name:
                node_id = node["id"]
                break
            if "title" in node:
                name = node["title"]
            if name == node_name:
                node_id = node["id"]
                break
        if node_id is not None:
            values = prompt[str(node_id)]
            if "inputs" in values:
                if widget_name in values["inputs"]:
                    value = values["inputs"][widget_name]
                    if isinstance(value, list):
                        raise ValueError(
                            "Converted widgets are not supported via named reference, use the inputs instead.")
                    return value
            raise NameError(f"Widget not found: {node_name}.{widget_name}")
        raise NameError(f"Node not found: {node_name}.{widget_name}")

    def get_size(self, target, property):
        if isinstance(target, dict) and "samples" in target:
            # Latent
            if property == "width":
                return target["samples"].shape[3] * 8
            return target["samples"].shape[2] * 8
        else:
            # Image
            if property == "width":
                return target.shape[2]
            return target.shape[1]

    # def evaluate(self, expression, prompt, extra_pnginfo={}, a=None, b=None, c=None):
    def evaluate(self, expression, prompt, extra_pnginfo={}, **initial_values):
        expression = expression.replace('\n', ' ').replace('\r', '')
        node = ast.parse(expression, mode='eval').body

        # bodylookup = {
        #     "initial_value%d" % i: initial_values[i] for i in range(1, MAX_FLOW_NUM)
        # }
        lookup = initial_values

        def eval_op(node, l, r):
            l = eval_expr(l)
            r = eval_expr(r)
            l = l if isinstance(l, int) else float(l)
            r = r if isinstance(r, int) else float(r)
            return operators[type(node.op)](l, r)

        def eval_expr(node):
            if isinstance(node, ast.Constant) or isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.BinOp):
                return eval_op(node, node.left, node.right)
            elif isinstance(node, ast.BoolOp):
                return eval_op(node, node.values[0], node.values[1])
            elif isinstance(node, ast.UnaryOp):
                return operators[type(node.op)](eval_expr(node.operand))
            elif isinstance(node, ast.Attribute):
                if node.value.id in lookup:
                    if node.attr == "width" or node.attr == "height":
                        return self.get_size(lookup[node.value.id], node.attr)

                return self.get_widget_value(extra_pnginfo, prompt, node.value.id, node.attr)
            elif isinstance(node, ast.Name):
                if node.id in lookup:
                    val = lookup[node.id]
                    if isinstance(val, (int, float, complex)):
                        return val
                    else:
                        raise TypeError(
                            f"Compex types (LATENT/IMAGE) need to reference their width/height, e.g. {node.id}.width")
                raise NameError(f"Name not found: {node.id}")
            elif isinstance(node, ast.Call):
                if node.func.id in functions:
                    fn = functions[node.func.id]
                    l = len(node.args)
                    if l < fn["args"][0] or (fn["args"][1] is not None and l > fn["args"][1]):
                        if fn["args"][1] is None:
                            toErr = " or more"
                        else:
                            toErr = f" to {fn['args'][1]}"
                        raise SyntaxError(
                            f"Invalid function call: {node.func.id} requires {fn['args'][0]}{toErr} arguments")
                    args = []
                    for arg in node.args:
                        args.append(eval_expr(arg))
                    return fn["call"](*args)
                raise NameError(f"Invalid function call: {node.func.id}")
            elif isinstance(node, ast.Compare):
                l = eval_expr(node.left)
                r = eval_expr(node.comparators[0])
                if isinstance(node.ops[0], ast.Eq):
                    return 1 if l == r else 0
                if isinstance(node.ops[0], ast.NotEq):
                    return 1 if l != r else 0
                if isinstance(node.ops[0], ast.Gt):
                    return 1 if l > r else 0
                if isinstance(node.ops[0], ast.GtE):
                    return 1 if l >= r else 0
                if isinstance(node.ops[0], ast.Lt):
                    return 1 if l < r else 0
                if isinstance(node.ops[0], ast.LtE):
                    return 1 if l <= r else 0
                raise NotImplementedError(
                    "Operator " + node.ops[0].__class__.__name__ + " not supported.")
            else:
                raise TypeError(node)

        r = eval_expr(node)

        lookup = initial_values
        return {
            "ui": {"value": [r]},
            "result": (int(r), float(r),str(r),),
        }


NODE_CLASS_MAPPINGS = {
    "MathExpression_clh": MathExpression_clh,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MathExpression_clh": "Math Expression clh",
}
