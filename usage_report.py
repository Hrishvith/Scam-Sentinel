"""Summarise Gnani credit use from usage_ledger.jsonl (offline, no credits).

  python usage_report.py
  python usage_report.py --calibrate tts --drop 4.2          # derive a rate from the dashboard
  python usage_report.py --calibrate stt --drop 1.5 --write  # ...and save it to rates.json

--drop is how many credits the dashboard Usage page showed for the most recent real call(s)
of that kind (--last N, default 1).
"""
from __future__ import annotations

import argparse
import json
import sys

from budget import KINDS, Budget, cost, load_rates, rates_path, read_ledger


def report(budget: Budget) -> str:
    rates = load_rates(budget.rates_file)
    rows = read_ledger(budget.ledger_file)
    lines = [f"{'kind':<10} {'calls':>6} {'cached':>7} {'units billed':>16} {'est. credits':>13}"]
    for kind, (field, key, per, _) in KINDS.items():
        real = [r for r in rows if r.get("kind") == kind and not r.get("cache_hit")]
        hits = sum(1 for r in rows if r.get("kind") == kind and r.get("cache_hit"))
        units = sum(float(r.get(field) or 0) for r in real)
        c = cost(kind, units, rates)
        unit = "s audio" if field == "audio_seconds" else "chars"
        lines.append(f"{kind:<10} {len(real):>6} {hits:>7} {units:>10.1f} {unit:<5} "
                     f"{'unmeasured' if c is None else f'{c:.2f}':>13}")
    start = float(rates["starting_credits"])
    reserve = start * float(rates["reserve_fraction"])
    spent, unmeasured = budget.totals()
    lines += ["",
              f"starting credits   {start:10.1f}",
              f"estimated spent    {spent:10.1f}",
              f"estimated balance  {start - spent:10.1f}",
              f"reserve ({rates['reserve_fraction']:.0%})      {reserve:10.1f}",
              f"spendable now      {max(0.0, start - spent - reserve):10.1f}"]
    missing = [k for k in KINDS if rates.get(KINDS[k][1]) is None]
    if missing:
        lines.append(f"\nUnmeasured rates: {', '.join(missing)}. Spend on these is NOT in the estimate "
                     f"({', '.join(f'{k}: {unmeasured[k]:.1f}' for k in missing)} units so far).")
    lines.append("Compare 'estimated balance' with the dashboard Usage page; the dashboard wins.")
    return "\n".join(lines)


def calibrate(budget: Budget, kind: str, drop: float, last: int) -> float:
    """Rate implied by `drop` credits over the last `last` real calls of `kind`."""
    field, key, per, _ = KINDS[kind]
    real = [r for r in read_ledger(budget.ledger_file) if r.get("kind") == kind and not r.get("cache_hit")]
    if len(real) < last:
        raise SystemExit(f"Only {len(real)} real {kind} call(s) in the ledger; need {last}.")
    units = sum(float(r.get(field) or 0) for r in real[-last:])
    if units <= 0:
        raise SystemExit("Those calls logged zero units; cannot derive a rate.")
    return drop / units * per


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--calibrate", choices=list(KINDS))
    ap.add_argument("--drop", type=float, help="credits the dashboard showed for those call(s)")
    ap.add_argument("--last", type=int, default=1)
    ap.add_argument("--write", action="store_true", help="save the derived rate to rates.json")
    args = ap.parse_args(argv)
    budget = Budget()

    if args.calibrate:
        if args.drop is None:
            ap.error("--calibrate needs --drop")
        rate = calibrate(budget, args.calibrate, args.drop, args.last)
        key = KINDS[args.calibrate][1]
        print(f"{key} = {rate:.6g}")
        if args.write:
            path = budget.rates_file
            data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
            data[key] = round(rate, 6)
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"saved to {path}")
        return
    print(report(budget))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
