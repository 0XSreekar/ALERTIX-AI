# ALERTIX Research Report

## Evaluation Methodology

This repository includes executable tests for ingestion parsing, processing state transitions, Omori-Utsu calculations, geolocation resolution, and citizen trust scoring. Stress testing is provided by `tests/stress/pipeline_stress.py`, which publishes 1000 Redis stream events for pipeline benchmarking.

## Current Measured Results

| Component | Test / Benchmark | Result |
|---|---:|---|
| Backend unit tests | `python -m pytest` | To be run per environment |
| Processing slice | `tests/test_processing_engine.py` | State, DLQ, risk tier coverage |
| ML core | `tests/test_ml_core.py` | Omori and static geolocation coverage |
| Citizen trust | `tests/test_citizen_service.py` | Tier, NER-lite, duplicate scoring coverage |

## Model Accuracy Tables

Learned model accuracy is intentionally not fabricated. The LSTM, U-Net, and damage models expose training loops and metric calculation, but production accuracy tables must be generated from real labelled datasets and saved checkpoints.

| Model | Required Dataset | Metrics |
|---|---|---|
| Flood LSTM | CWC gauge history + rainfall history | RMSE, MAE |
| Flood U-Net | Labelled SAR/optical flood masks | IoU, F1 |
| Damage segmenter | Labelled post-disaster imagery | Per-class accuracy |
| Wildfire DBSCAN | NASA FIRMS hotspots | Cluster precision/recall against incident polygons |
| Omori-Utsu | Historical aftershock catalog | Calibration error, Brier score |

## Limitations

- ALERTIX does not predict exact future earthquakes.
- Learned models require real checkpoint weights before inference.
- AI summaries are not official warnings and must be grounded in sensor/model data.
- Gauge seed coordinates support bootstrapping; operational feeds remain the source of truth.
