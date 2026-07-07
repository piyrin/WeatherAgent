"""
=============================================================================
计算器工具 — 安全的数学表达式求值
=============================================================================
职责：
  1. 接收数学表达式字符串
  2. 安全求值（使用 Python AST 而非 eval，防止代码注入）
  3. 返回计算结果

Agent 使用场景：
  用户问"北京到上海高铁5小时，平均速度多少"时，
  Agent 可能先查距离（1318km），再用本工具计算 1318÷5。
=============================================================================
"""

import ast
import math
import operator
from typing import Any

from app.tools.base import BaseTool
from app.utils.logger import logger


# =============================================================================
# 安全表达式求值器（基于 AST，不支持任意代码执行）
# =============================================================================

# 允许的操作符白名单
_ALLOWED_OPERATORS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,  # 负号，如 -5
    ast.UAdd: operator.pos,  # 正号，如 +5
}

# 允许的函数白名单
_ALLOWED_FUNCTIONS: dict[str, Any] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "ceil": math.ceil,
    "floor": math.floor,
    "pow": pow,
}

# 允许的常量
_ALLOWED_CONSTANTS: dict[str, Any] = {
    "pi": math.pi,
    "e": math.e,
}


class _SafeEvaluator(ast.NodeVisitor):
    """
    安全的 AST 表达式求值器

    只允许白名单内的操作符和函数，拒绝一切不安全操作
    （如属性访问、函数调用列表外的函数等）。
    """

    def __init__(self):
        self.result = None

    def visit_Expression(self, node: ast.Expression):
        """入口：表达式节点"""
        return self.visit(node.body)

    def visit_BinOp(self, node: ast.BinOp):
        """二元操作：a + b, a - b 等"""
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError(f"不支持的操作符: {op_type.__name__}")
        return _ALLOWED_OPERATORS[op_type](left, right)

    def visit_UnaryOp(self, node: ast.UnaryOp):
        """一元操作：-a, +a"""
        operand = self.visit(node.operand)
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError(f"不支持的操作符: {op_type.__name__}")
        return _ALLOWED_OPERATORS[op_type](operand)

    def visit_Constant(self, node: ast.Constant):
        """常量：数字、字符串等"""
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"不支持非常量数值: {type(node.value)}")
        return node.value

    def visit_Call(self, node: ast.Call):
        """函数调用：sqrt(4), abs(-5) 等"""
        if not isinstance(node.func, ast.Name):
            raise ValueError("不支持复杂函数调用")
        func_name = node.func.id
        if func_name not in _ALLOWED_FUNCTIONS:
            raise ValueError(f"不支持的函数: {func_name}")
        args = [self.visit(arg) for arg in node.args]
        return _ALLOWED_FUNCTIONS[func_name](*args)

    def visit_Name(self, node: ast.Name):
        """变量名：pi, e 等"""
        if node.id in _ALLOWED_CONSTANTS:
            return _ALLOWED_CONSTANTS[node.id]
        raise ValueError(f"不支持的变量: {node.id}")

    def generic_visit(self, node):
        """拒绝所有未明确允许的节点类型"""
        raise ValueError(f"不支持的表达式类型: {type(node).__name__}")


def safe_eval(expression: str) -> float:
    """
    安全的数学表达式求值

    参数：
        expression: 数学表达式字符串，如 "(3 + 5) * 2"

    返回值：
        计算结果（float）

    异常：
        ValueError：表达式不合法或包含不安全的操作
    """
    # 预处理：去掉空格
    expression = expression.strip()

    if not expression:
        raise ValueError("表达式不能为空")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"表达式语法错误: {str(exc)}") from exc

    evaluator = _SafeEvaluator()
    result = evaluator.visit(tree)

    if not isinstance(result, (int, float)):
        raise ValueError(f"计算结果类型异常: {type(result)}")

    return float(result)


# =============================================================================
# CalculatorTool
# =============================================================================


class CalculatorTool(BaseTool):
    """
    计算器工具

    安全地对数学表达式求值。
    使用 AST 解析 + 白名单机制，杜绝代码注入风险。
    """

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "执行数学计算。支持基本运算（+ - * /）、幂运算（**）、"
            "括号、以及常用函数（sqrt、abs、round、sin、cos、log 等）。"
            "参数：expression（数学表达式字符串，必填）"
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '1318 / 5'、'sqrt(16) + 3'、'(32 - 18) * 5 / 9'",
                },
            },
            "required": ["expression"],
        }

    async def _execute(self, expression: str, **kwargs: Any) -> dict:
        """
        执行数学计算

        参数：
            expression: 数学表达式字符串

        返回值：
            dict 包含计算结果
        """
        logger.info(f"计算表达式 | expression={expression}")

        try:
            value = safe_eval(expression)

            # 智能格式化：整数不显示小数点
            if value == int(value) and abs(value) < 1e15:
                formatted = str(int(value))
            else:
                formatted = f"{value:.6f}".rstrip("0").rstrip(".")

            summary = f"{expression} = {formatted}"

            return {
                "success": True,
                "result": {"expression": expression, "value": value, "formatted": formatted},
                "error": None,
                "summary": summary,
            }

        except (ValueError, ZeroDivisionError, OverflowError) as exc:
            error_msg = str(exc)
            return {
                "success": False,
                "result": None,
                "error": error_msg,
                "summary": f"计算失败: {error_msg}",
            }
