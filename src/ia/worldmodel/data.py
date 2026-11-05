"""A toy world: two coupled phase oscillators (Kuramoto) seen through mixed sensors.

Hidden state: phases theta_1, theta_2 with per-sequence omega_1, omega_2 and coupling K:
    d theta_i / dt = omega_i + K sin(theta_j - theta_i)
Observations: D channels. Most are a fixed nonlinear mixture of the oscillators (like EEG
electrodes mixing sources); `n_distractors` channels are unpredictable white noise of
std `distractor_std` (detail a good world model should ignore).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class World:
    x: np.ndarray       # (n, T, D) observations
    phases: np.ndarray  # (n, T, 2)
    omega: np.ndarray   # (n, 2)
    K: np.ndarray       # (n,)
    dt: float


def simulate(n: int, T: int, rng: np.random.Generator, dt: float = 0.05,
             K_range=(0.0, 1.5), omega_range=(0.5, 2.0), phase_noise: float = 0.02):
    omega = rng.uniform(*omega_range, size=(n, 2))
    K = rng.uniform(*K_range, size=n)
    theta = np.zeros((n, T, 2))
    theta[:, 0] = rng.uniform(0, 2 * np.pi, size=(n, 2))
    for t in range(1, T):
        th = theta[:, t - 1]
        diff = th[:, ::-1] - th                        # theta_j - theta_i
        dtheta = omega + K[:, None] * np.sin(diff)
        theta[:, t] = th + dt * dtheta + phase_noise * np.sqrt(dt) * rng.normal(size=(n, 2))
    return theta, omega, K


def features(phases: np.ndarray) -> np.ndarray:
    """sin/cos of each phase: the 4 'true' latent variables."""
    return np.concatenate([np.sin(phases), np.cos(phases)], axis=-1)


def targets(phases: np.ndarray) -> np.ndarray:
    """What a good abstraction should contain: each phase and the phase difference."""
    d = phases[..., 1] - phases[..., 0]
    return np.concatenate([features(phases), np.stack([np.sin(d), np.cos(d)], -1)], axis=-1)


def structured_distractor(n: int, T: int, rng: np.random.Generator, n_channels: int,
                          dt: float = 0.05, mixing_seed: int = 0) -> np.ndarray:
    """Predictable but irrelevant: two fast, independent oscillators mixed into channels."""
    omega = rng.uniform(3.0, 6.0, size=(n, 2))
    phase0 = rng.uniform(0, 2 * np.pi, size=(n, 2))
    t = np.arange(T) * dt
    ph = phase0[:, None, :] + omega[:, None, :] * t[None, :, None]
    feats = np.concatenate([np.sin(ph), np.cos(ph), np.sin(2 * ph), np.cos(2 * ph)], -1)
    W = np.random.default_rng(mixing_seed + 1).normal(size=(feats.shape[-1], n_channels))
    out = feats @ W
    return out / out.std()


def sensors(phases: np.ndarray, rng: np.random.Generator, D: int = 32, n_distractors: int = 8,
            distractor_std: float = 0.0, noise_std: float = 0.05, mixing_seed: int = 0,
            distractor_kind: str = "ruido", dt: float = 0.05) -> np.ndarray:
    mix = np.random.default_rng(mixing_seed)          # same sensor layout for every split
    W = mix.normal(size=(4, D - n_distractors))
    b = mix.normal(scale=0.5, size=D - n_distractors)
    signal = np.tanh(features(phases) @ W + b)
    signal += noise_std * rng.normal(size=signal.shape)
    if distractor_kind == "estructurado":
        n, T = phases.shape[:2]
        distract = distractor_std * structured_distractor(n, T, rng, n_distractors, dt, mixing_seed)
    else:
        distract = distractor_std * rng.normal(size=phases.shape[:2] + (n_distractors,))
    return np.concatenate([signal, distract], axis=-1).astype(np.float32)


def make_world(n: int, T: int, seed: int, distractor_std: float = 0.0,
               K_range=(0.0, 1.5), D: int = 32, n_distractors: int = 8, dt: float = 0.05,
               distractor_kind: str = "ruido") -> World:
    rng = np.random.default_rng(seed)
    phases, omega, K = simulate(n, T, rng, dt=dt, K_range=K_range)
    x = sensors(phases, rng, D=D, n_distractors=n_distractors, distractor_std=distractor_std,
                distractor_kind=distractor_kind, dt=dt)
    return World(x, phases, omega, K, dt)
