# Notes for future agents working on this project

Course: CS-3006 Parallel and Distributed Computing, Fall 2026. Paper 44, KADABRA
betweenness-centrality approximation. This is the private "rough work" repo; the
clean submission lives in a separate repo.

## The contribution: do not quietly shrink it

The committed build is three pieces plus a planned fourth:

1. A sequential KADABRA sampler and an exact Brandes oracle.
2. An OpenMP barrier loop (the 2019 baseline, and our safe fallback).
3. **The contribution: a cost model that predicts the stopping-check interval k.**
   We write the run time as sampling + checks + overshoot, minimize it to get
   `k* = sqrt(2*M*C*T/s)` (M = first passing prefix, C = cost of one check, T = threads,
   s = mean sample time), estimate M, C, s from the pilot KADABRA already runs, and test
   the three predictions (k* grows with graph size, grows ~sqrt2 per thread doubling,
   shrinks with larger diameter) against a measured sweep and against the paper's fixed
   N=1000 and the original N=11. A `static`/`dynamic`/`guided` schedule comparison is a
   secondary result.
4. **Planned second pillar: the lock-free `local-frame` version** (re-implemented from the
   2019 paper). It carries the hands-on parallel-implementation marks and gives the cost
   model a second, harder test (predicting its epoch length). Built after piece 3 is
   measured, gated on the many-seed accuracy check, with the barrier loop as the fallback.

### Why this shape, and what not to do

Earlier iterations drifted twice, and both are recorded in `research/` (two grilling rounds):

- Do **not** reduce the contribution to "a `static`/`dynamic`/`guided` schedule tweak" or to
  "re-run the 2019 batch-length sweep." The schedule change is ~one clause, and the
  interval sweep is already tuned in the 2019 paper's Appendix C (N=1000) and ships in
  NetworKit, so either alone reads as reproduction. The predictive cost model is what makes
  the interval work genuinely ours: the paper gives a constant, we give the reason and
  predict it per graph and thread count.
- Do **not** drop the lock-free `local-frame` version. A plain barrier loop is the 2019
  baseline, so without local-frame the hands-on parallel implementation (the 20-mark rubric
  line) is thin. It is the riskiest piece (epoch consistency with release/acquire; a missing
  fence hides behind x86's strong memory model until the many-seed Brandes check catches it),
  which is why it is a planned pillar gated on correctness rather than a hard dependency.

### Framing rules (from the course guide)

- The lock-free mechanism and the N=1000 tuning are the 2019 authors', not ours. We
  re-implement local-frame as a measured baseline and say so. Reproducing a method does not
  count as the contribution; the predictive model and its measurements do.
- We do not change KADABRA's stopping rule (f, g, omega, frozen budgets). Predicting the
  check interval k changes only how often we check, which is a legal stopping time, so the
  (epsilon, delta) guarantee is untouched. A result past lambda is a bug, not a new algorithm.
- All timings are our own; the 2019/2020 numbers are cited as context only.

## Style

Proposal and report: no em dashes. Varied sentence length, plain language, explain before
formula. Keep dense math (e.g. the computeDelta internals) as prose plus the one key formula,
not a formula dump.
