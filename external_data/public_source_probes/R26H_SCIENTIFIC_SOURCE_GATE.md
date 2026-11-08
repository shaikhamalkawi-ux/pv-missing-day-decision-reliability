# R26H independent public PV source gate — 8 November 2026

Status: DEVELOPMENT ONLY. R25-SE1, r25-public-release and the locked R22 results are unchanged. No Qatar/QEERI data used.

## Publisher original data
- TECNALIA: https://zenodo.org/records/18306410; publisher MD5 verified. Five simultaneous photovoltaic modules but source time cadence switches between five and ten minutes; date/metadata conflicts require HOLD.
- INES-CEA: https://zenodo.org/records/18316614; publisher MD5 verified. Four module series are not contemporaneous; only the bifacial/monofacial pair overlaps in 2024. Raw source time duplication and source rated-power semantics require HOLD.
- HKUST: https://zenodo.org/records/10909062, original April 2024 source. Original ZIP SHA256: 610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec. Original ZIP CRC PASS. Do not assume byte identity with later Dryad dataset. 44 inverter output time-series among one campus's PV installations.

## HKUST source clocks and device denominators
Native HKUST source observation window is 06:00 through 17:55, 5-minute intervals, 144 positions daily. Applying full-calendar-month coverage with exactly 144 unique positions and finite measured inverter power, five co-located multi-inverter roof groups have common months (12 group-months before capacity checks).

The Library roof has three strictly admitted complete months: 2022-07, 2023-05, 2023-07. The source's machine-readable RDF records per-inverter panels and STC:
- Library inverter 1: 156 panels x 370 W = 57,720 W DC STC.
- Library inverter 2: 152 panels x 370 W = 56,240 W DC STC.
- Library inverter 3: 152 panels x 370 W = 56,240 W DC STC.
Sum 170,200 W matches the station's published rated capacity exactly.

Four other roof groups have device-DC-STC sums differing from the station's rated-output figure or an unresolved multi-module map. That is not proof of error (station figures may describe AC while module STC is DC). They were conservatively held.

## Library source-conditional q-by-L surface (development, not paper)
Preserve original R22 shortlist q={0,0.025,0.05,0.075,0.1}, L=1..7 days, >=10 retained days, no imputation; observed 5-minute AC sample sum / module DC-STC denominator. Three source-months, same roof, NOT independent population units.

| q | L1 | L2 | L3 | L4 | L5 | L6 | L7 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0% | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| 2.5% | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| 5% | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| 7.5% | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| 10% | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 1/3 |

Source-computation run 42483211887: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/42483211887
Independent result readback 42483377276: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/42483377276
Readback verifies 35/35 q-L cells, 105/105 source-month decisions and monotonicity in L. Results are stable at q5 for L<=7 across these three months, with one month becoming fragile at q10 and L7. This is not device superiority or a generalized probability.

## Preservation
Original publisher data and source-derived audits are saved in the private Project 106Amen Drive folder:
https://drive.google.com/drive/folders/1Hv-htNU0iKgW-rJ395_hClvSkPL5n2bK

HKUST original ZIP exceeded the connector single-upload size. It was split byte-for-byte into four parts, each encapsulated within a GitHub Actions ZIP artifact. Extract each outer wrapper separately, concatenate the underlying PART00, PART01, PART02, PART03 data files in order, and verify original SHA256. Never concatenate outer artifact ZIP wrappers.

## Claim boundary and next gate
R26H is source-level exploratory evidence only, not an admitted fourth published cohort. Final manuscript addition requires source-vintage, device operation/configuration, weather support, timing and metadata review and evidence of meaningful engineering comparability. R25/R22 remains unchanged. No author data required to continue this public-source research; restricted Qatar/QEERI is excluded.
