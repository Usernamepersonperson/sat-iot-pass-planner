# Measured results (simulation)

Simulation start 2026-11-08T08:00:00Z, 7 days propagated, messages generated over the first 5 days. All numbers are simulated from the stated assumptions.

### Orbit set `sso`: sun-synchronous class (inc 96-99.5 deg, 450-650 km)

24 satellites, mean altitude 481.2 km, link closes above 9.8 deg elevation, max Doppler about 22.1 kHz.

| Site | Ground m | Mean/max horizon deg | Passes/day flat | Passes/day terrain | Lost % | Coverage min/day (terrain) | Uplink p50/p95 min | End-to-end p50/p95 min | Delivered % | mAh/day | Battery years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Interlaken, open valley floor | 568 | 13.1 / 27.0 | 85.3 | 84.3 | 1 | 307 | 14 / 65 | 54 / 129 | 100 | 0.67 | 7.4 |
| Lauterbrunnen, narrow valley floor | 788 | 24.9 / 41.5 | 85.0 | 44.6 | 48 | 174 | 25 / 120 | 73 / 193 | 100 | 0.58 | 8.5 |
| Foot of the Eiger north face | 1618 | 17.1 / 44.3 | 85.3 | 82.7 | 3 | 302 | 14 / 63 | 53 / 134 | 100 | 0.69 | 7.1 |
| Kleine Scheidegg, mountain saddle | 2057 | 13.7 / 28.6 | 85.1 | 79.6 | 7 | 308 | 14 / 65 | 53 / 141 | 100 | 0.66 | 7.5 |
| Schilthorn, ridge top | 2967 | 0.6 / 6.2 | 85.1 | 85.1 | 0 | 403 | 15 / 62 | 55 / 133 | 100 | 0.67 | 7.3 |

### Orbit set `mid`: mid-inclination class (inc 45-60 deg, 450-650 km)

24 satellites, mean altitude 480.7 km, link closes above 9.8 deg elevation, max Doppler about 22.1 kHz.

| Site | Ground m | Mean/max horizon deg | Passes/day flat | Passes/day terrain | Lost % | Coverage min/day (terrain) | Uplink p50/p95 min | End-to-end p50/p95 min | Delivered % | mAh/day | Battery years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Interlaken, open valley floor | 568 | 13.1 / 27.0 | 135.1 | 131.0 | 3 | 579 | 10 / 39 | 64 / 249 | 100 | 0.77 | 6.4 |
| Lauterbrunnen, narrow valley floor | 788 | 24.9 / 41.5 | 135.3 | 114.0 | 16 | 320 | 10 / 39 | 58 / 255 | 100 | 0.77 | 6.4 |
| Foot of the Eiger north face | 1618 | 17.1 / 44.3 | 135.6 | 118.9 | 12 | 531 | 11 / 39 | 61 / 252 | 99 | 0.77 | 6.4 |
| Kleine Scheidegg, mountain saddle | 2057 | 13.7 / 28.6 | 135.4 | 124.6 | 8 | 532 | 11 / 41 | 60 / 248 | 100 | 0.77 | 6.4 |
| Schilthorn, ridge top | 2967 | 0.6 / 6.2 | 135.3 | 135.3 | 0 | 654 | 11 / 39 | 65 / 256 | 100 | 0.76 | 6.5 |

### Orbit set `polar`: near-polar class (inc 80-90 deg, 450-900 km)

24 satellites, mean altitude 722.5 km, link closes above 17.1 deg elevation, max Doppler about 21.7 kHz.

| Site | Ground m | Mean/max horizon deg | Passes/day flat | Passes/day terrain | Lost % | Coverage min/day (terrain) | Uplink p50/p95 min | End-to-end p50/p95 min | Delivered % | mAh/day | Battery years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Interlaken, open valley floor | 568 | 13.1 / 27.0 | 77.9 | 77.9 | 0 | 352 | 15 / 57 | 32 / 117 | 100 | 0.66 | 7.5 |
| Lauterbrunnen, narrow valley floor | 788 | 24.9 / 41.5 | 77.4 | 57.1 | 26 | 260 | 19 / 67 | 28 / 108 | 100 | 0.65 | 7.6 |
| Foot of the Eiger north face | 1618 | 17.1 / 44.3 | 77.3 | 76.6 | 1 | 326 | 15 / 56 | 25 / 109 | 100 | 0.66 | 7.4 |
| Kleine Scheidegg, mountain saddle | 2057 | 13.7 / 28.6 | 77.4 | 76.3 | 1 | 356 | 16 / 57 | 27 / 121 | 100 | 0.66 | 7.5 |
| Schilthorn, ridge top | 2967 | 0.6 / 6.2 | 77.9 | 77.9 | 0 | 388 | 15 / 56 | 27 / 110 | 100 | 0.66 | 7.5 |


## Scheduled vs blind policy

| Orbit set | Site | Policy | Uplink p50/p95 min | Delivered % | mAh/day | Battery years |
|---|---|---|---:|---:|---:|---:|
| sso | Interlaken, open valley floor | scheduled | 14 / 65 | 100 | 0.67 | 7.4 |
| sso | Interlaken, open valley floor | blind | 69 / 240 | 97 | 1.64 | 3.0 |
| sso | Lauterbrunnen, narrow valley floor | scheduled | 25 / 120 | 100 | 0.58 | 8.5 |
| sso | Lauterbrunnen, narrow valley floor | blind | 109 / 318 | 73 | 1.74 | 2.8 |
| sso | Foot of the Eiger north face | scheduled | 14 / 63 | 100 | 0.69 | 7.1 |
| sso | Foot of the Eiger north face | blind | 80 / 250 | 100 | 1.56 | 3.2 |
| sso | Kleine Scheidegg, mountain saddle | scheduled | 14 / 65 | 100 | 0.66 | 7.5 |
| sso | Kleine Scheidegg, mountain saddle | blind | 70 / 235 | 97 | 1.60 | 3.1 |
| sso | Schilthorn, ridge top | scheduled | 15 / 62 | 100 | 0.67 | 7.3 |
| sso | Schilthorn, ridge top | blind | 55 / 196 | 99 | 1.44 | 3.4 |
| mid | Interlaken, open valley floor | scheduled | 10 / 39 | 100 | 0.77 | 6.4 |
| mid | Interlaken, open valley floor | blind | 32 / 131 | 100 | 1.20 | 4.1 |
| mid | Lauterbrunnen, narrow valley floor | scheduled | 10 / 39 | 100 | 0.77 | 6.4 |
| mid | Lauterbrunnen, narrow valley floor | blind | 61 / 255 | 96 | 1.53 | 3.2 |
| mid | Foot of the Eiger north face | scheduled | 11 / 39 | 99 | 0.77 | 6.4 |
| mid | Foot of the Eiger north face | blind | 36 / 160 | 100 | 1.20 | 4.1 |
| mid | Kleine Scheidegg, mountain saddle | scheduled | 11 / 41 | 100 | 0.77 | 6.4 |
| mid | Kleine Scheidegg, mountain saddle | blind | 32 / 146 | 100 | 1.33 | 3.7 |
| mid | Schilthorn, ridge top | scheduled | 11 / 39 | 100 | 0.76 | 6.5 |
| mid | Schilthorn, ridge top | blind | 30 / 106 | 100 | 1.15 | 4.3 |
| polar | Interlaken, open valley floor | scheduled | 15 / 57 | 100 | 0.66 | 7.5 |
| polar | Interlaken, open valley floor | blind | 69 / 234 | 99 | 1.44 | 3.4 |
| polar | Lauterbrunnen, narrow valley floor | scheduled | 19 / 67 | 100 | 0.65 | 7.6 |
| polar | Lauterbrunnen, narrow valley floor | blind | 81 / 307 | 92 | 1.54 | 3.2 |
| polar | Foot of the Eiger north face | scheduled | 15 / 56 | 100 | 0.66 | 7.4 |
| polar | Foot of the Eiger north face | blind | 63 / 229 | 94 | 1.49 | 3.3 |
| polar | Kleine Scheidegg, mountain saddle | scheduled | 16 / 57 | 100 | 0.66 | 7.5 |
| polar | Kleine Scheidegg, mountain saddle | blind | 67 / 256 | 99 | 1.48 | 3.3 |
| polar | Schilthorn, ridge top | scheduled | 15 / 56 | 100 | 0.66 | 7.5 |
| polar | Schilthorn, ridge top | blind | 57 / 204 | 98 | 1.40 | 3.5 |

## Sensitivity to satellite G/T (set `sso`)

| G/T dB/K | Link min elevation deg | Lauterbrunnen flat / terrain (lost %) | Schilthorn flat / terrain (lost %) |
|---:|---:|---:|---:|
| -24 | 20.7 | 53.0 / 41.6 (22%) | 52.7 / 52.7 (0%) |
| -22 | 14.6 | 68.9 / 43.7 (37%) | 68.9 / 68.9 (0%) |
| -20 | 9.8 | 85.0 / 44.6 (48%) | 85.1 / 85.1 (0%) |
| -18 | 6.1 | 101.1 / 44.6 (56%) | 100.9 / 100.9 (0%) |
| -16 | 3.8 | 112.0 / 44.6 (60%) | 111.6 / 111.6 (0%) |
