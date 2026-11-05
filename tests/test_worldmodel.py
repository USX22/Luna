import numpy as np
import pytest

from ia.worldmodel.data import features, make_world, simulate, targets
from ia.worldmodel.evaluate import fit_law, identifiable, recover_K, ridge_probe


def test_world_is_reproducible_and_shaped():
    a, b = make_world(4, 50, seed=1, distractor_std=2.0), make_world(4, 50, seed=1, distractor_std=2.0)
    assert a.x.shape == (4, 50, 32) and np.array_equal(a.x, b.x)
    assert a.x[..., -8:].std() > 1.5  # distractor channels are high-variance noise


def test_strong_coupling_locks_phase_and_zero_coupling_drifts():
    rng = np.random.default_rng(0)
    theta, omega, K = simulate(1, 2000, rng, K_range=(3.0, 3.0), omega_range=(1.0, 1.4))
    d = np.unwrap(theta[0, :, 1] - theta[0, :, 0])
    assert np.ptp(d[1000:]) < 0.5            # locked
    theta, *_ = simulate(1, 2000, rng, K_range=(0.0, 0.0), omega_range=(0.5, 2.0))
    d = np.unwrap(theta[0, :, 1] - theta[0, :, 0])
    assert abs(d[-1] - d[0]) > 1.0            # drifts


def test_probe_on_true_features_is_near_perfect():
    w = make_world(32, 60, seed=2)
    Z = features(w.phases)
    # sin/cos of the phase difference are bilinear in the features, so a linear probe
    # on the raw features cannot be perfect; on the full targets it is.
    r2, _ = ridge_probe(Z[:16], targets(w.phases)[:16], Z[16:], targets(w.phases)[16:])
    assert 0.5 < r2 < 0.99
    r2_full, _ = ridge_probe(targets(w.phases)[:16], targets(w.phases)[:16],
                             targets(w.phases)[16:], targets(w.phases)[16:])
    assert r2_full > 0.999


def test_symbolic_law_recovers_coupling_from_true_phases():
    w = make_world(40, 400, seed=3)
    mask = identifiable(w.phases)
    assert 5 <= mask.sum() < 40
    assert recover_K(targets(w.phases), w.K, w.dt, mask) > 0.95
    # phase-locked sequences are not identifiable: recovery there is poor
    assert recover_K(targets(w.phases), w.K, w.dt, ~mask) < 0.9
    i = int(np.argmax(mask))
    d = w.phases[i, :, 1] - w.phases[i, :, 0]
    K_hat, dw_hat = fit_law(d, w.dt)
    assert abs(K_hat - w.K[i]) < 0.15 and abs(dw_hat - (w.omega[i, 1] - w.omega[i, 0])) < 0.15


def test_training_objectives_run_and_jepa_does_not_collapse():
    torch = pytest.importorskip("torch")
    from ia.worldmodel.models import encode, train_encoder
    w = make_world(32, 60, seed=4)
    for kind in ("jepa", "generativo", "autoencoder", "aleatorio"):
        enc, losses = train_encoder(kind, w.x, steps=60, batch=64, seed=0, device="cpu")
        Z = encode(enc, w.x)
        assert Z.shape == (32, 57, 16) and np.isfinite(Z).all()
        if kind == "jepa":
            assert Z.std(axis=(0, 1)).mean() > 0.05  # no representational collapse
        if losses:
            assert np.mean(losses[-10:]) < np.mean(losses[:10])


def test_structured_distractor_is_predictable_but_irrelevant():
    w = make_world(8, 200, seed=5, distractor_std=3.0, distractor_kind="estructurado")
    dist = w.x[..., -8:]
    assert 2.0 < dist.std() < 4.0
    # predictable: strongly autocorrelated at lag 1 (unlike white noise)
    a, b = dist[:, :-1].ravel(), dist[:, 1:].ravel()
    assert np.corrcoef(a, b)[0, 1] > 0.8
    # irrelevant: same distractor process regardless of the oscillators of interest
    noise = make_world(8, 200, seed=5, distractor_std=3.0)
    assert abs(np.corrcoef(noise.x[..., -8:][:, :-1].ravel(), noise.x[..., -8:][:, 1:].ravel())[0, 1]) < 0.1
