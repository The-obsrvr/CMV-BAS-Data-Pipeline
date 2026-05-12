"""
sample_threads.py — Random sample of N threads from a JSONL file.

Usage:
    python sample_threads.py
    python sample_threads.py --input Data/filtered_threads.jsonl --n 500
    python sample_threads.py --n 500 --delta-ratio 0.5 --seed 42
    python sample_threads.py --n 500 --output Data/sample_500.jsonl \
           --remainder Data/remainder.jsonl

"""
import json
import random
import argparse
from pathlib import Path

def sample_threads(
        input_path: Path,
        output_path: Path,
        n: int = 500,
        seed: int = 42,
        delta_ratio: float = 0.5,
        remainder_path: Path = None,
        ) -> None:
    # Load and split into strata
    delta_pool: list[dict] = []
    non_delta_pool: list[dict] = []

    with open(input_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            thread = json.loads(line)
            if thread.get("is_delta", False):
                delta_pool.append(thread)
            else:
                non_delta_pool.append(thread)

    total = len(delta_pool) + len(non_delta_pool)
    print(f"Loaded {total} threads  (delta={len(delta_pool)}  non-delta={len(non_delta_pool)})")

    if n > total:
        print(f"Warning: requested {n} but only {total} available — sampling all")
        n = total

    random.seed(seed)

    # Compute per-stratum quotas
    n_delta = round(n * delta_ratio)
    n_non_delta = n - n_delta

    # Clamp to available pool sizes and redistribute deficit
    if n_delta > len(delta_pool):
        deficit = n_delta - len(delta_pool)
        n_delta = len(delta_pool)
        n_non_delta = min(n_non_delta + deficit, len(non_delta_pool))

    if n_non_delta > len(non_delta_pool):
        deficit = n_non_delta - len(non_delta_pool)
        n_non_delta = len(non_delta_pool)
        n_delta = min(n_delta + deficit, len(delta_pool))

    print(f"Sampling  delta={n_delta}  non-delta={n_non_delta}  total={n_delta + n_non_delta}")

    # Sample each stratum
    sampled_delta = random.sample(delta_pool, n_delta)
    sampled_non_delta = random.sample(non_delta_pool, n_non_delta)
    sampled = sampled_delta + sampled_non_delta

    # Shuffle so delta and non-delta are interleaved in output
    random.shuffle(sampled)

    # Use id-based sets for correct remainder computation
    sampled_delta_ids = {id(t) for t in sampled_delta}
    sampled_non_delta_ids = {id(t) for t in sampled_non_delta}
    remainder = (
            [t for t in delta_pool if id(t) not in sampled_delta_ids] +
            [t for t in non_delta_pool if id(t) not in sampled_non_delta_ids]
    )

    # ── Write sample ───────────────────────────────────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for thread in sampled:
            f.write(json.dumps(thread, ensure_ascii=False) + "\n")

    actual_delta = sum(1 for t in sampled if t.get("is_delta", False))
    actual_non_delta = len(sampled) - actual_delta
    print(f"Wrote {len(sampled)} threads → {output_path}")
    print(f"  delta={actual_delta} ({100 * actual_delta / len(sampled):.1f}%)  "
          f"non-delta={actual_non_delta} ({100 * actual_non_delta / len(sampled):.1f}%)"
          )

    # ── Write remainder ────────────────────────────────────────────────────────
    if remainder_path:
        remainder_path.parent.mkdir(parents=True, exist_ok=True)
        with open(remainder_path, "w", encoding="utf-8") as f:
            for thread in remainder:
                f.write(json.dumps(thread, ensure_ascii=False) + "\n")
        rem_delta = sum(1 for t in remainder if t.get("is_delta", False))
        rem_non_delta = len(remainder) - rem_delta
        print(f"Wrote {len(remainder)} remainder threads → {remainder_path}")
        print(f"  delta={rem_delta}  non-delta={rem_non_delta}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stratified sample of N threads balanced on delta/non-delta"
        )
    parser.add_argument("--input", "-i", default="Data/filtered_threads.jsonl",
                        help="Input JSONL (default: Data/filtered_threads.jsonl)"
                        )
    parser.add_argument("--output", "-o", default="Data/sample_500.jsonl",
                        help="Output JSONL (default: Data/sample_500.jsonl)"
                        )
    parser.add_argument("--n", type=int, default=500,
                        help="Total threads to sample (default: 500)"
                        )
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)"
                        )
    parser.add_argument("--delta-ratio", type=float, default=0.5,
                        help="Fraction of sample that should be delta (default: 0.5)"
                        )
    parser.add_argument("--remainder", default=None,
                        help="Optional path to write unsampled threads"
                        )
    args = parser.parse_args()

    sample_threads(
        input_path=Path(args.input),
        output_path=Path(args.output),
        n=args.n,
        seed=args.seed,
        delta_ratio=args.delta_ratio,
        remainder_path=Path(args.remainder) if args.remainder else None,
        )


if __name__ == "__main__":
    main()
