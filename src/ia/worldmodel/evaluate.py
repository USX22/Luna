"""Linear probes (abstraction) and symbolic law extraction (latent -> symbols)."""
from __future__ import annotations

import numpy as np


def ridge_probe(Z_tr: np.ndarray, Y_tr: np.ndarray, Z_te: np.ndarray, Y_te: np.ndarray,
                alpha: float = 1e-2) -> tuple[float, np.ndarray]:
    """Fit a linear readout on train, return (mean R2 on test, test predictions)."""
    Z_tr, Z_te = Z_tr.reshape(-1, Z_tr.shape[-1]), Z_te.reshape(-1, Z_te.shape[-1])
    shape = Y_te.shape
    Y_tr, Y_te = Y_tr.reshape(-1, Y_tr.shape[-1]), Y_te.reshape(-1, Y_te.shape[-1])
    mu, sd = Z_tr.mean(0), Z_tr.std(0) + 1e-8
    A = np.c_[(Z_tr - mu) / sd, np.ones(len(Z_tr))]
    B = np.c_[(Z_te - mu) / sd, np.ones(len(Z_te))]
    coef = np.linalg.solve(A.T @ A + alpha * np.eye(A.shape[1]), A.T @ Y_tr)
    pred = B @ coef
    ss_res = ((Y_te - pred) ** 2).sum(0)
    ss_tot = ((Y_te - Y_te.mean(0)) ** 2).sum(0) + 1e-12
    return float(np.mean(1 - ss_res / ss_tot)), pred.reshape(shape)


def fit_law(dphase: np.ndarray, dt: float) -> tuple[float, float]:
    """Sparse-regression (SINDy-style) fit of d(dphase)/dt = a + b sin(dphase) + c cos(dphase).

    For two Kuramoto oscillators the true law is  d(dphase)/dt = d_omega - 2K sin(dphase),
    so K_hat = -b / 2 and d_omega_hat = a. Returns (K_hat, d_omega_hat).
    """
    u = np.unwrap(dphase)
    deriv = np.gradient(u, dt)
    lib = np.c_[np.ones_like(u), np.sin(u), np.cos(u)]
    coef, *_ = np.linalg.lstsq(lib, deriv, rcond=None)
    coef[np.abs(coef) < 0.05] = 0.0  # sparsity threshold
    return float(-coef[1] / 2), float(coef[0])


def identifiable(phases: np.ndarray, threshold: float = 0.3) -> np.ndarray:
    """Sequences whose phase difference explores enough to identify K.

    When the oscillators phase-lock, d(dphase)/dt ~ 0 and sin(dphase) is ~constant, so K
    cannot be separated from d_omega: no method could recover it from that data.
    """
    d = phases[..., 1] - phases[..., 0]
    return np.std(np.sin(d), axis=1) > threshold


def recover_K(pred_targets: np.ndarray, K_true: np.ndarray, dt: float,
              mask: np.ndarray | None = None) -> float:
    """Correlation between true K and K recovered from decoded phase differences,
    over the identifiable sequences (`mask`)."""
    dphase = np.arctan2(pred_targets[..., 4], pred_targets[..., 5])
    K_hat = np.array([fit_law(d, dt)[0] for d in dphase])
    if mask is not None:
        K_hat, K_true = K_hat[mask], K_true[mask]
    if len(K_hat) < 3 or np.std(K_hat) < 1e-9:
        return 0.0
    return float(np.corrcoef(K_hat, K_true)[0, 1])
