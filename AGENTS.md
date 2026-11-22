# Notes for future agents working on this project

Course: CS-3006 Parallel and Distributed Computing, Fall 2026. Paper 44, KADABRA
betweenness-centrality approximation. This is the private "rough work" repo; the
clean submission lives in a separate repo.

## The contribution: do not quietly shrink it

The committed build is four pieces: a sequential KADABRA sampler, an exact Brandes
oracle, an OpenMP **barrier** loop (the 2019 baseline, and our safe fallback), and a
**lock-free `local-frame`** version re-implemented from the 2019 paper. On top of these
sit **three measurement studies**, which are our actual contribution:

1. **Barrier vs lock-free at laptop scale** — does the 2019 result (lock-free beats
   barrier, measured on 32-36 cores) still hold at 1/2/4/physical cores on small graphs,
   and where does the ordering flatten or reverse.
2. **Schedule** — static vs dynamic vs guided, for the uneven per-sample BFS cost.
3. **Batch length k** — the synchronization-cadence trade-off (barrier cost vs samples
   taken past the stopping point).

### Why the lock-free version must stay in

An earlier revision dropped the lock-free version and kept only the schedule + batch-length
study on a plain barrier loop. Two grilling rounds (recorded in `research/`) showed why that
is **a very thin contribution** and should not be repeated:

- A plain OpenMP barrier loop over samples **is** the 2019 paper's baseline. Submitting only
  that, with a scheduling tweak, re-delivers their starting point, not a contribution.
- The batch-length / samples-per-check trade-off is **already tuned in the 2019 paper's
  Appendix C** (about 1000 samples per epoch) and ships in NetworKit, so on its own it reads
  as reproduction.
- The static/dynamic/guided schedule change is essentially one clause; thin as a standalone
  contribution.

The lock-free `local-frame` version is what makes the parallel implementation *meaningful*
(the 20-mark rubric line) and gives the barrier-vs-lock-free study something real to measure.
It is also the main technical risk (epoch consistency with release/acquire ordering; a missing
fence hides behind x86's strong memory model until the many-seed Brandes check catches it), so
the barrier loop is built first and kept as the fallback. **Keep the lock-free version. Do not
reduce the contribution back to schedule + batch-length alone.**

### Framing rules (from the course guide)

- The lock-free mechanism is the 2019 authors', not ours. We re-implement one variant as a
  measured baseline and say so. Reproducing a method does not by itself count as the
  contribution; the measurement does.
- We do not change KADABRA's stopping rule (f, g, omega, frozen budgets). A result past the
  error bound lambda is a bug in our sampler or snapshot, not a new algorithm.
- All timings are our own; the 2019/2020 numbers are cited as context only.

## Style

Proposal and report: no em dashes. Varied sentence length, plain language, explain before
formula. Keep dense math (e.g. the computeDelta internals) as prose plus the one key formula,
not a formula dump.
