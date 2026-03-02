"""
ARIA Tool Registry — Math & Code Execution
=============================================
Registers all mathematical tools and the code executor
into ARIA's tool-calling system.

Usage from ARIA:
    from atlas.assistants.aria.tools.registry import ToolRegistry

    registry = ToolRegistry()
    result = registry.call("black_scholes", S=150, K=155, T=0.25, r=0.05, sigma=0.2)
    result = registry.call("execute_code", code="print(2+2)")

Copyright (c) 2026 M&C. All rights reserved.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("atlas.aria.tools")


class ToolRegistry:
    """
    Central registry for all ARIA tools.
    Handles discovery, validation, and execution.
    """

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._executor = None
        self._register_all()

    def _register_all(self):
        """Register all available tool categories."""
        self._register_math_tools()
        self._register_code_executor()
        logger.info("ARIA tools registered: %d total", len(self._tools))

    def _register_math_tools(self):
        """Register financial math tools."""
        try:
            from atlas.assistants.aria.tools.financial_math import MATH_TOOLS

            TOOL_DESCRIPTIONS = {
                "present_value": {
                    "description": "Calculate present value of a future amount. PV = FV/(1+r)^n",
                    "params": {"fv": "float", "rate": "float", "periods": "int"},
                    "example": "present_value(fv=10000, rate=0.05, periods=10)",
                },
                "future_value": {
                    "description": "Calculate future value. FV = PV*(1+r)^n",
                    "params": {"pv": "float", "rate": "float", "periods": "int"},
                    "example": "future_value(pv=10000, rate=0.05, periods=10)",
                },
                "annuity_pv": {
                    "description": "Present value of an annuity stream.",
                    "params": {"payment": "float", "rate": "float", "periods": "int"},
                    "example": "annuity_pv(payment=500, rate=0.04, periods=20)",
                },
                "perpetuity_pv": {
                    "description": "Present value of a perpetuity (with optional growth).",
                    "params": {"payment": "float", "rate": "float", "growth": "float (optional)"},
                    "example": "perpetuity_pv(payment=1000, rate=0.08, growth=0.02)",
                },
                "effective_rate": {
                    "description": "Convert nominal rate to effective annual rate.",
                    "params": {"nominal": "float", "compounding_periods": "int"},
                    "example": "effective_rate(nominal=0.12, compounding_periods=12)",
                },
                "bond_price": {
                    "description": "Price a coupon bond given face value, coupon rate, YTM, and periods.",
                    "params": {"face": "float", "coupon_rate": "float", "ytm": "float", "periods": "int"},
                    "example": "bond_price(face=1000, coupon_rate=0.05, ytm=0.06, periods=10)",
                },
                "macaulay_duration": {
                    "description": "Calculate Macaulay and Modified duration of a bond.",
                    "params": {"face": "float", "coupon_rate": "float", "ytm": "float", "periods": "int"},
                    "example": "macaulay_duration(face=1000, coupon_rate=0.05, ytm=0.06, periods=10)",
                },
                "bond_convexity": {
                    "description": "Calculate bond convexity.",
                    "params": {"face": "float", "coupon_rate": "float", "ytm": "float", "periods": "int"},
                    "example": "bond_convexity(face=1000, coupon_rate=0.05, ytm=0.06, periods=10)",
                },
                "wacc": {
                    "description": "Weighted Average Cost of Capital.",
                    "params": {"equity": "float", "debt": "float", "cost_equity": "float", "cost_debt": "float", "tax_rate": "float"},
                    "example": "wacc(equity=600, debt=400, cost_equity=0.12, cost_debt=0.06, tax_rate=0.25)",
                },
                "npv": {
                    "description": "Net Present Value of cash flows.",
                    "params": {"cashflows": "list[float]", "discount_rate": "float"},
                    "example": "npv(cashflows=[-100000, 30000, 40000, 50000], discount_rate=0.10)",
                },
                "irr": {
                    "description": "Internal Rate of Return via Newton-Raphson.",
                    "params": {"cashflows": "list[float]"},
                    "example": "irr(cashflows=[-100000, 30000, 40000, 50000])",
                },
                "black_scholes": {
                    "description": "Black-Scholes option pricing (call or put).",
                    "params": {"S": "float (stock price)", "K": "float (strike)", "T": "float (years)", "r": "float (risk-free)", "sigma": "float (vol)", "option_type": "'call' or 'put'"},
                    "example": "black_scholes(S=150, K=155, T=0.25, r=0.05, sigma=0.20)",
                },
                "greeks": {
                    "description": "All Black-Scholes Greeks (Delta, Gamma, Vega, Theta, Rho).",
                    "params": {"S": "float", "K": "float", "T": "float", "r": "float", "sigma": "float", "option_type": "str"},
                    "example": "greeks(S=150, K=155, T=0.25, r=0.05, sigma=0.20)",
                },
                "put_call_parity": {
                    "description": "Given a call or put price, compute the other via put-call parity.",
                    "params": {"S": "float", "K": "float", "T": "float", "r": "float", "call_price or put_price": "float"},
                    "example": "put_call_parity(S=150, K=155, T=0.25, r=0.05, call_price=8.50)",
                },
                "implied_volatility": {
                    "description": "Find implied volatility from market option price via bisection.",
                    "params": {"market_price": "float", "S": "float", "K": "float", "T": "float", "r": "float"},
                    "example": "implied_volatility(market_price=8.50, S=150, K=155, T=0.25, r=0.05)",
                },
                "portfolio_stats": {
                    "description": "Portfolio expected return and variance from weights, returns, and covariance matrix.",
                    "params": {"weights": "list", "expected_returns": "list", "cov_matrix": "list[list]"},
                    "example": "portfolio_stats(weights=[0.6, 0.4], expected_returns=[0.10, 0.06], cov_matrix=[[0.04, 0.01],[0.01, 0.02]])",
                },
                "capm": {
                    "description": "CAPM expected return: E[Ri] = Rf + β(E[Rm]-Rf).",
                    "params": {"risk_free": "float", "beta": "float", "market_return": "float"},
                    "example": "capm(risk_free=0.04, beta=1.2, market_return=0.10)",
                },
                "beta_from_data": {
                    "description": "Calculate beta from return data arrays.",
                    "params": {"asset_returns": "list", "market_returns": "list"},
                    "example": "beta_from_data(asset_returns=[...], market_returns=[...])",
                },
                "value_at_risk": {
                    "description": "VaR and CVaR (historical or parametric).",
                    "params": {"returns": "list", "confidence": "float", "method": "'historical' or 'parametric'"},
                    "example": "value_at_risk(returns=[...], confidence=0.95)",
                },
                "sharpe_ratio": {
                    "description": "Annualized Sharpe ratio from daily returns.",
                    "params": {"returns": "list", "risk_free_rate": "float"},
                    "example": "sharpe_ratio(returns=[...], risk_free_rate=0.04)",
                },
                "sortino_ratio": {
                    "description": "Sortino ratio (uses downside deviation only).",
                    "params": {"returns": "list"},
                    "example": "sortino_ratio(returns=[...])",
                },
                "descriptive_stats": {
                    "description": "Full descriptive statistics (mean, median, std, skew, kurtosis).",
                    "params": {"data": "list[float]"},
                    "example": "descriptive_stats(data=[1.2, 3.4, 2.1, ...])",
                },
                "ols_regression": {
                    "description": "OLS linear regression with coefficients, t-stats, R².",
                    "params": {"y": "list", "X": "list[list]", "add_intercept": "bool"},
                    "example": "ols_regression(y=[...], X=[[x1_vals], [x2_vals]])",
                },
                "correlation_matrix": {
                    "description": "Pearson correlation matrix from named data series.",
                    "params": {"data": "dict of name → list"},
                    "example": "correlation_matrix(data={'AAPL': [...], 'MSFT': [...]})",
                },
                "gbm_simulate": {
                    "description": "Monte Carlo GBM simulation for asset price paths.",
                    "params": {"S0": "float", "mu": "float", "sigma": "float", "T": "float", "n_steps": "int", "n_paths": "int"},
                    "example": "gbm_simulate(S0=100, mu=0.08, sigma=0.20, T=1.0, n_steps=252, n_paths=5000)",
                },
            }

            for name, func in MATH_TOOLS.items():
                desc = TOOL_DESCRIPTIONS.get(name, {"description": func.__doc__ or name, "params": {}, "example": ""})
                self._tools[name] = {
                    "function": func,
                    "category": "financial_math",
                    "description": desc["description"],
                    "params": desc.get("params", {}),
                    "example": desc.get("example", ""),
                }

        except ImportError as e:
            logger.warning("Could not load financial math tools: %s", e)

    def _register_code_executor(self):
        """Register the code execution tool."""
        try:
            from atlas.assistants.aria.tools.code_executor.executor import CodeExecutor
            self._executor = CodeExecutor(timeout=30.0)

            self._tools["execute_code"] = {
                "function": self._execute_code,
                "category": "code_execution",
                "description": "Execute arbitrary Python code in a sandboxed environment. "
                              "Has access to numpy, pandas, math, and all financial_math tools. "
                              "Use this for complex calculations, data processing, or custom analysis.",
                "params": {"code": "str (Python code)", "context": "dict (optional variables)"},
                "example": 'execute_code(code="import numpy as np\\nprint(np.mean([1,2,3]))")',
            }
        except ImportError as e:
            logger.warning("Could not load code executor: %s", e)

    def _execute_code(self, code: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Wrapper for code execution."""
        if self._executor is None:
            return {"error": "Code executor not available"}
        return self._executor.execute(code, context)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def call(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call a registered tool by name.

        Args:
            tool_name: Name of the tool
            **kwargs:  Tool-specific arguments

        Returns:
            Tool result dict
        """
        if tool_name not in self._tools:
            return {
                "error": f"Unknown tool: {tool_name}",
                "available": self.list_tools(),
            }

        tool = self._tools[tool_name]
        try:
            result = tool["function"](**kwargs)
            return result
        except Exception as e:
            return {"error": f"{type(e).__name__}: {str(e)}"}

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return sorted(self._tools.keys())

    def describe_tool(self, name: str) -> Dict[str, Any]:
        """Get description for a specific tool."""
        if name not in self._tools:
            return {"error": f"Unknown tool: {name}"}
        tool = self._tools[name]
        return {
            "name": name,
            "category": tool["category"],
            "description": tool["description"],
            "params": tool.get("params", {}),
            "example": tool.get("example", ""),
        }

    def describe_all(self) -> List[Dict[str, Any]]:
        """Get descriptions for all tools (for ARIA's system prompt)."""
        return [self.describe_tool(name) for name in self.list_tools()]

    def to_system_prompt_block(self) -> str:
        """
        Generate a text block describing all tools for ARIA's system prompt.
        This gets injected into ARIA so she knows what tools are available.
        """
        lines = ["## Available Mathematical & Code Tools\n"]
        lines.append("You can call these tools to perform calculations:\n")

        by_category = {}
        for name, tool in self._tools.items():
            cat = tool["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append((name, tool))

        for cat, tools in sorted(by_category.items()):
            lines.append(f"\n### {cat.replace('_', ' ').title()}\n")
            for name, tool in tools:
                lines.append(f"**{name}**: {tool['description']}")
                if tool.get("example"):
                    lines.append(f"  Example: `{tool['example']}`")
                lines.append("")

        return "\n".join(lines)
