"""
horizonx-tracker demo — simulates a regime classifier backtest.

Run:
    python examples/demo.py
    streamlit run dashboard/app.py
"""
import json
import math
import pathlib
import random
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
import tracker


def run_backtest(config: dict, regime: str) -> None:
    with tracker.start_run(
        name=f"regime-{regime}",
        tags={"regime": regime, "universe": "US_equities", "framework": "HorizonX"},
    ) as run:
        run.log_params(config)

        # Simulate monthly rebalancing decisions over 24 months
        equity = 1.0
        for month in range(24):
            monthly_return = random.gauss(
                0.008 if regime == "expansion" else -0.005,
                0.03,
            )
            equity *= 1 + monthly_return

            sharpe = (monthly_return - 0.004) / 0.03
            drawdown = min(0.0, monthly_return - 0.01)

            run.log_metric("monthly_return", monthly_return, step=month)
            run.log_metric("equity_curve", equity, step=month)
            run.log_metric("sharpe", sharpe, step=month)
            run.log_metric("drawdown", drawdown, step=month)

        # Final summary metrics (no step — logged once)
        annualised_return = equity ** (12 / 24) - 1
        run.log_metric("annualised_return", annualised_return)
        run.log_metric("final_equity", equity)

        # Save a fake model checkpoint as an artifact
        tmp = pathlib.Path(tempfile.mkdtemp()) / "regime_model.json"
        tmp.write_text(json.dumps({"regime": regime, "config": config}, indent=2))
        run.log_artifact(str(tmp), name="regime_model.json")

        print(f"[{regime:>12}]  run_id={run.run_id[:8]}  "
              f"final_equity={equity:.3f}  annualised_return={annualised_return:.2%}")


if __name__ == "__main__":
    random.seed(42)

    configs = [
        {"lookback": 60,  "threshold": 0.65, "rebalance_freq": "monthly"},
        {"lookback": 120, "threshold": 0.70, "rebalance_freq": "monthly"},
        {"lookback": 60,  "threshold": 0.55, "rebalance_freq": "weekly"},
    ]
    regimes = ["expansion", "contraction", "expansion"]

    print("Running regime classifier backtests...\n")
    for config, regime in zip(configs, regimes):
        run_backtest(config, regime)

    print(f"\nDone. Launch dashboard with: streamlit run dashboard/app.py")
