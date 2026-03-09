"""
Financial Concepts Knowledge Base
==================================
Comprehensive, structured encyclopedia of financial concepts for ARIA.

Every concept includes:
  - summary       : One-line definition
  - definition    : Full explanation
  - mechanics     : Step-by-step how it works
  - formulas      : Plain-text + LaTeX math (plain used at runtime)
  - examples      : Concrete worked examples with numbers
  - risks         : Downside / risk factors
  - advantages    : Upside / benefits
  - related_ids   : Links to related concepts
  - tags          : Searchable keywords

This is the single source of truth for financial education in Atlas.
ARIA consumes this via ExplainConceptTool.

Categories:
  core_actions       - Buy, Sell
  position_types     - Long, Short
  time_strategies    - Buy&Hold, Day Trading, Swing, Position
  market_direction   - Bull, Bear markets
  order_types        - Market Order, Limit Order
  advanced_concepts  - Margin, Leverage, Hedging, Options, Futures, etc.
  risk_math          - VaR, CVaR, Drawdown, Kelly, Sharpe, Liquidation
  pnl_math           - P&L formulas, returns, the Super-Formula

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Formula:
    """A single mathematical formula."""
    name:        str          # "Long P&L"
    plain:       str          # Human-readable: "Profit = (Sell - Buy) × Qty"
    latex:       str          # LaTeX form for rendering: "Π = Q(P_t - P_0)"
    variables:   Dict[str, str] = field(default_factory=dict)  # var → meaning
    description: str = ""     # When / how to use this formula


@dataclass
class Example:
    """A concrete worked example."""
    title:       str          # "Going long on AAPL"
    scenario:    str          # Setup description
    calculation: str          # Step-by-step math
    outcome:     str          # Final result + takeaway


@dataclass
class ConceptEntry:
    """
    A single financial concept — the atomic unit of the knowledge base.
    """
    id:           str                   # Unique slug: "short_selling"
    name:         str                   # Display name: "Short Selling"
    emoji:        str                   # Visual: "📉"
    category:     str                   # "position_types"
    summary:      str                   # One-liner definition
    definition:   str                   # Full 2–4 sentence explanation
    mechanics:    List[str]             # Ordered steps / bullets
    formulas:     List[Formula]         # Math formulas
    examples:     List[Example]         # Worked examples
    risks:        List[str]             # Risk bullets
    advantages:   List[str]             # Benefit bullets
    related_ids:  List[str]             # IDs of related concepts
    tags:         List[str]             # Searchable tags
    aliases:      List[str]             # Alternative names → "shorting", "short"

    def one_liner(self) -> str:
        return f"{self.emoji}  **{self.name}** — {self.summary}"


# ---------------------------------------------------------------------------
# The Knowledge Base
# ---------------------------------------------------------------------------

_CONCEPTS: List[ConceptEntry] = [

    # ══════════════════════════════════════════════════════════════════
    #  CORE ACTIONS
    # ══════════════════════════════════════════════════════════════════

    ConceptEntry(
        id="buy",
        name="Buy",
        emoji="📈",
        category="core_actions",
        summary="Purchase an asset expecting its price to rise.",
        definition=(
            "To buy (also called 'going long' or 'opening a long position') means to exchange "
            "cash for ownership of a financial asset — stock, ETF, crypto, bond, or contract. "
            "Your profit or loss depends entirely on what happens to the price after you buy. "
            "The maximum loss on a cash (non-leveraged) buy is 100% of the amount invested, "
            "if the asset goes to zero."
        ),
        mechanics=[
            "Choose the asset and the quantity you want to purchase.",
            "Select an order type: market (instant, best available price) or limit (specific price).",
            "Your broker debits cash and credits the asset to your account.",
            "You are now 'long' — you profit if price rises, lose if it falls.",
            "Exit by selling the position; P&L is realised at that point.",
        ],
        formulas=[
            Formula(
                name="Buy P&L (Simple)",
                plain="Profit = (Sell Price − Buy Price) × Quantity − Costs",
                latex=r"\Pi = Q(P_{sell} - P_{buy}) - C",
                variables={"Q": "quantity (shares/units)", "P": "price", "C": "transaction costs"},
                description="The fundamental long position profit equation.",
            ),
            Formula(
                name="Simple Return",
                plain="Return = (Sell Price − Buy Price) / Buy Price",
                latex=r"R = (P_t - P_0) / P_0",
                variables={"P_t": "price at exit", "P_0": "price at entry"},
                description="Percentage return on the position.",
            ),
            Formula(
                name="Break-even Price (with proportional fee α)",
                plain="Break-even ≈ Buy Price × (1 + 2α)",
                latex=r"P_{BE} \approx P_0(1 + 2\alpha)",
                variables={"α": "fee rate per side (e.g. 0.001 for 0.1%)"},
                description="Minimum exit price to recover costs.",
            ),
        ],
        examples=[
            Example(
                title="AAPL long trade",
                scenario="Buy 100 shares of AAPL at $150. Price rises to $165.",
                calculation="Profit = ($165 − $150) × 100 = $1,500",
                outcome="Return = $1,500 / $15,000 = +10%. Excluding fees.",
            ),
            Example(
                title="Loss scenario",
                scenario="Buy 50 shares at $200. Price falls to $180.",
                calculation="Loss = ($180 − $200) × 50 = −$1,000",
                outcome="Return = −$1,000 / $10,000 = −10%.",
            ),
        ],
        risks=[
            "Full capital loss if asset goes to $0.",
            "Opportunity cost — capital tied up cannot be deployed elsewhere.",
            "Market timing risk — even good companies can decline short-term.",
        ],
        advantages=[
            "Simple to understand and execute.",
            "Maximum loss capped at amount invested (no debt).",
            "Unlimited upside potential.",
            "Eligible for long-term capital gains tax treatment (varies by jurisdiction).",
        ],
        related_ids=["sell", "long_position", "limit_order", "market_order", "stop_loss"],
        tags=["buy", "long", "entry", "purchase", "basic"],
        aliases=["purchase", "go long", "open long", "long entry"],
    ),

    ConceptEntry(
        id="sell",
        name="Sell",
        emoji="💰",
        category="core_actions",
        summary="Dispose of an asset you own to realise cash or a P&L.",
        definition=(
            "Selling can mean two very different things in markets. (1) Closing a long position: "
            "you sell an asset you own, realising any profit or loss. (2) Opening a short position: "
            "you sell borrowed shares, betting the price will fall so you can buy them back cheaper. "
            "In everyday use, 'sell' almost always refers to the first meaning unless you specify 'short sell'."
        ),
        mechanics=[
            "Select the position or asset to sell.",
            "Choose quantity (all or partial).",
            "Decide order type: market (immediate) or limit (at a target price).",
            "Broker credits cash and debits the asset from your account.",
            "P&L is realised and your position is reduced or closed.",
        ],
        formulas=[
            Formula(
                name="Net Proceeds",
                plain="Net Proceeds = (Sell Price × Quantity) − Fees",
                latex=r"NP = Q \cdot P_{sell} - C",
                variables={"Q": "quantity", "P_sell": "sell price", "C": "fees"},
                description="Cash you actually receive after fees.",
            ),
        ],
        examples=[
            Example(
                title="Taking profit",
                scenario="Own 200 SPY shares bought at $430. Now at $480. Sell all.",
                calculation="Proceeds = $480 × 200 = $96,000. Cost basis = $86,000. Gain = $10,000.",
                outcome="+11.6% return. Locked in profit.",
            ),
            Example(
                title="Cutting losses",
                scenario="Own 100 TSLA shares at $300. Falls to $240. Sell.",
                calculation="Loss = ($240 − $300) × 100 = −$6,000.",
                outcome="−20% loss realised. Capital preserved at $24,000 for redeployment.",
            ),
        ],
        risks=[
            "Selling too early can miss further upside (seller's remorse).",
            "Selling during panic often locks in the worst price.",
            "Tax event: selling triggers capital gains/losses in most jurisdictions.",
        ],
        advantages=[
            "Realises profit and reduces market exposure.",
            "Stops further losses if thesis changes.",
            "Frees capital for better opportunities.",
        ],
        related_ids=["buy", "short_position", "stop_loss", "take_profit"],
        tags=["sell", "exit", "close", "liquidate"],
        aliases=["exit", "close position", "liquidate", "offload"],
    ),

    # ══════════════════════════════════════════════════════════════════
    #  POSITION TYPES
    # ══════════════════════════════════════════════════════════════════

    ConceptEntry(
        id="long_position",
        name="Long Position",
        emoji="📈",
        category="position_types",
        summary="Owning an asset and profiting if its price rises.",
        definition=(
            "A long position means you have purchased and hold an asset. You profit if the price "
            "goes up and lose if it goes down. This is the default mode most retail investors "
            "operate in. Long positions can be held from seconds (day trading) to decades (buy-and-hold). "
            "Maximum loss = amount invested. Maximum gain = unlimited (theoretically)."
        ),
        mechanics=[
            "Buy an asset (stock, ETF, crypto, futures contract).",
            "Hold while price moves.",
            "Profit = (Exit Price − Entry Price) × Quantity.",
            "Exit by selling — P&L is locked in.",
        ],
        formulas=[
            Formula(
                name="Long P&L (full)",
                plain="Profit = Q × (P_exit − P_entry) − Fees − Slippage",
                latex=r"\Pi_t = Q(P_t - P_0) - C - s",
                variables={"Q": "quantity", "P_t": "current/exit price", "P_0": "entry price",
                           "C": "transaction costs", "s": "slippage"},
                description="Complete P&L including execution friction.",
            ),
            Formula(
                name="Log Return",
                plain="Log Return = ln(Exit Price / Entry Price)",
                latex=r"r = \ln(P_t / P_0)",
                variables={"ln": "natural logarithm"},
                description="Log returns are additive over time — preferred in quant work.",
            ),
        ],
        examples=[
            Example(
                title="Long stock with profit",
                scenario="Buy 500 shares at $20. Price rises to $28 over 6 months.",
                calculation="P&L = ($28 − $20) × 500 = $4,000. Return = 40%.",
                outcome="+$4,000. Log return = ln(28/20) = 33.6% (log scale).",
            ),
        ],
        risks=[
            "Price falls → direct loss.",
            "Black swan events (company bankruptcy, regulatory shock) can cause near-total loss.",
            "Holding long in a bear market erodes capital.",
        ],
        advantages=[
            "Simple and well-understood.",
            "Limited loss (can't lose more than invested, cash position).",
            "Eligible for dividends and shareholder rights.",
        ],
        related_ids=["short_position", "buy", "leverage", "bull_market"],
        tags=["long", "ownership", "buy", "bullish"],
        aliases=["long", "long trade", "long side"],
    ),

    ConceptEntry(
        id="short_position",
        name="Short Position (Short Selling)",
        emoji="📉",
        category="position_types",
        summary="Borrow and sell an asset, profit if the price falls.",
        definition=(
            "Short selling involves borrowing shares from your broker, selling them immediately, "
            "then buying them back later at (hopefully) a lower price, returning them, and keeping "
            "the difference as profit. It is the mechanism for betting a price will fall. "
            "The risk is asymmetric: maximum gain is limited (price → 0), maximum loss is theoretically "
            "infinite (price can rise without limit)."
        ),
        mechanics=[
            "Borrow shares from broker (automatic at most brokers, a borrow fee applies).",
            "Immediately sell the borrowed shares → receive cash proceeds.",
            "Wait for price to fall.",
            "Buy back ('cover') the shares at a lower price.",
            "Return borrowed shares to broker.",
            "Keep the spread as profit, minus borrow fees and commissions.",
        ],
        formulas=[
            Formula(
                name="Short P&L",
                plain="Profit = (Short Price − Cover Price) × Quantity − Borrow Cost − Fees",
                latex=r"\Pi = Q(P_0 - P_t) - Q P_0 \cdot b \cdot \Delta t - C",
                variables={"P_0": "price at short entry", "P_t": "price at cover",
                           "b": "annualised borrow rate", "Δt": "holding time (years)"},
                description="Short profit minus borrow fees (charged daily on notional).",
            ),
            Formula(
                name="Short Return",
                plain="Return = (Short Price − Cover Price) / Short Price",
                latex=r"R_{short} = (P_0 - P_t) / P_0",
                variables={},
                description="Note: denominator is entry price, not cover price.",
            ),
            Formula(
                name="Max Loss (short)",
                plain="Max Loss is unlimited (price can rise to infinity)",
                latex=r"\Pi_{min} \to -\infty \text{ as } P_t \to \infty",
                variables={},
                description="This is the fundamental asymmetry of short selling.",
            ),
        ],
        examples=[
            Example(
                title="Successful short",
                scenario="Short 200 shares at $100. Price falls to $70. Cover.",
                calculation="P&L = ($100 − $70) × 200 = $6,000. Return = 30%.",
                outcome="+$6,000. Minus borrow fees if held for weeks/months.",
            ),
            Example(
                title="Short squeeze (loss scenario)",
                scenario="Short 100 shares at $50. Price surges to $150 due to short squeeze.",
                calculation="Loss = ($50 − $150) × 100 = −$10,000.",
                outcome="−200% loss on notional. You lost twice the initial position value.",
            ),
        ],
        risks=[
            "Unlimited loss potential — price can rise indefinitely.",
            "Margin calls: broker demands more collateral as loss grows.",
            "Short squeeze: forced buying by multiple shorts can rocket the price.",
            "Borrow fees can be very high for 'hard to borrow' stocks.",
            "Dividends on shorted stock must be paid to the lender.",
            "Regulatory risk: short selling bans have occurred in crises.",
        ],
        advantages=[
            "Profit from falling prices.",
            "Hedge a long portfolio (reduce net market exposure).",
            "Expose fraudulent or overvalued companies.",
        ],
        related_ids=["long_position", "margin_trading", "short_squeeze", "hedging"],
        tags=["short", "bearish", "borrow", "sell short"],
        aliases=["short", "shorting", "short sell", "go short", "short side"],
    ),

    # ══════════════════════════════════════════════════════════════════
    #  TIME-BASED STRATEGIES
    # ══════════════════════════════════════════════════════════════════

    ConceptEntry(
        id="buy_and_hold",
        name="Buy and Hold",
        emoji="⏳",
        category="time_strategies",
        summary="Buy an asset and hold it for years regardless of short-term volatility.",
        definition=(
            "Buy and hold is a passive long-term investment strategy. You purchase assets — "
            "typically diversified index funds or quality individual stocks — and hold them "
            "through market cycles without trying to time the market. The philosophy is grounded "
            "in the empirical fact that markets trend upward over long periods, and that frequent "
            "trading destroys returns through taxes and fees."
        ),
        mechanics=[
            "Identify quality assets (broad index ETFs, blue chips, quality growth).",
            "Buy and do not sell for at least 3–10+ years.",
            "Reinvest dividends (compound returns).",
            "Ignore short-term volatility — it's noise to a long-term holder.",
            "Review periodically and rebalance if allocation drifts.",
        ],
        formulas=[
            Formula(
                name="Compound Growth",
                plain="Final Value = Initial Value × (1 + Annual Return)^Years",
                latex=r"V_T = V_0 (1 + r)^T",
                variables={"V_0": "initial investment", "r": "annual return", "T": "years"},
                description="The power of compounding over time.",
            ),
            Formula(
                name="Rule of 72",
                plain="Years to Double = 72 / Annual Return %",
                latex=r"T_{double} \approx 72 / r\%",
                variables={"r%": "percentage return"},
                description="Quick estimate of doubling time at any return rate.",
            ),
        ],
        examples=[
            Example(
                title="S&P 500 30-year buy and hold",
                scenario="Invest $10,000 in SPY in 1994. Hold to 2024. Avg return ~10.5%/yr.",
                calculation="$10,000 × (1.105)^30 ≈ $206,000.",
                outcome="+1,960% total return. No stock-picking required.",
            ),
        ],
        risks=[
            "Requires emotional discipline during major crashes (e.g. −57% in 2009).",
            "If held in wrong asset (company goes bankrupt), full loss.",
            "Sequence of returns risk for retirees.",
        ],
        advantages=[
            "Very low fees (minimal trading).",
            "Tax-efficient (fewer realisation events).",
            "Time-in-market beats timing-the-market empirically.",
            "No skill in short-term prediction required.",
        ],
        related_ids=["long_position", "diversification", "bull_market", "portfolio"],
        tags=["passive", "long-term", "compounding", "index investing"],
        aliases=["passive investing", "index investing", "buy-and-hold"],
    ),

    ConceptEntry(
        id="day_trading",
        name="Day Trading",
        emoji="⚡",
        category="time_strategies",
        summary="Open and close all positions within the same trading session.",
        definition=(
            "Day trading involves entering and exiting positions within the same trading day — "
            "no positions are held overnight. Profits come from exploiting small intraday price "
            "movements using technical analysis, order flow, and momentum. Day trading requires "
            "fast execution, discipline, and significant capital. Research consistently shows that "
            "the majority of day traders lose money after fees."
        ),
        mechanics=[
            "Identify intraday setups using charts (1m, 5m, 15m timeframes).",
            "Enter position at optimal entry signal.",
            "Use tight stop losses (small risk per trade).",
            "Exit before market close — no overnight risk.",
            "Repeat with high frequency; many small wins target > losses.",
        ],
        formulas=[
            Formula(
                name="Daily P&L",
                plain="Daily P&L = Σ (Exits − Entries) × Sizes − All Commissions",
                latex=r"\Pi_{day} = \sum_i Q_i(P_{exit,i} - P_{entry,i}) - \sum_i C_i",
                variables={},
                description="Sum of all trades in a session after costs.",
            ),
        ],
        examples=[
            Example(
                title="5 trades, mixed results",
                scenario="5 trades: +$300, −$100, +$200, −$150, +$50. Commissions: $25 total.",
                calculation="Net = $300 − $100 + $200 − $150 + $50 − $25 = $275.",
                outcome="Profitable day: +$275. But over a month, consistency is what matters.",
            ),
        ],
        risks=[
            "High transaction costs erode profits on small moves.",
            "Psychological pressure leads to emotional decisions.",
            "Pattern Day Trader (PDT) rule in the US: need $25,000+ for >3 day trades/week.",
            "Most day traders underperform simple buy-and-hold strategies.",
        ],
        advantages=[
            "No overnight gap risk.",
            "Potentially high returns if skilled and disciplined.",
            "Can profit in both bull and bear markets.",
        ],
        related_ids=["swing_trading", "short_position", "market_order", "stop_loss"],
        tags=["intraday", "active", "technical", "scalping"],
        aliases=["intraday trading", "scalping"],
    ),

    ConceptEntry(
        id="swing_trading",
        name="Swing Trading",
        emoji="🔄",
        category="time_strategies",
        summary="Hold positions for days to weeks to capture medium-term price swings.",
        definition=(
            "Swing trading targets multi-day to multi-week price moves — riding the 'swing' "
            "between support and resistance levels, or following medium-term trends. It sits "
            "between day trading (hours) and position trading (months). Swing traders use "
            "a mix of technical and fundamental analysis and accept overnight and weekend risk."
        ),
        mechanics=[
            "Identify a trending or range-bound market on daily/4h charts.",
            "Enter on a pullback to support (long) or rally to resistance (short).",
            "Set stop loss below support / above resistance.",
            "Target: next resistance level or 2–3× the risk (R:R ratio ≥ 2).",
            "Hold for 2–10 trading days, then reassess.",
        ],
        formulas=[
            Formula(
                name="Risk/Reward Ratio",
                plain="R:R = (Target Price − Entry) / (Entry − Stop Loss)",
                latex=r"R:R = (P_{target} - P_{entry}) / (P_{entry} - P_{stop})",
                variables={},
                description="Minimum R:R of 2:1 is a common swing trading requirement.",
            ),
        ],
        examples=[
            Example(
                title="Bullish swing on MSFT",
                scenario="MSFT pulls back to $380 support. Entry: $380. Stop: $370. Target: $400.",
                calculation="Risk = $10/share. Reward = $20/share. R:R = 2:1.",
                outcome="If target hit: +$20 gain. If stopped: −$10 loss. Edge over multiple trades.",
            ),
        ],
        risks=[
            "Overnight and weekend gap risk (news can gap past stop).",
            "Requires active monitoring of positions.",
            "Medium-term trends can reverse unexpectedly.",
        ],
        advantages=[
            "Better work/life balance than day trading.",
            "Lower commissions than day trading (fewer trades).",
            "Can capture meaningful moves without full-time screen time.",
        ],
        related_ids=["day_trading", "position_trading", "stop_loss", "take_profit"],
        tags=["swing", "medium-term", "technical", "trend"],
        aliases=["swing", "swing trade"],
    ),

    ConceptEntry(
        id="position_trading",
        name="Position Trading",
        emoji="📅",
        category="time_strategies",
        summary="Hold positions for weeks to months following macro or major trends.",
        definition=(
            "Position trading sits between swing trading and buy-and-hold. A position trader "
            "holds trades for weeks to months, following major macro trends, earnings cycles, "
            "or sector rotations. It requires patience, a macro view, and the ability to sit "
            "through normal volatility without panic. Less active than swing trading, more "
            "tactical than passive investing."
        ),
        mechanics=[
            "Form a thesis (macro: rising rates → short bonds; sector: AI boom → long NVDA).",
            "Enter on technical confirmation of the macro thesis.",
            "Hold through normal volatility — wide stops to avoid premature exits.",
            "Exit when thesis is invalidated or target reached.",
        ],
        formulas=[],
        examples=[
            Example(
                title="Macro trade: energy sector",
                scenario="Thesis: oil supply constraint + strong demand → energy stocks up. Buy XLE.",
                calculation="Hold XLE for 3 months during rally from $85 to $105.",
                outcome="+23.5% in 3 months. Wide stop allowed holding through normal swings.",
            ),
        ],
        risks=[
            "Macro thesis can be wrong or take longer than capital allows.",
            "Wider stops mean larger potential losses per trade.",
            "Opportunity cost of slow-moving positions.",
        ],
        advantages=[
            "Low transaction costs.",
            "Aligns with institutional-scale moves.",
            "Less screen time than day/swing trading.",
        ],
        related_ids=["swing_trading", "buy_and_hold", "hedging"],
        tags=["macro", "long-term", "trend-following", "position"],
        aliases=["position trade", "trend following"],
    ),

    # ══════════════════════════════════════════════════════════════════
    #  MARKET DIRECTION
    # ══════════════════════════════════════════════════════════════════

    ConceptEntry(
        id="bull_market",
        name="Bull Market",
        emoji="🐂",
        category="market_direction",
        summary="A sustained period of rising asset prices, usually defined as +20% from recent lows.",
        definition=(
            "A bull market is a period in which asset prices rise persistently, driven by strong "
            "economic fundamentals, investor optimism, and risk-on sentiment. Historically defined "
            "as a rise of 20% or more from the most recent low. Bull markets can last years. "
            "The average bull market lasts ~3.8 years with an average gain of ~160%."
        ),
        mechanics=[
            "Economic expansion drives corporate earnings growth.",
            "Investors increase risk appetite → capital flows into equities.",
            "Rising prices attract more buyers → self-reinforcing momentum.",
            "Eventually ends via recession, rate shock, or valuation excess.",
        ],
        formulas=[],
        examples=[
            Example(
                title="2009–2020 S&P 500 bull market",
                scenario="S&P 500 bottomed in March 2009 at ~666. Peaked Feb 2020 at ~3,386.",
                calculation="Gain = (3386 − 666) / 666 = +408% over ~11 years.",
                outcome="Longest bull market in US history. Buy-and-hold was optimal strategy.",
            ),
        ],
        risks=[
            "Late-cycle bull markets show euphoria — valuation bubble risk.",
            "Overconfidence → under-hedging.",
        ],
        advantages=[
            "Long positions profitable.",
            "Dividends and compounding work strongly.",
        ],
        related_ids=["bear_market", "buy_and_hold", "long_position"],
        tags=["bull", "uptrend", "risk-on", "rally"],
        aliases=["bull run", "uptrend", "rising market"],
    ),

    ConceptEntry(
        id="bear_market",
        name="Bear Market",
        emoji="🐻",
        category="market_direction",
        summary="A sustained decline of −20% or more from recent highs.",
        definition=(
            "A bear market is a prolonged decline in asset prices — officially defined as a "
            "fall of 20% or more from the recent peak. Bear markets are driven by economic "
            "contraction, rising rates, geopolitical shocks, or systemic financial crises. "
            "They create opportunities for short sellers and patient long-term buyers who "
            "accumulate at depressed prices."
        ),
        mechanics=[
            "Trigger: recession fear, rate hike, credit crisis, or external shock.",
            "Investor sentiment shifts from greed to fear.",
            "Selling pressure → falling prices → more fear → more selling.",
            "Often ends when central bank provides liquidity or economy bottoms.",
        ],
        formulas=[
            Formula(
                name="Drawdown from Peak",
                plain="Drawdown = (Current Price − Peak Price) / Peak Price",
                latex=r"DD = (P_t - P_{peak}) / P_{peak}",
                variables={},
                description="Negative number. Bear market threshold: −20%.",
            ),
        ],
        examples=[
            Example(
                title="2022 Bear Market",
                scenario="S&P 500 peaked at ~4,800 in Jan 2022. Fell to ~3,500 by Oct 2022.",
                calculation="Decline = (3500 − 4800) / 4800 = −27.1%.",
                outcome="Full recovery took until early 2024. Long-term holders stayed patient.",
            ),
        ],
        risks=[
            "Long positions can suffer severe losses.",
            "Margin calls can force selling at the worst time.",
        ],
        advantages=[
            "Short positions and put options profit.",
            "Long-term accumulation at discounted prices (for patient capital).",
        ],
        related_ids=["bull_market", "short_position", "hedging", "drawdown"],
        tags=["bear", "downtrend", "recession", "crash", "decline"],
        aliases=["bear run", "crash", "downtrend"],
    ),

    # ══════════════════════════════════════════════════════════════════
    #  ORDER TYPES
    # ══════════════════════════════════════════════════════════════════

    ConceptEntry(
        id="market_order",
        name="Market Order",
        emoji="⚡",
        category="order_types",
        summary="Execute immediately at the best available current price.",
        definition=(
            "A market order instructs the broker to buy or sell immediately at whatever the "
            "current market price is. It guarantees execution but not a specific price. "
            "For liquid assets (SPY, AAPL), the execution price is usually very close to the "
            "last quoted price. For illiquid assets or large orders, slippage can be significant."
        ),
        mechanics=[
            "Submit order — broker sends to exchange immediately.",
            "Matched against the best available ask (if buying) or bid (if selling).",
            "Order fills typically in milliseconds for liquid assets.",
            "Final fill price may differ slightly from quoted price (slippage).",
        ],
        formulas=[
            Formula(
                name="Slippage (simple model)",
                plain="Slippage = |Fill Price − Expected Price| × Quantity",
                latex=r"s = |P_{fill} - P_{expected}| \cdot Q",
                variables={},
                description="Total cost of execution worse than mid-market.",
            ),
            Formula(
                name="Effective Spread",
                plain="Spread = Ask Price − Bid Price",
                latex=r"S = A - B",
                variables={"A": "best ask", "B": "best bid"},
                description="You lose half the spread when buying/selling with a market order.",
            ),
        ],
        examples=[
            Example(
                title="Buying SPY with market order",
                scenario="SPY bid=$495.00, ask=$495.02. Buy 100 shares market order.",
                calculation="You pay ~$495.02. Spread cost = $0.02 × 100 = $2.",
                outcome="Filled instantly. Spread cost = $2. Acceptable for liquid ETF.",
            ),
        ],
        risks=[
            "No price guarantee — can fill significantly worse in fast markets.",
            "In illiquid markets, large orders move price against you (market impact).",
        ],
        advantages=[
            "Guaranteed execution (assuming liquid market).",
            "No risk of order not filling.",
            "Simple — useful when speed matters more than price.",
        ],
        related_ids=["limit_order", "stop_loss", "liquidity"],
        tags=["order", "execution", "instant", "fill"],
        aliases=["market buy", "market sell", "at market"],
    ),

    ConceptEntry(
        id="limit_order",
        name="Limit Order",
        emoji="🎯",
        category="order_types",
        summary="Buy or sell only at a specific price or better.",
        definition=(
            "A limit order sets a maximum buy price or minimum sell price. For a buy limit order, "
            "you will only pay your specified price or lower. For a sell limit order, you will "
            "only receive your price or higher. This gives you price control at the cost of "
            "execution certainty — the order may never fill if price doesn't reach your level."
        ),
        mechanics=[
            "Place order with a specific limit price.",
            "Order sits in the order book until the market reaches your price.",
            "If price is reached, order fills (in order of price-time priority).",
            "If price never reaches your level, order expires unfilled.",
        ],
        formulas=[],
        examples=[
            Example(
                title="Limit buy below market",
                scenario="AAPL trading at $190. Place limit buy at $185 (wait for dip).",
                calculation="If price dips to $185, buy fills at $185. If not, order expires.",
                outcome="Price control achieved. Risk: AAPL never reaches $185 and you miss the move.",
            ),
        ],
        risks=[
            "No fill guarantee — position may not be entered.",
            "Partial fills possible (only some shares execute).",
            "Market moves away before your price is hit (opportunity cost).",
        ],
        advantages=[
            "Precise price control.",
            "You are the maker (add liquidity) → often lower fees.",
            "Useful for illiquid assets where market order would have high slippage.",
        ],
        related_ids=["market_order", "stop_loss", "take_profit"],
        tags=["limit", "order", "price control", "GTC"],
        aliases=["limit buy", "limit sell", "GTC order"],
    ),

    ConceptEntry(
        id="stop_loss",
        name="Stop Loss",
        emoji="🛑",
        category="advanced_concepts",
        summary="Automatic order to exit a position if price moves against you by a set amount.",
        definition=(
            "A stop loss is a pre-set order that automatically closes your position when the "
            "price reaches a specified 'stop' level. It limits your maximum loss on any trade. "
            "Once triggered, it typically converts to a market order (stop-market) or limit order "
            "(stop-limit). Stop losses are fundamental to risk management — position sizing and "
            "stop distance together define your maximum risk per trade."
        ),
        mechanics=[
            "Define maximum loss you're willing to accept on the trade.",
            "Set stop price below entry (for longs) or above entry (for shorts).",
            "If price reaches the stop, a sell/cover order is triggered automatically.",
            "Position is closed, limiting further loss.",
        ],
        formulas=[
            Formula(
                name="Risk per trade",
                plain="Risk = (Entry Price − Stop Price) × Quantity",
                latex=r"Risk = (P_{entry} - P_{stop}) \times Q",
                variables={},
                description="Maximum dollar loss if stopped out.",
            ),
            Formula(
                name="Position size from risk budget",
                plain="Quantity = Risk Budget / (Entry Price − Stop Price)",
                latex=r"Q = R_{budget} / (P_{entry} - P_{stop})",
                variables={"R_budget": "max $ risk per trade"},
                description="Size your position so a stop-out equals your risk budget.",
            ),
        ],
        examples=[
            Example(
                title="Stop loss on NVDA long",
                scenario="Buy NVDA at $800. Stop at $760. Max risk = $40/share. Buy 25 shares.",
                calculation="Risk = ($800 − $760) × 25 = $1,000 maximum loss.",
                outcome="If NVDA falls to $760, sell order triggers. Total loss capped at $1,000.",
            ),
        ],
        risks=[
            "Stop-hunts: market makers push price briefly below stop then reverses.",
            "Gap risk: overnight news can gap price past the stop.",
            "Stop-limit orders may not fill if market gaps past limit.",
        ],
        advantages=[
            "Hard cap on loss — essential for risk management.",
            "Removes emotion from exit decisions.",
            "Enables proper position sizing.",
        ],
        related_ids=["take_profit", "buy", "sell", "long_position", "risk_per_trade"],
        tags=["stop", "risk management", "exit", "loss protection"],
        aliases=["stop", "SL", "trailing stop", "protective stop"],
    ),

    ConceptEntry(
        id="take_profit",
        name="Take Profit",
        emoji="🎯",
        category="advanced_concepts",
        summary="Automatic order to close a position at a pre-set profit target.",
        definition=(
            "A take profit (TP) order automatically closes your position when price reaches "
            "your profit target. It locks in gains without requiring you to watch the screen. "
            "Combined with a stop loss, it defines your Risk/Reward ratio before entering a "
            "trade — a professional practice that keeps discipline in execution."
        ),
        mechanics=[
            "Set target price above entry (for longs) or below entry (for shorts).",
            "When price reaches target, a close order executes automatically.",
            "Can be a limit order (better fill) or market order (guaranteed execution).",
        ],
        formulas=[
            Formula(
                name="Risk/Reward Ratio",
                plain="R:R = (Take Profit − Entry) / (Entry − Stop Loss)",
                latex=r"R:R = (P_{TP} - P_{entry}) / (P_{entry} - P_{SL})",
                variables={},
                description="Set R:R ≥ 2:1 so winners are twice the size of losers.",
            ),
        ],
        examples=[
            Example(
                title="SPY swing trade",
                scenario="Enter SPY long at $480. Stop at $472. TP at $496.",
                calculation="Risk = $8. Reward = $16. R:R = 2:1.",
                outcome="If TP hit: +$16/share. If stop hit: −$8/share. Need >33% win rate to be profitable.",
            ),
        ],
        risks=[
            "Price may reverse just before hitting target (premature TP gives away upside).",
            "If target too tight, winners too small to overcome losers.",
        ],
        advantages=[
            "Locks in profit without emotion.",
            "Defines expected value before trade entry.",
        ],
        related_ids=["stop_loss", "limit_order", "swing_trading"],
        tags=["take profit", "TP", "target", "exit"],
        aliases=["TP", "profit target", "target order"],
    ),

    # ══════════════════════════════════════════════════════════════════
    #  ADVANCED CONCEPTS
    # ══════════════════════════════════════════════════════════════════

    ConceptEntry(
        id="margin_trading",
        name="Margin Trading",
        emoji="💳",
        category="advanced_concepts",
        summary="Trading with borrowed money from your broker to increase position size.",
        definition=(
            "Margin trading allows you to borrow capital from your broker to take positions "
            "larger than your own cash. If you have $10,000 and 2x margin, you can control "
            "$20,000 worth of assets. Margin amplifies both gains and losses proportionally. "
            "Brokers charge margin interest daily. If your equity falls below the maintenance "
            "margin requirement, you receive a margin call: add funds or positions are liquidated."
        ),
        mechanics=[
            "Deposit initial margin (your equity) with the broker.",
            "Broker lends additional capital (the margin loan).",
            "Interest is charged on the borrowed amount (daily).",
            "Profit/loss is applied to your equity — amplified by leverage.",
            "If equity falls below maintenance margin → margin call → add funds or forced liquidation.",
        ],
        formulas=[
            Formula(
                name="Equity",
                plain="Equity = Account Value − Margin Loan",
                latex=r"E_t = V_t - L",
                variables={"V_t": "current position value", "L": "margin loan"},
                description="Your net worth in the account.",
            ),
            Formula(
                name="Maintenance margin check",
                plain="Equity must be ≥ Maintenance Margin Rate × Position Value",
                latex=r"E_t \geq m \cdot N_t",
                variables={"m": "maintenance margin rate (e.g. 0.25)", "N_t": "current notional"},
                description="If violated, margin call is issued.",
            ),
        ],
        examples=[
            Example(
                title="2x margin long",
                scenario="$10,000 equity. Borrow $10,000. Buy $20,000 of AAPL at $200 (100 shares).",
                calculation="Stock rises to $220: gain = ($220−$200)×100 = $2,000. Return on equity = 20% (vs 10% unleveraged).",
                outcome="If stock falls to $180: loss = $2,000. Return = −20% on equity. Margin call risk if maintenance breached.",
            ),
        ],
        risks=[
            "Losses are amplified symmetrically with gains.",
            "Margin interest accrues daily — holding cost.",
            "Margin call forces liquidation at worst possible time.",
            "Risk of losing more than initial deposit.",
        ],
        advantages=[
            "Amplified returns on successful trades.",
            "Ability to take larger positions than cash allows.",
        ],
        related_ids=["leverage", "short_position", "liquidation_math"],
        tags=["margin", "leverage", "borrow", "amplify"],
        aliases=["margin", "trading on margin", "leveraged position"],
    ),

    ConceptEntry(
        id="leverage",
        name="Leverage",
        emoji="⚖️",
        category="advanced_concepts",
        summary="Using borrowed capital to control a position larger than your own equity.",
        definition=(
            "Leverage is the ratio of total position size to your own equity. 10x leverage "
            "means $1,000 of your capital controls $10,000 of assets. Every 1% move in the "
            "asset becomes a 10% move in your equity. Leverage does not change the Sharpe ratio "
            "of a strategy in theory (return and risk scale together), but in practice it "
            "introduces liquidation risk, funding costs, and psychological pressure."
        ),
        mechanics=[
            "Leverage = Total Notional / Own Equity.",
            "Return on equity ≈ Leverage × Asset Return.",
            "Funding cost (interest or perpetual funding) reduces net return.",
            "Margin requirements set a floor: 10x leverage = 10% margin requirement.",
        ],
        formulas=[
            Formula(
                name="Leverage ratio",
                plain="Leverage = Total Position Value / Equity",
                latex=r"L = N / E",
                variables={"N": "notional position size", "E": "own equity"},
                description="e.g. L=10 means you control 10× your capital.",
            ),
            Formula(
                name="Return on equity (approx)",
                plain="Equity Return ≈ Leverage × Asset Return − Funding Costs",
                latex=r"R_E \approx L \cdot R_{asset} - r_f",
                variables={"r_f": "funding rate"},
                description="Leverage amplifies returns and losses in equal measure.",
            ),
        ],
        examples=[
            Example(
                title="10x leveraged BTC trade",
                scenario="$1,000 equity, 10x leverage → $10,000 BTC position. BTC moves +5%.",
                calculation="Asset gain = $500. Return on equity = 50%.",
                outcome="A 10% move in BTC would wipe out entire equity (liquidation). High risk.",
            ),
        ],
        risks=[
            "10% adverse move at 10x leverage = total loss (liquidation).",
            "Funding costs erode leveraged positions held long-term.",
            "Leverage magnifies emotional reactions → poor decision making.",
        ],
        advantages=[
            "Capital efficiency — control more with less.",
            "Higher returns when correct on direction.",
        ],
        related_ids=["margin_trading", "liquidation_math", "kelly_criterion"],
        tags=["leverage", "amplify", "notional", "margin"],
        aliases=["leverage ratio", "gearing", "margin leverage"],
    ),

    ConceptEntry(
        id="hedging",
        name="Hedging",
        emoji="🛡️",
        category="advanced_concepts",
        summary="Taking an opposite position to reduce risk on an existing holding.",
        definition=(
            "Hedging is the practice of offsetting risk from one position by taking an "
            "opposing position in a correlated asset. The goal is not to maximize profit "
            "but to reduce variance and protect against adverse moves. A perfect hedge "
            "eliminates all risk but also all upside. In practice, partial hedges balance "
            "cost against protection. Common hedges: long puts, short index futures, "
            "inverse ETFs, or correlated asset shorts."
        ),
        mechanics=[
            "Identify the risk you want to reduce (market risk, FX risk, sector risk).",
            "Find a correlated instrument that moves inversely.",
            "Size the hedge to offset the relevant portion of risk.",
            "Accept that hedges cost money (premium for puts, borrow for shorts).",
        ],
        formulas=[
            Formula(
                name="Hedge ratio",
                plain="Hedge Ratio = Value to Hedge / Value of Hedge Instrument",
                latex=r"h = V_{portfolio} / V_{hedge}",
                variables={},
                description="How much of the hedge instrument to buy for given exposure.",
            ),
        ],
        examples=[
            Example(
                title="Portfolio hedge with puts",
                scenario="Own $100,000 of tech stocks. Buy SPY put options for $2,000.",
                calculation="If market crashes 20%, puts might gain $15,000. Net loss reduced from $20,000 to ~$7,000.",
                outcome="Cost: $2,000 premium (2% per year). Insurance against tail risk.",
            ),
        ],
        risks=[
            "Hedge cost reduces overall returns in bull markets.",
            "Imperfect hedges (basis risk) may not protect as expected.",
            "Over-hedging can turn a profit-seeking portfolio into a cash equivalent.",
        ],
        advantages=[
            "Reduces drawdown and portfolio variance.",
            "Protects capital in tail events.",
            "Allows holding core positions through volatility.",
        ],
        related_ids=["short_position", "options", "bear_market", "diversification"],
        tags=["hedge", "protection", "risk reduction", "puts", "insurance"],
        aliases=["hedge", "portfolio hedge", "downside protection"],
    ),

    ConceptEntry(
        id="options",
        name="Options",
        emoji="📋",
        category="advanced_concepts",
        summary="Contracts giving the right (not obligation) to buy/sell at a set price before expiry.",
        definition=(
            "An option is a derivatives contract that gives the buyer the right — but not the "
            "obligation — to buy (call) or sell (put) an underlying asset at a specific price "
            "(strike) before or on a specific date (expiry). Options are priced using models "
            "like Black-Scholes. Option buyers pay a premium; sellers collect it and take on "
            "the obligation. Options can be used for speculation, hedging, or income generation."
        ),
        mechanics=[
            "Calls: right to buy at strike (used for bullish bets or hedging short positions).",
            "Puts: right to sell at strike (used for bearish bets or hedging long positions).",
            "Premium = intrinsic value + time value.",
            "Greeks describe sensitivity: Delta (price), Gamma (delta's delta), Theta (time decay), Vega (volatility).",
        ],
        formulas=[
            Formula(
                name="Call Payoff (at expiry)",
                plain="Call Profit = max(Stock Price − Strike, 0) − Premium Paid",
                latex=r"Payoff_{call} = \max(S_T - K, 0) - c",
                variables={"S_T": "stock price at expiry", "K": "strike price", "c": "premium paid"},
                description="Buyer profits only if stock rises above strike + premium.",
            ),
            Formula(
                name="Put Payoff (at expiry)",
                plain="Put Profit = max(Strike − Stock Price, 0) − Premium Paid",
                latex=r"Payoff_{put} = \max(K - S_T, 0) - p",
                variables={"S_T": "stock price at expiry", "K": "strike price", "p": "premium paid"},
                description="Buyer profits only if stock falls below strike − premium.",
            ),
        ],
        examples=[
            Example(
                title="Long call on AAPL",
                scenario="AAPL at $180. Buy $190 call for $5 premium. Expiry in 30 days.",
                calculation="If AAPL rises to $200: payoff = max(200−190, 0) − 5 = $5. Return = 100%.",
                outcome="If AAPL stays below $190: lose entire $5 premium. Max loss = premium paid.",
            ),
        ],
        risks=[
            "Buyers can lose 100% of premium if option expires out-of-the-money.",
            "Sellers have unlimited risk (uncovered calls) or large risk (naked puts).",
            "Time decay (theta) erodes option value daily.",
        ],
        advantages=[
            "Defined risk for buyers (max loss = premium).",
            "Leverage: control 100 shares per contract for a fraction of the cost.",
            "Flexible strategies: income, speculation, hedging.",
        ],
        related_ids=["hedging", "call_option", "put_option", "volatility"],
        tags=["options", "derivatives", "calls", "puts", "premium"],
        aliases=["option", "derivatives", "calls and puts"],
    ),

    ConceptEntry(
        id="futures",
        name="Futures",
        emoji="⏱️",
        category="advanced_concepts",
        summary="Contracts obligating buy/sell of an asset at a set price on a future date.",
        definition=(
            "A futures contract is an agreement to buy or sell a specific quantity of an "
            "asset at a predetermined price on a specific future date. Unlike options, "
            "futures create an obligation — both parties must fulfill. Futures are marked "
            "to market daily (daily settlement). They are used for hedging (e.g. airlines "
            "hedging oil) and speculation. Perpetual futures (popular in crypto) have no "
            "expiry but use a funding mechanism."
        ),
        mechanics=[
            "Both buyer and seller must post initial margin.",
            "Daily mark-to-market: P&L is credited/debited to accounts each day.",
            "At expiry: physical delivery or cash settlement.",
            "Futures typically trade at a premium/discount to spot (basis).",
        ],
        formulas=[
            Formula(
                name="Futures P&L",
                plain="Profit = (Exit Price − Entry Price) × Contract Size",
                latex=r"\Pi = Q(F_{exit} - F_{entry})",
                variables={"F": "futures price", "Q": "contract multiplier"},
                description="Linear payoff — same as spot long/short but marked daily.",
            ),
            Formula(
                name="Perpetual Funding Cost",
                plain="Funding Paid = Funding Rate × Notional",
                latex=r"F_{cost} = f \cdot N",
                variables={"f": "funding rate per period (can be positive or negative)"},
                description="Perpetuals use funding to keep price near spot.",
            ),
        ],
        examples=[
            Example(
                title="S&P 500 futures hedge",
                scenario="Own $500,000 stock portfolio. Short /ES futures (S&P 500) to hedge.",
                calculation="1 /ES contract = $50 × S&P level. At 5,000: 1 contract = $250,000 exposure.",
                outcome="Need ~2 contracts to hedge $500,000 portfolio. Gains on short offset portfolio losses in crash.",
            ),
        ],
        risks=[
            "Daily mark-to-market can trigger margin calls.",
            "Leverage is very high (small margin controls large notional).",
            "Contango/backwardation: roll costs can erode returns for commodity futures.",
        ],
        advantages=[
            "Very liquid markets (ES futures trade 23h/day).",
            "Efficient hedging vehicle.",
            "No stock borrow needed for short exposure.",
        ],
        related_ids=["margin_trading", "leverage", "hedging", "options"],
        tags=["futures", "derivatives", "forward", "perpetual"],
        aliases=["futures contract", "forward", "perp", "perpetual"],
    ),

    ConceptEntry(
        id="short_squeeze",
        name="Short Squeeze",
        emoji="🚀",
        category="advanced_concepts",
        summary="Rapid price spike forcing short sellers to buy back shares, pushing price higher.",
        definition=(
            "A short squeeze occurs when a heavily shorted stock rises sharply, forcing short "
            "sellers to buy back shares to limit losses. This buying pressure drives the price "
            "even higher, which forces more shorts to cover, creating a self-reinforcing spiral. "
            "Famous examples: GameStop (GME) in 2021, Volkswagen in 2008. Short interest above "
            "20% of float indicates high squeeze potential."
        ),
        mechanics=[
            "Stock has high short interest (many shares borrowed and sold short).",
            "Positive catalyst: earnings beat, news, coordinated buying.",
            "Price rises → short sellers face losses.",
            "Short sellers buy to cover → additional buying pressure → price rises more.",
            "Cascade effect: more shorts forced to cover → parabolic price move.",
        ],
        formulas=[
            Formula(
                name="Days to Cover (short squeeze pressure)",
                plain="Days to Cover = Short Interest / Average Daily Volume",
                latex=r"DTC = SI / ADV",
                variables={"SI": "shares sold short", "ADV": "average daily share volume"},
                description="Higher DTC = more squeeze potential (shorts take longer to exit).",
            ),
        ],
        examples=[
            Example(
                title="GameStop (GME) 2021",
                scenario="GME heavily shorted. Reddit retail buyers coordinated long buying. Short interest ~140% of float.",
                calculation="GME rose from ~$20 to ~$480 in days. Melvin Capital lost ~$6.8 billion.",
                outcome="Shorts covering + new buyers = parabolic move. Most retail late-buyers then lost money on reversal.",
            ),
        ],
        risks=[
            "Short sellers face catastrophic losses in squeezes.",
            "Long buyers entering late can also lose when squeeze reverses.",
        ],
        advantages=[
            "Long holders benefit massively during squeeze.",
        ],
        related_ids=["short_position", "long_position", "volatility"],
        tags=["squeeze", "GME", "short interest", "gamma squeeze"],
        aliases=["squeeze", "gamma squeeze"],
    ),

    ConceptEntry(
        id="diversification",
        name="Diversification",
        emoji="🌐",
        category="advanced_concepts",
        summary="Spreading investments across assets to reduce idiosyncratic risk.",
        definition=(
            "Diversification reduces portfolio risk by holding assets whose returns are not "
            "perfectly correlated. When one asset falls, others may hold steady or rise, "
            "cushioning the overall portfolio. Diversification eliminates idiosyncratic "
            "(company-specific) risk but cannot eliminate systematic (market-wide) risk. "
            "The benefit diminishes after ~20–30 uncorrelated holdings."
        ),
        mechanics=[
            "Spread across different stocks, sectors, geographies, asset classes.",
            "Correlation < 1 between assets = diversification benefit.",
            "Portfolio variance reduces as assets are added (up to a limit).",
            "True diversification requires low correlation, not just many holdings.",
        ],
        formulas=[
            Formula(
                name="Portfolio Variance (2-asset)",
                plain="Var(portfolio) = w₁²σ₁² + w₂²σ₂² + 2w₁w₂ρσ₁σ₂",
                latex=r"\sigma_p^2 = w_1^2\sigma_1^2 + w_2^2\sigma_2^2 + 2w_1 w_2 \rho_{12}\sigma_1\sigma_2",
                variables={"w": "weight", "σ": "volatility", "ρ": "correlation between assets"},
                description="Lower ρ reduces portfolio variance below weighted average of individual variances.",
            ),
        ],
        examples=[
            Example(
                title="Portfolio diversification benefit",
                scenario="50% AAPL (σ=30%), 50% GLD (σ=20%), correlation ρ=0.05.",
                calculation="Portfolio σ = sqrt(0.5²×0.3² + 0.5²×0.2² + 2×0.5×0.5×0.05×0.3×0.2) ≈ 18.3%.",
                outcome="Lower risk than either asset alone. Low correlation between stocks and gold provides benefit.",
            ),
        ],
        risks=[
            "Over-diversification ('diworsification') dilutes concentrated good ideas.",
            "In crisis, correlations spike — diversification reduces when most needed.",
        ],
        advantages=[
            "Reduces idiosyncratic risk without sacrificing expected return.",
            "Smoother equity curve → lower drawdowns.",
        ],
        related_ids=["portfolio", "hedging", "buy_and_hold", "correlation"],
        tags=["diversification", "risk reduction", "correlation", "portfolio construction"],
        aliases=["diversify", "spread risk"],
    ),

    ConceptEntry(
        id="liquidity",
        name="Liquidity",
        emoji="💧",
        category="advanced_concepts",
        summary="How easily an asset can be bought or sold without moving its price.",
        definition=(
            "Liquidity describes the ease and speed with which an asset can be converted to "
            "cash at a fair price. Highly liquid assets (SPY, AAPL, BTC) can be bought or "
            "sold instantly with minimal price impact. Illiquid assets (small-cap stocks, "
            "real estate) may require time and price concessions to sell. Liquidity "
            "evaporates in crises — spreads widen dramatically."
        ),
        mechanics=[
            "Bid-ask spread: narrow spread = high liquidity.",
            "Daily volume: higher volume = higher liquidity.",
            "Market depth: large orders above/below price = deep market.",
            "In a crisis, liquidity providers withdraw → spreads widen 10–100x.",
        ],
        formulas=[
            Formula(
                name="Bid-Ask Spread",
                plain="Spread = (Ask − Bid) / Mid × 100%",
                latex=r"S\% = (A - B) / M \times 100",
                variables={"A": "ask", "B": "bid", "M": "mid = (A+B)/2"},
                description="Percentage spread is the cost of liquidity.",
            ),
        ],
        examples=[],
        risks=[
            "Illiquid positions cannot be exited quickly during crises.",
            "Large orders in illiquid markets move price against you (market impact).",
        ],
        advantages=[
            "Highly liquid assets allow quick entry/exit and tight spreads.",
        ],
        related_ids=["market_order", "spread", "volatility"],
        tags=["liquidity", "spread", "volume", "bid-ask"],
        aliases=["market depth", "tradability"],
    ),

    ConceptEntry(
        id="volatility",
        name="Volatility",
        emoji="🌊",
        category="advanced_concepts",
        summary="Statistical measure of how much an asset's price fluctuates.",
        definition=(
            "Volatility is the standard deviation of an asset's returns over a period, "
            "typically expressed as an annualized percentage. High volatility means large "
            "price swings; low volatility means stable prices. Volatility is both a risk "
            "measure and an opportunity measure. It is the key input to option pricing (VIX "
            "is the market's implied volatility of the S&P 500). Historical vol uses past "
            "data; implied vol is derived from option prices and reflects market expectations."
        ),
        mechanics=[
            "Historical volatility: std dev of log returns × sqrt(252) to annualize.",
            "Implied volatility: inferred from option prices via Black-Scholes.",
            "VIX: the 'fear gauge' — 30-day implied vol of S&P 500 options.",
        ],
        formulas=[
            Formula(
                name="Historical Volatility (annualized)",
                plain="σ_annual = σ_daily × √252",
                latex=r"\sigma_{ann} = \sigma_{daily} \times \sqrt{252}",
                variables={"σ_daily": "std dev of daily log returns"},
                description="252 trading days per year is the standard annualization factor.",
            ),
            Formula(
                name="Daily Volatility",
                plain="σ_daily = std_dev(daily log returns over window)",
                latex=r"\sigma_d = \text{std}(r_1, r_2, \ldots, r_n)",
                variables={},
                description="Compute over rolling window (21-day = 1 month is common).",
            ),
        ],
        examples=[
            Example(
                title="AAPL vs GLD volatility",
                scenario="AAPL daily σ = 1.6% → annualized σ = 1.6% × √252 ≈ 25.4%. GLD daily σ = 0.7% → 11.1% annualized.",
                calculation="AAPL is ~2.3× more volatile than gold.",
                outcome="GLD is less volatile → lower expected return but more stable in portfolio.",
            ),
        ],
        risks=[
            "High volatility = unpredictable price moves in both directions.",
            "Leveraged positions can be liquidated by volatility spikes.",
        ],
        advantages=[
            "High vol creates opportunities for options sellers and swing traders.",
            "Low vol environments suit buy-and-hold.",
        ],
        related_ids=["options", "sharpe_ratio", "var_cvar"],
        tags=["volatility", "VIX", "risk", "standard deviation"],
        aliases=["vol", "implied vol", "historical vol", "VIX"],
    ),

    # ══════════════════════════════════════════════════════════════════
    #  RISK MATH
    # ══════════════════════════════════════════════════════════════════

    ConceptEntry(
        id="var_cvar",
        name="Value at Risk & CVaR",
        emoji="📊",
        category="risk_math",
        summary="Statistical measures of potential loss at a given confidence level.",
        definition=(
            "Value at Risk (VaR) at confidence level c answers: 'With (1−c) probability, "
            "we will not lose more than X in the next N days.' For example, 95% 1-day VaR "
            "of $10,000 means there's a 5% chance of losing more than $10,000 in one day. "
            "Conditional VaR (CVaR, also called Expected Shortfall) asks: given that we "
            "ARE in the worst 5%, what is the expected loss? CVaR is a more coherent risk "
            "measure — it captures tail risk that VaR ignores."
        ),
        mechanics=[
            "Historical VaR: sort past returns, find the (1−c) quantile.",
            "Parametric VaR: assume normal distribution, use z-score.",
            "CVaR: average of all returns worse than VaR threshold.",
        ],
        formulas=[
            Formula(
                name="Historical VaR",
                plain="VaR = −(sorted_returns at (1−c)th percentile) × √horizon",
                latex=r"VaR_{c,h} = -r_{(1-c)} \cdot \sqrt{h}",
                variables={"c": "confidence (e.g. 0.95)", "h": "horizon in days"},
                description="Scale 1-day VaR to multi-day by √h (assumes independence).",
            ),
            Formula(
                name="CVaR / Expected Shortfall",
                plain="CVaR = average of all returns worse than VaR threshold",
                latex=r"CVaR_c = E[r \mid r < -VaR_c]",
                variables={},
                description="Always ≥ VaR. Captures the severity of tail losses.",
            ),
        ],
        examples=[
            Example(
                title="AAPL 1-day 95% VaR",
                scenario="AAPL daily returns over 252 days. Sort ascending. Find 5th percentile.",
                calculation="5th percentile daily return = −2.8%. VaR on $10,000 position = $280.",
                outcome="95% of days, loss ≤ $280. CVaR might be $450 (average of worst 5%).",
            ),
        ],
        risks=[
            "Historical VaR assumes the future looks like the past — fails in black swans.",
            "VaR says nothing about how bad the loss is BEYOND the threshold.",
        ],
        advantages=[
            "Industry standard risk metric for regulatory and internal reporting.",
            "Simple to interpret and communicate.",
        ],
        related_ids=["volatility", "drawdown", "sharpe_ratio"],
        tags=["VaR", "CVaR", "risk", "tail risk", "expected shortfall"],
        aliases=["VaR", "CVaR", "expected shortfall", "Value at Risk"],
    ),

    ConceptEntry(
        id="drawdown",
        name="Drawdown & Max Drawdown",
        emoji="📉",
        category="risk_math",
        summary="Peak-to-trough decline in portfolio value; max drawdown is the worst such decline.",
        definition=(
            "Drawdown measures how much a portfolio has declined from its most recent peak. "
            "If a portfolio was worth $100,000 and fell to $75,000, the drawdown is −25%. "
            "Maximum Drawdown (MDD) is the largest peak-to-trough decline over any period. "
            "It is the single most important risk metric for many traders — because it "
            "measures the worst actual experience of holding the strategy, not just volatility."
        ),
        mechanics=[
            "Track the running maximum (peak) of the equity curve.",
            "Drawdown at each point = (current value − peak) / peak.",
            "Max drawdown = minimum value of the drawdown series.",
            "Recovery time = how long to return to the previous peak.",
        ],
        formulas=[
            Formula(
                name="Drawdown at time t",
                plain="DD(t) = (E(t) − Peak(t)) / Peak(t)",
                latex=r"DD_t = (E_t - E_t^{max}) / E_t^{max}",
                variables={"E_t": "equity at time t", "E_t^max": "running maximum equity"},
                description="Always ≤ 0. Zero means at all-time high.",
            ),
            Formula(
                name="Max Drawdown",
                plain="MDD = minimum value of DD(t) over all time",
                latex=r"MDD = \min_t DD_t",
                variables={},
                description="The worst single peak-to-trough decline in history.",
            ),
        ],
        examples=[
            Example(
                title="Tech portfolio drawdown 2022",
                scenario="Portfolio: $200,000 peak in Nov 2021. Falls to $130,000 by Oct 2022.",
                calculation="Max Drawdown = ($130,000 − $200,000) / $200,000 = −35%.",
                outcome="Took until early 2024 to recover. 2+ years underwater.",
            ),
        ],
        risks=[
            "Large drawdowns require disproportionate recovery: −50% drawdown requires +100% to recover.",
            "Emotional difficulty of holding through large drawdowns often causes panic selling at the bottom.",
        ],
        advantages=[
            "Drawdown analysis reveals the true 'pain' of a strategy.",
            "Calmar ratio (return/MDD) is a drawdown-adjusted performance measure.",
        ],
        related_ids=["var_cvar", "sharpe_ratio", "bear_market"],
        tags=["drawdown", "MDD", "peak-to-trough", "underwater"],
        aliases=["MDD", "maximum drawdown", "underwater period"],
    ),

    ConceptEntry(
        id="sharpe_ratio",
        name="Sharpe Ratio",
        emoji="📐",
        category="risk_math",
        summary="Risk-adjusted return: excess return per unit of volatility.",
        definition=(
            "The Sharpe ratio measures how much return a strategy generates per unit of risk "
            "taken. It is the most widely used risk-adjusted performance metric. "
            "Sharpe = (Strategy Return − Risk-Free Rate) / Strategy Volatility. "
            "A Sharpe > 1 is good; > 2 is excellent; > 3 is exceptional. The Sortino ratio "
            "is a variant that penalizes only downside volatility. The Calmar ratio uses "
            "max drawdown instead of volatility."
        ),
        mechanics=[
            "Calculate strategy return over period.",
            "Subtract risk-free rate (T-bill yield).",
            "Divide by return volatility (std dev of returns, annualized).",
        ],
        formulas=[
            Formula(
                name="Sharpe Ratio",
                plain="Sharpe = (Mean Return − Risk-Free Rate) / Std Dev of Returns  × √252",
                latex=r"S = \frac{E[r] - r_f}{\sigma_r} \times \sqrt{252}",
                variables={"r_f": "daily risk-free rate", "σ_r": "daily return std dev"},
                description="Annualized. Multiply by √252 if using daily returns.",
            ),
            Formula(
                name="Sortino Ratio",
                plain="Sortino = (Mean Return − Risk-Free) / Downside Std Dev × √252",
                latex=r"S_{sort} = \frac{E[r] - r_f}{\sigma_{down}}",
                variables={"σ_down": "std dev of negative returns only"},
                description="Penalizes only bad volatility — preferred by many practitioners.",
            ),
            Formula(
                name="Calmar Ratio",
                plain="Calmar = Annual Return / |Max Drawdown|",
                latex=r"Calmar = R_{annual} / |MDD|",
                variables={},
                description="Higher is better. >1 is acceptable, >3 is excellent.",
            ),
        ],
        examples=[
            Example(
                title="Strategy comparison",
                scenario="Strategy A: 20% annual return, 25% vol. Strategy B: 15% return, 10% vol. RF=5%.",
                calculation="Sharpe A = (20−5)/25 = 0.60. Sharpe B = (15−5)/10 = 1.00.",
                outcome="Strategy B has better risk-adjusted returns despite lower absolute return.",
            ),
        ],
        risks=[
            "Sharpe assumes normal distribution — understates tail risk.",
            "Strategies can manipulate Sharpe by smoothing returns (illiquid asset mark-to-market).",
        ],
        advantages=[
            "Single number to compare strategies on risk-adjusted basis.",
            "Industry standard — used by institutions worldwide.",
        ],
        related_ids=["var_cvar", "drawdown", "volatility"],
        tags=["Sharpe", "Sortino", "Calmar", "risk-adjusted", "performance"],
        aliases=["Sharpe", "Sortino", "risk-adjusted return"],
    ),

    ConceptEntry(
        id="kelly_criterion",
        name="Kelly Criterion",
        emoji="🎲",
        category="risk_math",
        summary="Mathematical formula for the optimal fraction of capital to bet on each trade.",
        definition=(
            "The Kelly criterion determines the position size that maximises the long-run "
            "geometric growth rate of capital. Betting more than Kelly is mathematically "
            "guaranteed to underperform in the long run — and can cause ruin. "
            "In trading, 'half-Kelly' (bet half the Kelly fraction) is common to account "
            "for estimation error. Kelly optimizes log utility — equivalent to maximizing "
            "the expected log of wealth."
        ),
        mechanics=[
            "Estimate win probability p and loss probability q = 1−p.",
            "Estimate win payoff ratio b (average win / average loss).",
            "Compute Kelly fraction f*.",
            "In practice: use half-Kelly (f* / 2) due to estimation uncertainty.",
        ],
        formulas=[
            Formula(
                name="Kelly Fraction (binary bet)",
                plain="f* = p − q/b = (b·p − q) / b",
                latex=r"f^* = p - \frac{q}{b} = \frac{bp - q}{b}",
                variables={"p": "win probability", "q": "1−p (loss probability)",
                           "b": "win/loss ratio (avg win ÷ avg loss)"},
                description="Fraction of capital to risk. Max between 0 and 1.",
            ),
            Formula(
                name="Expected Log Growth (Kelly)",
                plain="g = p·ln(1 + f·b) + q·ln(1 − f)",
                latex=r"g = p \ln(1 + f \cdot b) + q \ln(1 - f)",
                variables={"f": "bet fraction"},
                description="Kelly maximizes g. Betting more destroys growth rate.",
            ),
            Formula(
                name="Even-odds Kelly",
                plain="f* = 2p − 1  (for 1:1 bets)",
                latex=r"f^* = 2p - 1",
                variables={},
                description="Simple case: edge in percentage form.",
            ),
        ],
        examples=[
            Example(
                title="Trading edge with Kelly",
                scenario="Strategy: win rate 55%, avg win $200, avg loss $150. b = 200/150 = 1.33.",
                calculation="f* = (1.33 × 0.55 − 0.45) / 1.33 = (0.73 − 0.45) / 1.33 ≈ 21%.",
                outcome="Bet ~21% of capital per trade (Kelly). In practice use 10.5% (half-Kelly).",
            ),
        ],
        risks=[
            "Full Kelly is very aggressive — drawdowns can be extreme.",
            "Kelly is sensitive to input errors (p and b estimates are uncertain).",
            "Never bet > Kelly: mathematically guaranteed to underperform.",
        ],
        advantages=[
            "Theoretically optimal for long-run capital growth.",
            "Prevents over-betting (which destroys compound growth).",
        ],
        related_ids=["leverage", "drawdown", "sharpe_ratio"],
        tags=["Kelly", "position sizing", "optimal bet", "edge"],
        aliases=["Kelly", "Kelly criterion", "Kelly fraction"],
    ),

    ConceptEntry(
        id="liquidation_math",
        name="Liquidation Price (Leveraged Positions)",
        emoji="💥",
        category="risk_math",
        summary="The price at which your leveraged position is forcibly closed due to margin breach.",
        definition=(
            "In leveraged trading, your broker or exchange will forcibly close your position "
            "if your equity falls below the maintenance margin requirement. The price at which "
            "this happens is the liquidation price. Knowing your liquidation price before entering "
            "a leveraged trade is essential risk management. The formula depends on your leverage, "
            "entry price, and the platform's maintenance margin rate."
        ),
        mechanics=[
            "At liquidation: your equity = maintenance margin requirement.",
            "Longs: liquidation occurs if price falls sufficiently far.",
            "Shorts: liquidation occurs if price rises sufficiently far.",
            "Maintenance margin rate (m) is set by broker (often 25% for stocks).",
        ],
        formulas=[
            Formula(
                name="Long liquidation price",
                plain="Liquidation Price ≈ Entry × (L−1) / (L × (1−m))",
                latex=r"P_{liq} = P_0 \cdot \frac{L-1}{L(1-m)}",
                variables={"L": "leverage multiplier", "m": "maintenance margin rate",
                           "P_0": "entry price"},
                description="For L=10, m=0.05: Liq = P_0 × 9/(10×0.95) = P_0 × 0.947. Liquidated at ~5% drop.",
            ),
            Formula(
                name="Short liquidation price",
                plain="Liquidation Price ≤ (Equity + Notional) / ((1+m) × Quantity)",
                latex=r"P_{liq} = \frac{E_0 + QP_0}{(1+m)Q}",
                variables={},
                description="Max price the short can reach before liquidation.",
            ),
        ],
        examples=[
            Example(
                title="10x long BTC liquidation",
                scenario="BTC at $50,000. 10x leverage. Maintenance margin = 0.5%.",
                calculation="Liq = $50,000 × (10−1) / (10 × (1−0.005)) = $50,000 × 9/9.95 ≈ $45,226.",
                outcome="A 9.5% BTC decline liquidates the position. Price volatility of 10%+ is common in BTC.",
            ),
        ],
        risks=[
            "Cascade liquidations: many traders at similar levels → price gap triggers mass liquidations.",
            "Once liquidated, you cannot recover the position.",
            "Liquidation fees add to the loss.",
        ],
        advantages=[
            "Understanding liquidation price allows safe leverage use with appropriate buffers.",
        ],
        related_ids=["leverage", "margin_trading", "short_position"],
        tags=["liquidation", "margin call", "leverage", "forced close"],
        aliases=["liquidation", "margin call", "forced liquidation"],
    ),

    # ══════════════════════════════════════════════════════════════════
    #  P&L MATH (Super-Formula)
    # ══════════════════════════════════════════════════════════════════

    ConceptEntry(
        id="pnl_super_formula",
        name="Trade P&L — The Complete Formula",
        emoji="🧮",
        category="pnl_math",
        summary="The universal P&L identity for any trade: directional gain minus costs and carry.",
        definition=(
            "Every trade's profit or loss decomposes into three components: (1) directional "
            "gain from price movement, (2) execution costs (fees, spread, slippage), and "
            "(3) carry costs (financing, borrow, funding). Understanding all three is what "
            "separates professional traders from amateurs who only think about price direction."
        ),
        mechanics=[
            "Directional: Q × (Exit Price − Entry Price). For shorts, this is naturally negative if price rises.",
            "Execution: fees, bid-ask spread, and slippage on both entry and exit.",
            "Carry: for longs on margin — interest. For shorts — borrow fees. For futures — funding.",
            "Net P&L = Directional − Execution − Carry.",
        ],
        formulas=[
            Formula(
                name="Universal Trade P&L",
                plain="P&L = [Q × (Exit − Entry)] − Fees/Spread/Slippage − Financing/Borrow/Funding",
                latex=r"\Pi = \underbrace{Q(P_{exit}-P_{entry})}_{\text{directional}} - \underbrace{C + s}_{\text{execution}} - \underbrace{b\cdot N\cdot\Delta t}_{\text{carry}}",
                variables={
                    "Q": "quantity",
                    "C": "fixed commissions",
                    "s": "slippage",
                    "b": "borrow/funding rate (annualized)",
                    "N": "notional",
                    "Δt": "holding time in years",
                },
                description="The complete trade P&L accounting for all costs.",
            ),
            Formula(
                name="Log vs Simple Returns",
                plain="Log return r = ln(P_exit / P_entry). Simple return R = (P_exit − P_entry) / P_entry. Relation: R = e^r − 1",
                latex=r"r = \ln(P_t/P_0),\quad R = e^r - 1",
                variables={},
                description="Log returns add across time. Simple returns multiply. Quants prefer log.",
            ),
        ],
        examples=[
            Example(
                title="Full P&L breakdown: long stock",
                scenario="Buy 100 NVDA at $700. Sell at $730. Commission: $2 each side. Borrowed on margin at 6% annual. Held 10 days.",
                calculation=(
                    "Directional = ($730 − $700) × 100 = $3,000\n"
                    "Commission = 2 × $2 = $4\n"
                    "Margin interest = $700 × 100 × 0.5 × (6%/365 × 10) = $57.53\n"
                    "Net P&L = $3,000 − $4 − $57.53 = $2,938.47"
                ),
                outcome="Net $2,938 profit. Without costs: $3,000. Costs = $61.53 (2% of profit). Small but compounds.",
            ),
        ],
        risks=[
            "Ignoring carry costs overestimates actual profitability.",
            "Slippage on large orders in illiquid markets can dwarf commissions.",
        ],
        advantages=[
            "Forces complete thinking about all profit drivers.",
        ],
        related_ids=["buy", "short_position", "margin_trading", "futures"],
        tags=["P&L", "profit", "loss", "formula", "costs", "carry"],
        aliases=["P&L formula", "profit and loss", "PnL"],
    ),

]


# ---------------------------------------------------------------------------
# Knowledge Base Index
# ---------------------------------------------------------------------------

class FinanceKnowledgeBase:
    """
    Searchable index over all financial concepts.

    Usage:
        from atlas.shared.finance_concepts import FINANCE_KB

        entry = FINANCE_KB.lookup("short selling")
        results = FINANCE_KB.search("kelly")
        category = FINANCE_KB.by_category("risk_math")
    """

    def __init__(self, concepts: List[ConceptEntry]):
        self._by_id:    Dict[str, ConceptEntry] = {c.id: c for c in concepts}
        self._all:      List[ConceptEntry] = concepts

        # Build alias → id map
        self._alias_map: Dict[str, str] = {}
        for c in concepts:
            self._alias_map[c.id.lower()] = c.id
            self._alias_map[c.name.lower()] = c.id
            for alias in c.aliases:
                self._alias_map[alias.lower()] = c.id

    # ------------------------------------------------------------------
    # Primary lookup — fuzzy
    # ------------------------------------------------------------------

    def lookup(self, term: str) -> Optional[ConceptEntry]:
        """
        Find a concept by any name, alias, or partial match.

        Returns the best match or None.
        """
        t = term.strip().lower()

        # 1. Exact alias/id match
        if t in self._alias_map:
            return self._by_id[self._alias_map[t]]

        # 2. Partial match on id or name
        for c in self._all:
            if t in c.id.lower() or t in c.name.lower():
                return c

        # 3. Tag match
        matches = [c for c in self._all if any(t in tag.lower() for tag in c.tags)]
        if matches:
            return matches[0]

        return None

    def search(self, query: str) -> List[ConceptEntry]:
        """
        Return all concepts matching a query (name, alias, tag, or summary).
        """
        q = query.strip().lower()
        results = []
        seen = set()

        for c in self._all:
            if c.id in seen:
                continue
            if (q in c.id.lower()
                    or q in c.name.lower()
                    or q in c.summary.lower()
                    or any(q in tag for tag in c.tags)
                    or any(q in alias.lower() for alias in c.aliases)):
                results.append(c)
                seen.add(c.id)

        return results

    def by_category(self, category: str) -> List[ConceptEntry]:
        return [c for c in self._all if c.category == category]

    def all_ids(self) -> List[str]:
        return list(self._by_id.keys())

    def categories(self) -> List[str]:
        return sorted(set(c.category for c in self._all))

    def __len__(self) -> int:
        return len(self._all)

    def __repr__(self) -> str:
        cats = {}
        for c in self._all:
            cats[c.category] = cats.get(c.category, 0) + 1
        return f"FinanceKnowledgeBase({len(self._all)} concepts: {cats})"


# ---------------------------------------------------------------------------
# Format helpers (for ARIA's responses)
# ---------------------------------------------------------------------------

def format_summary(entry: ConceptEntry) -> str:
    """One-line summary for inline reference."""
    return f"{entry.emoji} **{entry.name}**: {entry.summary}"


def format_full(entry: ConceptEntry, include_math: bool = True) -> str:
    """
    Full formatted explanation for ARIA's 'expand' responses.
    Returns markdown string.
    """
    lines = []
    lines.append(f"## {entry.emoji} {entry.name}")
    lines.append(f"*Category: {entry.category.replace('_', ' ').title()}*\n")
    lines.append(f"**TL;DR:** {entry.summary}\n")

    lines.append("### Definition")
    lines.append(entry.definition + "\n")

    if entry.mechanics:
        lines.append("### How it Works")
        for i, step in enumerate(entry.mechanics, 1):
            lines.append(f"{i}. {step}")
        lines.append("")

    if include_math and entry.formulas:
        lines.append("### Key Formulas")
        for f in entry.formulas:
            lines.append(f"**{f.name}**")
            lines.append(f"```\n{f.plain}\n```")
            if f.variables:
                var_str = " | ".join(f"{k} = {v}" for k, v in f.variables.items())
                lines.append(f"*Variables: {var_str}*")
            if f.description:
                lines.append(f"> {f.description}")
            lines.append("")

    if entry.examples:
        lines.append("### Worked Examples")
        for ex in entry.examples:
            lines.append(f"**{ex.title}**")
            lines.append(f"*Setup:* {ex.scenario}")
            lines.append(f"*Calculation:*\n```\n{ex.calculation}\n```")
            lines.append(f"*Result:* {ex.outcome}\n")

    if entry.risks:
        lines.append("### Risks ⚠️")
        for r in entry.risks:
            lines.append(f"- {r}")
        lines.append("")

    if entry.advantages:
        lines.append("### Advantages ✅")
        for a in entry.advantages:
            lines.append(f"- {a}")
        lines.append("")

    if entry.related_ids:
        lines.append("### Related Concepts")
        related_names = [entry.name if eid == entry.id else eid.replace("_", " ").title()
                         for eid in entry.related_ids]
        lines.append(", ".join(f"`{n}`" for n in entry.related_ids))
        lines.append("")

    return "\n".join(lines)


def format_math_only(entry: ConceptEntry) -> str:
    """Return only the formulas section."""
    if not entry.formulas:
        return f"No formulas defined for **{entry.name}**."

    lines = [f"## {entry.emoji} {entry.name} — Formulas"]
    for f in entry.formulas:
        lines.append(f"### {f.name}")
        lines.append(f"```\n{f.plain}\n```")
        if f.variables:
            for var, desc in f.variables.items():
                lines.append(f"- `{var}` = {desc}")
        if f.description:
            lines.append(f"\n> {f.description}")
        lines.append("")
    return "\n".join(lines)


# Global singleton
FINANCE_KB = FinanceKnowledgeBase(_CONCEPTS)
