# CS-3006 Final Project — KADABRA Betweenness Approximation

Parallel and Distributed Computing (CS-3006), Fall 2026. Base paper 44: **KADABRA is an ADaptive Algorithm for Betweenness via Random Approximation** (Borassi & Natale, ESA 2016).

This is the clean submission repository: the code, data, and documents we hand in.

## What we build

A sequential KADABRA-style betweenness sampler, a straightforward OpenMP parallel version, and a contribution that studies **work distribution and synchronization cadence** for the parallel sampler (loop scheduling and stopping-check frequency), validated against exact betweenness (Brandes) and measured on our own machine. See [proposal/PROPOSAL.md](proposal/PROPOSAL.md).

## Layout

| Path | Contents |
|---|---|
| `src/` | Commented C/C++ source |
| `data/` | Test graphs and generators |
| `proposal/` | Milestone 2 proposal and defense notes |
| `report/` | Technical report (`report.pdf`) |
| `slides/` | Presentation (`presentation.pdf`) |

## Build and run

To be filled in as the code lands: dependencies, compiler and version, the exact compile command, run commands, input format, expected output, and reproduction steps.

## Attribution

Base paper: Borassi & Natale, ESA 2016. Comparison baselines: van der Grinten, Angriman & Meyerhenke 2019 (OpenMP); van der Grinten & Meyerhenke 2020 (MPI). Reference implementation consulted: https://github.com/natema/kadabra (Apache-2.0). Our implementation is our own; any external code is acknowledged here. AI assistance is disclosed in the report.
