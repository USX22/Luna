"""Encoders trained with different objectives, same architecture and budget.

- jepa:        predict the *latent* of a future window (EMA target encoder, VICReg-style
               variance/covariance terms against collapse).
- generativo:  predict the future *observation* x(t+k).
- autoencoder: reconstruct the current window.
- aleatorio:   untrained encoder (baseline).
Encoders read a short window of frames, so velocities (omega, K) are inferable.
"""
from __future__ import annotations

import copy

import numpy as np
import torch
from torch import nn

KINDS = ("jepa", "generativo", "autoencoder", "aleatorio")


def mlp(i: int, h: int, o: int) -> nn.Module:
    return nn.Sequential(nn.Linear(i, h), nn.GELU(), nn.Linear(h, h), nn.GELU(), nn.Linear(h, o))


def windows(x: np.ndarray, w: int) -> np.ndarray:
    """(n, T, D) -> (n, T-w+1, w*D): window ending at each time t >= w-1."""
    n, T, D = x.shape
    idx = np.arange(w)[None, :] + np.arange(T - w + 1)[:, None]
    return x[:, idx].reshape(n, T - w + 1, w * D)


def var_cov_loss(z: torch.Tensor) -> torch.Tensor:
    z = z - z.mean(0)
    std = torch.sqrt(z.var(0) + 1e-4)
    var_term = torch.relu(1 - std).mean()
    cov = (z.T @ z) / (len(z) - 1)
    off = cov - torch.diag(torch.diag(cov))
    return var_term + (off ** 2).sum() / z.shape[1]


def train_encoder(kind: str, x: np.ndarray, window: int = 4, horizon: int = 5, z_dim: int = 16,
                  hidden: int = 128, steps: int = 1500, batch: int = 256, lr: float = 1e-3,
                  seed: int = 0, device: str | None = None) -> tuple[nn.Module, list[float]]:
    if kind not in KINDS:
        raise ValueError(kind)
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    W = windows(x, window)                          # (n, T', w*D)
    n, Tw, din = W.shape
    D = x.shape[-1]
    enc = mlp(din, hidden, z_dim).to(device)
    if kind == "aleatorio":
        return enc.eval(), []
    head_out = {"jepa": z_dim, "generativo": D, "autoencoder": din}[kind]
    head = mlp(z_dim, hidden, head_out).to(device)
    target = copy.deepcopy(enc).requires_grad_(False) if kind == "jepa" else None
    opt = torch.optim.AdamW(list(enc.parameters()) + list(head.parameters()), lr=lr)
    Wt = torch.tensor(W, device=device)
    Xt = torch.tensor(x, device=device)
    losses = []
    for _ in range(steps):
        s = torch.as_tensor(rng.integers(0, n, batch), device=device)
        t = torch.as_tensor(rng.integers(0, Tw - horizon, batch), device=device)
        z = enc(Wt[s, t])
        if kind == "jepa":
            with torch.no_grad():
                zt = target(Wt[s, t + horizon])
            loss = ((head(z) - zt) ** 2).mean() + var_cov_loss(z)
        elif kind == "generativo":
            frame = Xt[s, t + window - 1 + horizon]   # observation `horizon` steps ahead
            loss = ((head(z) - frame) ** 2).mean()
        else:
            loss = ((head(z) - Wt[s, t]) ** 2).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
        if target is not None:
            with torch.no_grad():
                for pt, pe in zip(target.parameters(), enc.parameters()):
                    pt.mul_(0.99).add_(pe, alpha=0.01)
        losses.append(float(loss.detach()))
    return enc.eval(), losses


@torch.no_grad()
def encode(enc: nn.Module, x: np.ndarray, window: int = 4) -> np.ndarray:
    W = windows(x, window)
    dev = next(enc.parameters()).device
    n, Tw, din = W.shape
    Z = enc(torch.tensor(W.reshape(-1, din), device=dev)).cpu().numpy()
    return Z.reshape(n, Tw, -1)
