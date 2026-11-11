# Measured results (simulation)

Simulation start 2026-11-11T15:00:00Z, 7 days propagated, messages generated over the first 5 days. All numbers are simulated from the stated assumptions.

### Orbit set `sso`: sun-synchronous class (inc 96-99.5 deg, 450-650 km)

24 satellites, mean altitude 482.6 km, link closes above 9.8 deg elevation, max Doppler about 22.1 kHz.

| Site | Ground m | Mean/max horizon deg | Passes/day flat | Passes/day terrain | Lost % | Coverage min/day (terrain) | Uplink p50/p95 min | End-to-end p50/p95 min | Delivered % | mAh/day | Battery years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Interlaken, open valley floor | 568 | 13.1 / 27.0 | 86.4 | 85.9 | 1 | 319 | 12 / 58 | 51 / 114 | 100 | 0.72 | 6.8 |
| Lauterbrunnen, narrow valley floor | 788 | 24.9 / 41.5 | 86.3 | 46.0 | 47 | 179 | 24 / 117 | 63 / 162 | 100 | 0.63 | 7.8 |
| Foot of the Eiger north face | 1618 | 17.1 / 44.3 | 86.1 | 82.6 | 4 | 304 | 13 / 57 | 38 / 117 | 100 | 0.72 | 6.9 |
| Kleine Scheidegg, mountain saddle | 2057 | 13.7 / 28.6 | 86.1 | 79.3 | 8 | 313 | 13 / 68 | 41 / 123 | 100 | 0.72 | 6.9 |
| Schilthorn, ridge top | 2967 | 0.6 / 6.2 | 86.4 | 86.4 | 0 | 414 | 13 / 57 | 47 / 117 | 100 | 0.72 | 6.8 |

### Orbit set `mid`: mid-inclination class (inc 45-60 deg, 450-650 km)

24 satellites, mean altitude 477.0 km, link closes above 9.7 deg elevation, max Doppler about 22.1 kHz.

| Site | Ground m | Mean/max horizon deg | Passes/day flat | Passes/day terrain | Lost % | Coverage min/day (terrain) | Uplink p50/p95 min | End-to-end p50/p95 min | Delivered % | mAh/day | Battery years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Interlaken, open valley floor | 568 | 13.1 / 27.0 | 133.3 | 130.1 | 2 | 583 | 9 / 38 | 57 / 243 | 100 | 0.76 | 6.5 |
| Lauterbrunnen, narrow valley floor | 788 | 24.9 / 41.5 | 133.3 | 112.9 | 15 | 315 | 9 / 41 | 56 / 253 | 100 | 0.77 | 6.4 |
| Foot of the Eiger north face | 1618 | 17.1 / 44.3 | 133.4 | 116.7 | 13 | 536 | 10 / 42 | 57 / 243 | 100 | 0.76 | 6.5 |
| Kleine Scheidegg, mountain saddle | 2057 | 13.7 / 28.6 | 133.4 | 123.6 | 7 | 534 | 9 / 39 | 55 / 246 | 100 | 0.77 | 6.4 |
| Schilthorn, ridge top | 2967 | 0.6 / 6.2 | 133.3 | 133.3 | 0 | 669 | 10 / 40 | 61 / 247 | 100 | 0.76 | 6.5 |

### Orbit set `polar`: near-polar class (inc 80-90 deg, 450-900 km)

24 satellites, mean altitude 713.9 km, link closes above 16.8 deg elevation, max Doppler about 21.7 kHz.

| Site | Ground m | Mean/max horizon deg | Passes/day flat | Passes/day terrain | Lost % | Coverage min/day (terrain) | Uplink p50/p95 min | End-to-end p50/p95 min | Delivered % | mAh/day | Battery years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Interlaken, open valley floor | 568 | 13.1 / 27.0 | 78.0 | 78.0 | 0 | 341 | 15 / 53 | 29 / 102 | 100 | 0.68 | 7.3 |
| Lauterbrunnen, narrow valley floor | 788 | 24.9 / 41.5 | 78.0 | 57.0 | 27 | 250 | 19 / 68 | 26 / 98 | 100 | 0.66 | 7.5 |
| Foot of the Eiger north face | 1618 | 17.1 / 44.3 | 78.0 | 77.6 | 1 | 313 | 15 / 52 | 24 / 100 | 100 | 0.70 | 7.1 |
| Kleine Scheidegg, mountain saddle | 2057 | 13.7 / 28.6 | 78.1 | 77.0 | 1 | 344 | 15 / 53 | 26 / 100 | 100 | 0.69 | 7.2 |
| Schilthorn, ridge top | 2967 | 0.6 / 6.2 | 77.9 | 77.9 | 0 | 377 | 15 / 55 | 27 / 102 | 100 | 0.68 | 7.3 |


## Scheduled vs blind policy

| Orbit set | Site | Policy | Uplink p50/p95 min | Delivered % | mAh/day | Battery years |
|---|---|---|---:|---:|---:|---:|
| sso | Interlaken, open valley floor | scheduled | 12 / 58 | 100 | 0.72 | 6.8 |
| sso | Interlaken, open valley floor | blind | 64 / 284 | 98 | 1.58 | 3.1 |
| sso | Lauterbrunnen, narrow valley floor | scheduled | 24 / 117 | 100 | 0.63 | 7.8 |
| sso | Lauterbrunnen, narrow valley floor | blind | 97 / 305 | 85 | 1.81 | 2.7 |
| sso | Foot of the Eiger north face | scheduled | 13 / 57 | 100 | 0.72 | 6.9 |
| sso | Foot of the Eiger north face | blind | 67 / 277 | 91 | 1.50 | 3.3 |
| sso | Kleine Scheidegg, mountain saddle | scheduled | 13 / 68 | 100 | 0.72 | 6.9 |
| sso | Kleine Scheidegg, mountain saddle | blind | 63 / 264 | 94 | 1.47 | 3.4 |
| sso | Schilthorn, ridge top | scheduled | 13 / 57 | 100 | 0.72 | 6.8 |
| sso | Schilthorn, ridge top | blind | 47 / 225 | 99 | 1.34 | 3.7 |
| mid | Interlaken, open valley floor | scheduled | 9 / 38 | 100 | 0.76 | 6.5 |
| mid | Interlaken, open valley floor | blind | 35 / 165 | 100 | 1.19 | 4.1 |
| mid | Lauterbrunnen, narrow valley floor | scheduled | 9 / 41 | 100 | 0.77 | 6.4 |
| mid | Lauterbrunnen, narrow valley floor | blind | 70 / 269 | 97 | 1.47 | 3.4 |
| mid | Foot of the Eiger north face | scheduled | 10 / 42 | 100 | 0.76 | 6.5 |
| mid | Foot of the Eiger north face | blind | 36 / 141 | 100 | 1.28 | 3.8 |
| mid | Kleine Scheidegg, mountain saddle | scheduled | 9 / 39 | 100 | 0.77 | 6.4 |
| mid | Kleine Scheidegg, mountain saddle | blind | 36 / 131 | 100 | 1.32 | 3.7 |
| mid | Schilthorn, ridge top | scheduled | 10 / 40 | 100 | 0.76 | 6.5 |
| mid | Schilthorn, ridge top | blind | 27 / 102 | 100 | 1.13 | 4.4 |
| polar | Interlaken, open valley floor | scheduled | 15 / 53 | 100 | 0.68 | 7.3 |
| polar | Interlaken, open valley floor | blind | 60 / 203 | 100 | 1.56 | 3.2 |
| polar | Lauterbrunnen, narrow valley floor | scheduled | 19 / 68 | 100 | 0.66 | 7.5 |
| polar | Lauterbrunnen, narrow valley floor | blind | 83 / 272 | 97 | 1.59 | 3.1 |
| polar | Foot of the Eiger north face | scheduled | 15 / 52 | 100 | 0.70 | 7.1 |
| polar | Foot of the Eiger north face | blind | 60 / 240 | 99 | 1.52 | 3.2 |
| polar | Kleine Scheidegg, mountain saddle | scheduled | 15 / 53 | 100 | 0.69 | 7.2 |
| polar | Kleine Scheidegg, mountain saddle | blind | 65 / 208 | 100 | 1.45 | 3.4 |
| polar | Schilthorn, ridge top | scheduled | 15 / 55 | 100 | 0.68 | 7.3 |
| polar | Schilthorn, ridge top | blind | 53 / 204 | 100 | 1.41 | 3.5 |

## Sensitivity to satellite G/T (set `sso`)

| G/T dB/K | Link min elevation deg | Lauterbrunnen flat / terrain (lost %) | Schilthorn flat / terrain (lost %) |
|---:|---:|---:|---:|
| -24 | 20.8 | 54.6 / 42.1 (23%) | 54.4 / 54.4 (0%) |
| -22 | 14.7 | 68.7 / 45.1 (34%) | 68.6 / 68.6 (0%) |
| -20 | 9.8 | 86.3 / 46.0 (47%) | 86.4 / 86.4 (0%) |
| -18 | 6.2 | 101.4 / 46.0 (55%) | 101.3 / 101.3 (0%) |
| -16 | 3.8 | 112.9 / 46.0 (59%) | 112.9 / 112.9 (0%) |
