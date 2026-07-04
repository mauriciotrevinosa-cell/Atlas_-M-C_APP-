"""
Small, safe feature expression engine for Atlas market data.

This is a qlib-style convenience layer, not a qlib runtime. Expressions are
parsed through a tiny whitelist of functions so feature sets can be declared,
tested, and reused without eval().
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

import numpy as np
import pandas as pd


_FUNC_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$")


@dataclass(frozen=True)
class FeatureExpression:
    """Named expression specification."""

    name: str
    expression: str

    def to_dict(self) -> Dict[str, str]:
        return {"name": self.name, "expression": self.expression}


DEFAULT_QLIB_LITE_EXPRESSIONS: Sequence[FeatureExpression] = (
    FeatureExpression("ret_1", "Return($close, 1)"),
    FeatureExpression("ret_5", "Return($close, 5)"),
    FeatureExpression("ma_10_gap", "Div(Sub($close, Mean($close, 10)), Mean($close, 10))"),
    FeatureExpression("vol_z_20", "ZScore($volume, 20)"),
    FeatureExpression("price_volume_corr_20", "Corr($close, $volume, 20)"),
)


class FeatureExpressionEngine:
    """Evaluate a small whitelist of market feature expressions."""

    def __init__(self, data: pd.DataFrame):
        if data.empty:
            raise ValueError("FeatureExpressionEngine requires non-empty data")
        self.data = data
        self._columns = {str(col).lower(): col for col in data.columns}

    def evaluate(self, expression: str) -> pd.Series:
        expression = expression.strip()
        if not expression:
            raise ValueError("expression cannot be empty")

        if expression.startswith("$"):
            return self._column(expression[1:])

        if self._is_number(expression):
            return pd.Series(float(expression), index=self.data.index)

        match = _FUNC_RE.match(expression)
        if not match:
            raise ValueError(f"Unsupported expression: {expression}")

        name = match.group(1).lower()
        args = self._split_args(match.group(2))
        return self._call(name, args)

    def evaluate_many(self, specs: Iterable[FeatureExpression]) -> pd.DataFrame:
        result = pd.DataFrame(index=self.data.index)
        for spec in specs:
            result[spec.name] = self.evaluate(spec.expression)
        return result

    def evaluate_default(self) -> pd.DataFrame:
        return self.evaluate_many(DEFAULT_QLIB_LITE_EXPRESSIONS)

    def _call(self, name: str, args: List[str]) -> pd.Series:
        if name in {"mean", "std", "min", "max"}:
            self._expect_args(name, args, 2)
            series = self.evaluate(args[0])
            window = self._int_arg(args[1])
            rolling = series.rolling(window=window, min_periods=window)
            return getattr(rolling, name)()

        if name == "ref":
            self._expect_args(name, args, 2)
            return self.evaluate(args[0]).shift(self._int_arg(args[1]))

        if name == "delta":
            self._expect_args(name, args, 2)
            series = self.evaluate(args[0])
            periods = self._int_arg(args[1])
            return series - series.shift(periods)

        if name == "return":
            self._expect_args(name, args, 2)
            return self.evaluate(args[0]).pct_change(self._int_arg(args[1]))

        if name == "logreturn":
            self._expect_args(name, args, 2)
            series = self.evaluate(args[0]).astype(float)
            periods = self._int_arg(args[1])
            return np.log(series / series.shift(periods))

        if name == "zscore":
            self._expect_args(name, args, 2)
            series = self.evaluate(args[0]).astype(float)
            window = self._int_arg(args[1])
            mean = series.rolling(window=window, min_periods=window).mean()
            std = series.rolling(window=window, min_periods=window).std(ddof=0)
            return (series - mean) / std.replace(0, np.nan)

        if name == "corr":
            self._expect_args(name, args, 3)
            left = self.evaluate(args[0]).astype(float)
            right = self.evaluate(args[1]).astype(float)
            window = self._int_arg(args[2])
            return left.rolling(window=window, min_periods=window).corr(right)

        if name in {"add", "sub", "mul", "div"}:
            self._expect_args(name, args, 2)
            left = self.evaluate(args[0]).astype(float)
            right = self.evaluate(args[1]).astype(float)
            if name == "add":
                return left + right
            if name == "sub":
                return left - right
            if name == "mul":
                return left * right
            return left / right.replace(0, np.nan)

        if name == "clip":
            self._expect_args(name, args, 3)
            series = self.evaluate(args[0]).astype(float)
            lower = self._float_arg(args[1])
            upper = self._float_arg(args[2])
            return series.clip(lower=lower, upper=upper)

        raise ValueError(f"Unsupported function: {name}")

    def _column(self, name: str) -> pd.Series:
        column = self._columns.get(name.lower())
        if column is None:
            raise ValueError(f"Column not found: {name}")
        return self.data[column]

    @classmethod
    def _split_args(cls, raw: str) -> List[str]:
        args: List[str] = []
        depth = 0
        start = 0
        for idx, char in enumerate(raw):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth < 0:
                    raise ValueError("unbalanced expression parentheses")
            elif char == "," and depth == 0:
                args.append(raw[start:idx].strip())
                start = idx + 1
        if depth != 0:
            raise ValueError("unbalanced expression parentheses")
        tail = raw[start:].strip()
        if tail:
            args.append(tail)
        return args

    @staticmethod
    def _expect_args(name: str, args: Sequence[str], expected: int) -> None:
        if len(args) != expected:
            raise ValueError(f"{name} expects {expected} args, got {len(args)}")

    @staticmethod
    def _int_arg(value: str) -> int:
        number = float(value)
        if not math.isfinite(number) or int(number) != number or number <= 0:
            raise ValueError(f"Expected positive integer, got {value}")
        return int(number)

    @staticmethod
    def _float_arg(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"Expected finite number, got {value}")
        return number

    @staticmethod
    def _is_number(value: str) -> bool:
        try:
            float(value)
            return True
        except ValueError:
            return False
