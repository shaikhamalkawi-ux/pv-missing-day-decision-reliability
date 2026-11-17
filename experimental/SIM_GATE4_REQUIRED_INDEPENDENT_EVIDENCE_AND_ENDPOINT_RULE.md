# Decision-identifiability gate for a single missing PV inverter (engineering note)

Scope: one inverter j has a contiguous missing interval G; the other inverter
total yields are known. This elementary monotonic argument is not claimed
as a novel theorem, and it does not supply an error bound by itself.

Let y_j^obs be j's normalized energy outside G; X_j be its unknown
normalized energy during G. For k != j, y_k are completely observed
whole-month normalized yields. Let q in [0,1), t=1-q and

    S(X) = { i : y_i(X) >= t * max_h y_h(X) },
    y_j(X)=y_j^obs+X,  y_k(X)=y_k (k != j).

Suppose an independently justified physical/instrumental evidence chain gives
X in [a,b], with 0<=a<=b. Membership of j in S(X) is non-decreasing
in X, while membership of any k!=j is non-increasing in X.
Thus

    S(a)==S(b)  <=>  S(X) identical for every X in [a,b].

For one missing scalar, the *two-endpoint test* is sufficient and necessary
for an invariant whole-month shortlist over this bounded interval.

**No source-independent measurement = no narrow bound by default.**
The source Library site-power field has been experimentally shown in
SIM-GATE3 to equal a near-exact forward average of the inverter streams.
It cannot survive a hypothesized upstream inverter measurement outage
without an independently documented redundant feed path.

### Concrete route to an actual certificate

During the missing inverter-data period, independently log the PV
combiner total E_combiner using a separately acquired, verified and
calibrated meter. Read the OTHER inverter outputs from channels known
to remain live under the failure topology. Time-align all integrations.
If the meter directly sums inverter AC energy at the same measurement
boundary and all uncertainty intervals are valid:

    E_j^lo = max(0, E_total^lo - sum(k!=j) E_k^hi)
    E_j^hi = min(E_j^max, E_total^hi - sum(k!=j) E_k^lo)

If the meter boundary differs, explicitly include verified bounds
for AC cable losses, transformer losses and auxiliary consumption
before using these formulas. Normalize using fixed DC-STC ratings.
Apply the two-endpoint shortlist test.

This separates independent *measurement* evidence from documented
independent *failure-path availability*. A genuine extra meter can
still share a power supply, uplink or logger with the lost channel,
so fault-survivability must also be tested.

### How to validate

1. Register physical topology, meter traceable error limits and
   source-pinned timestamps before evaluating any withheld months.
2. Hold back whole later calendar months and preferably other roofs,
   preserving real failures if available; do not treat 588 overlapping
   simulated gaps as independent trials.
3. Evaluate (i) hard-bound containment, (ii) wrong certified decisions,
   (iii) abstention/no-certificate, and (iv) naive mistakes corrected
   *among only genuinely certified outputs*. If any assumption fails,
   downgrade to provisional model-assisted prediction or abstain.
4. Do not treat manufacturer/instrument +/-5% source guidance as a
   field-proven bound for a derived site channel or for target-to-peer
   residuals. Do not import learned local extrema into hard certificates.

The existing HKUST open dataset by Lin et al. (Scientific Data, 2025,
doi:10.1038/s41597-025-04397-y) includes an on-campus weather tower
and resampled inverter telemetry, but those facts do not establish an
independent source-side PV combiner meter with distinct acquisition
survivability. SIM-GATE4 empirical peer local ratio has seven interval
violations in the July 2023 chronological holdout at q=5%; therefore
its apparent decision accuracy is not a valid hard-certificate result.

R40 baseline remains unchanged. A new scientific version would require
a source-specific verified additional sensor/path or a mathematical
physical bound certified for the already-frozen target.
