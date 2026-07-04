from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_web_dashboard_does_not_present_fake_personal_finances() -> None:
    source = _read("ui_web/src/components/Dashboard.jsx")

    assert "$2,450,890.00" not in source
    assert "$1.2M" not in source
    assert "$400K" not in source
    assert "$1.6M" not in source
    assert "No portfolio data" in source
    assert "/api/portfolio" in source


def test_legacy_portfolio_seed_is_not_activated() -> None:
    source = _read("apps/desktop/finance.js")

    assert "seedPortfolio();" not in source
    assert "retireLegacySeedPortfolio();" in source
    assert "atlas_archived_demo_portfolio_" in source


def test_paper_trading_never_labels_synthetic_ticks_as_live() -> None:
    source = _read("apps/desktop/paper_trading.js")

    assert "Live prices" not in source
    assert "live price'" not in source
    assert "PAPER SIMULATION" in source
    assert "Math.random()" in source  # allowed only because the mode is explicit


def test_decision_center_has_no_invented_default_capital() -> None:
    source = _read("apps/desktop/decision.js")

    assert "let _capital       = 100_000" not in source
    assert 'id="dec-capital" value="0"' in source
    assert "Approval blocked" in source
