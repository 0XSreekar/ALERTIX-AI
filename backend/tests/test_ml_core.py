import pytest

from app.ml.aftershock_omori import OmoriUtsuModel
from app.ml.geolocation import resolve_static


def test_omori_predicts_probability_not_exact_earthquake():
    result = OmoriUtsuModel().predict(mainshock_magnitude=6.5, elapsed_hours=12)

    assert 0 <= result.probability <= 1
    assert result.risk_level in {"low", "medium", "high", "critical"}
    assert result.confidence_interval[0] <= result.confidence_interval[1]


def test_omori_fit_updates_parameters_from_aftershock_times():
    model = OmoriUtsuModel()
    params = model.fit([0.05, 0.1, 0.2, 0.7, 1.2, 2.0])

    assert params.k > 0
    assert params.c > 0
    assert params.p > 0


def test_static_geolocation_resolves_nearest_river():
    result = resolve_static(16.506, 80.648)

    assert result.nearest_river_name == "Krishna"
    assert result.distance_to_river_km < 1


def test_static_geolocation_rejects_bad_coordinates():
    with pytest.raises(ValueError):
        resolve_static(100, 80)
