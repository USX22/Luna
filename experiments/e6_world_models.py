"""E6: JEPA vs. generative prediction in a world of coupled oscillators.

    pip install -e ".[mundo]"
    python experiments/e6_world_models.py                      # full sweep (GPU recommended)
    python experiments/e6_world_models.py --pasos 300 --semillas 0   # quick pilot

See docs/investigacion/modelos_de_mundo.md for hypotheses (registered beforehand).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from ia.worldmodel.data import make_world, targets
from ia.worldmodel.evaluate import identifiable, recover_K, ridge_probe
from ia.worldmodel.models import KINDS, encode, train_encoder


def run(kind: str, sigma: float, seed: int, args) -> dict:
    kw = {"distractor_std": sigma, "distractor_kind": args.tipo}
    train = make_world(args.n_train, args.T, seed=1000 + seed, **kw)
    probe = make_world(args.n_probe, args.T, seed=2000 + seed, **kw)
    test = make_world(args.n_probe, args.T, seed=3000 + seed, **kw)
    ood = make_world(args.n_probe, args.T, seed=4000 + seed, K_range=(1.5, 3.0), **kw)
    t0 = time.time()
    enc, losses = train_encoder(kind, train.x, window=args.ventana, horizon=args.horizonte,
                                steps=args.pasos, seed=seed)
    w = args.ventana
    Zp, Zt, Zo = (encode(enc, d.x, w) for d in (probe, test, ood))
    Yp, Yt, Yo = (targets(d.phases)[:, w - 1:] for d in (probe, test, ood))
    r2, pred = ridge_probe(Zp, Yp, Zt, Yt)
    r2_ood, pred_ood = ridge_probe(Zp, Yp, Zo, Yo)
    return {"modelo": kind, "tipo": args.tipo, "sigma_distractor": sigma, "semilla": seed,
            "r2": round(r2, 4), "r2_ood": round(r2_ood, 4),
            "ley_K_corr": round(recover_K(pred, test.K, test.dt, identifiable(test.phases)), 4),
            "ley_K_corr_ood": round(recover_K(pred_ood, ood.K, ood.dt, identifiable(ood.phases)), 4),
            "n_identificables": int(identifiable(test.phases).sum()),
            "z_std": round(float(Zt.std(axis=(0, 1)).mean()), 4),
            "loss_final": round(float(np.mean(losses[-50:])), 5) if losses else None,
            "segundos": round(time.time() - t0, 1)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--modelos", nargs="+", default=list(KINDS), choices=list(KINDS))
    ap.add_argument("--distractores", type=float, nargs="+", default=[0.0, 1.0, 3.0])
    ap.add_argument("--semillas", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--tipo", choices=["ruido", "estructurado"], default="ruido",
                    help="distractor: ruido blanco (E6) o dinámica predecible e irrelevante (E6b)")
    ap.add_argument("--pasos", type=int, default=3000)
    ap.add_argument("--n-train", type=int, default=512)
    ap.add_argument("--n-probe", type=int, default=128)
    ap.add_argument("--T", type=int, default=120)
    ap.add_argument("--ventana", type=int, default=4)
    ap.add_argument("--horizonte", type=int, default=5)
    ap.add_argument("--out", default="results/e6")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"e6_{int(time.time())}.jsonl"
    rows = []
    with path.open("w") as fh:
        for sigma in args.distractores:
            for seed in args.semillas:
                for kind in args.modelos:
                    r = run(kind, sigma, seed, args)
                    rows.append(r)
                    fh.write(json.dumps(r) + "\n")
                    fh.flush()
                    print(f"σ={sigma:<4} semilla={seed} {kind:<12} R²={r['r2']:.3f} "
                          f"R²ood={r['r2_ood']:.3f} ley-K r={r['ley_K_corr']:.2f} ({r['segundos']}s)")
    print("\nMedias por modelo y σ (R² · R² fuera de distribución · correlación de K recuperada):")
    for sigma in args.distractores:
        for kind in args.modelos:
            rs = [r for r in rows if r["modelo"] == kind and r["sigma_distractor"] == sigma]
            m = lambda k: np.mean([r[k] for r in rs])  # noqa: E731
            print(f"  σ={sigma:<4} {kind:<12} {m('r2'):.3f} · {m('r2_ood'):.3f} · {m('ley_K_corr'):.2f}")
    print(f"Resultados en {path}")


if __name__ == "__main__":
    main()
