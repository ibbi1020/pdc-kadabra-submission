# CS-3006 Milestone 2 Proposal

**Course:** Parallel and Distributed Computing (CS-3006), Fall 2026
**Due:** 23 November 2026
**Paper:** 44 — KADABRA is an ADaptive Algorithm for Betweenness via Random Approximation
**Citation:** Michele Borassi and Emanuele Natale, ESA 2016. https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ESA.2016.20

## 1. Group

| Role | Name | Roll number | Section | Email |
|---|---|---|---|---|
| Contact | | | | |
| Member 2 | | | | |
| Member 3 | | | | |

## 2. Understanding of the paper

This section is worth 10 marks. Explain the graph problem, the research objective, the paper’s core contribution, and the algorithm workflow, then review the paper critically.

### 2.1 The graph problem

What betweenness centrality measures, and why the exact algorithm is expensive.

### 2.2 Research objective and core contribution

What question KADABRA answers, and what is new in the paper compared with earlier sampling methods.

### 2.3 Algorithm workflow

The sampling loop in our own words: how a sample is drawn, how scores are updated, and how the algorithm decides to stop. Stay with the unweighted case we will implement.

### 2.4 Critical review

What the paper does well, what it leaves open, and which assumptions we are relying on (graph type, weights, approximation guarantee).

## 3. Scope, challenge, and complexity

This section is worth 10 marks. Define a focused scope, explain the computational difficulty, and say why this task is the right size.

### 3.1 What we will implement

Catalogue task for paper 44: sampled shortest-path betweenness on a small graph, independent samples run in parallel, error compared with exact centrality.

Concretely, three pieces:

1. **Sequential baseline (ours).** A KADABRA-style sampler that draws a random vertex pair and one uniform random shortest path between them, then adds one to every vertex on that path. We implement the path sampler with a **one-sided BFS and σ-weighted predecessor backtracking**, not the balanced bidirectional BFS. This samples a uniform shortest path correctly, is much simpler to get right, and keeps the baseline clearly our own rather than a copy of the shipped NetworKit class.
2. **A straightforward OpenMP version.** A parallel-for over independent samples with a shared score array. We state openly that this reproduces the 2019 OpenMP baseline (§4.3), so it is the thing we measure against, not our contribution.
3. **The contribution: a work-distribution and synchronization-cadence study (OpenMP).** The 2019 paper's contribution is a lock-free epoch mechanism; ours is orthogonal to it. We compare `static` vs `dynamic` vs `guided` scheduling for the uneven per-sample cost, and we measure the **stopping-check cadence** trade-off — checking the stopping condition every *k* samples and plotting synchronization overhead against wasted samples. This maps directly to the course's "work distribution and synchronization understood" criterion.

Course concept: **OpenMP** (shared-memory threads, scheduling, synchronization).

### 3.2 What we will leave out

- The 2019 lock-free frames (`local-frame`, `shared-frame`, `indexed-frame`). Re-deriving them would reproduce that paper's contribution. We cite them as the baseline instead. Note that a plain "private per-thread accumulator + merge" scheme *is* `local-frame`, so we deliberately do not claim that as our idea.
- MPI (the 2020 paper). We have one machine and small graphs; its gains come from clusters and NUMA, neither of which we can show.
- A GPU/OpenCL KADABRA sampler. The sampler's BFS is irregular and maps poorly to a GPU; this is a semester-scale effort, not two weeks.
- Beating SILVAN/BAVARIAN on sample count. That lane is closed by published work with public code.
- Changing KADABRA's stopping rule. A home-grown rule would void the (ε, δ) guarantee and force us to re-prove it.

### 3.3 Computational challenges

Exact betweenness is Θ(|V||E|), which is why sampling exists. The real difficulty in our scope is parallel, not asymptotic: the per-sample cost varies with the drawn pair, so naive static scheduling leaves threads idle; the shared score array invites contention and races; and the stopping condition must be read on a *consistent* snapshot of the counts, or the error guarantee breaks. Exact Brandes on our small graphs is cheap and serves as the ground-truth oracle.

### 3.4 Why this scope is appropriate

The sequential sampler and the OpenMP version are a few hundred lines; the scheduling/cadence study and the measurement harness are the substantive work. It fits two weeks, it exercises real course concepts (decomposition, scheduling, synchronization), and the guide rewards a rigorously measured study even when the speedup on small graphs is modest or negative.

## 4. Implementation plan and attribution

This section is worth 5 marks. State the parallelization strategy, the expected contribution, the evaluation plan, the risks, and every paper or repository the plan depends on.

### 4.1 Parallelization strategy

Threads draw independent samples in an OpenMP loop. The shared state is the per-vertex score array and the sample counter. Synchronization happens at the stopping check: threads must agree on a consistent set of counts before the check runs. We vary two things and measure the effect: the loop **schedule** (`static` / `dynamic` / `guided`), which attacks the uneven per-sample cost, and the **stopping-check cadence** (check every *k* samples), which trades synchronization frequency against extra samples taken past the stopping point.

### 4.2 Expected contribution

Beyond a plain parallel loop (= the 2019 baseline), our contribution is the measured answer to two questions that paper did not center: how much does scheduling policy matter for KADABRA's load-imbalanced samples on small graphs, and what is the real cost curve of checking the adaptive stopping condition more or less often. We keep KADABRA's stopping rule unchanged throughout, so the (ε, δ) guarantee is intact and any error we report is the sampler's, not a broken rule's.

### 4.3 Prior work that already implemented this approach

The guide requires this when a later paper already did the approach we propose. That paper becomes the baseline we compare against.

- van der Grinten, Angriman, and Meyerhenke (2019), OpenMP sampling. https://arxiv.org/abs/1903.09422
- van der Grinten and Meyerhenke (2020), MPI sampling, if we use MPI. https://arxiv.org/abs/1910.11039

The 2019 paper measured the OpenMP baseline at about 6.3× on 32 cores and its lock-free frames up to about 2.9× beyond that; the 2020 paper measured MPI scaling on clusters. Those are 32-core/cluster numbers. We copy none of them — we run our own small-graph experiments on our own machine and report only what we measure. Their results appear in our report only as the published context our scheduling/cadence study sits beside.

### 4.4 Existing code

Acknowledge any repository we will read. The original release is https://github.com/natema/kadabra. State that we will write our own implementation, and that cloning or repackaging that code is not our contribution.

### 4.5 Evaluation plan

- **Correctness:** one small hand-checkable graph first, then ER / Barabási–Albert / small SNAP graphs. Primary metric is **max additive error vs ε** over many seeds, with the empirical fraction of runs exceeding ε compared against δ. Secondary: average/RMSE error and **Kendall-τ / top-k overlap** against the exact ranking. We put KADABRA's normalized scores and the Brandes scores in the **identical normalization** (and the undirected factor of two) before comparing, so a units mismatch cannot masquerade as a guarantee violation.
- **Performance:** our own runs only. Speedup \(S = T_{serial} / T_{parallel}\), efficiency \(E = S / P\). We measure speedup with a **fixed sample budget** (stopping check disabled inside the timed region) so serial and parallel runs do identical work; the adaptive time-to-accuracy is reported separately.
- The timed region is the sampling kernel, separate from graph loading, diameter preprocessing, and printing.
- We report graph size, directed/undirected, storage format, machine, physical core count, compiler and flags, thread counts, and medians with variance. Threads and (where possible) CPU frequency are pinned to keep laptop turbo/throttling from swamping a small effect.

### 4.6 Risks

- **Speedup invisible on small graphs / laptop noise.** Likely. We mitigate with high-diameter inputs, kernel-only fixed-budget timing, and many repetitions, and we frame a small or negative result as a measured finding, which the guide permits.
- **Races on the shared score array; inconsistent stopping-check snapshot.** We use correct atomics/consistent merges and validate the deterministic single-thread path against Brandes before parallelizing.
- **Non-uniform shortest-path sampling bias.** Silent; we validate on graphs with many ties (grids, bipartite).
- **Per-thread RNG correlation.** Fixed master seed with decorrelated per-thread streams; a deterministic reference run as the oracle.
- **`natema/kadabra` is archived 2016 C++11.** If we build it as a reference it may need patching on a modern compiler; we budget for that and preserve its Apache-2.0 attribution.

### 4.7 Work split

Who reads the paper, who owns the sequential baseline, who owns the parallel version, who owns the experiments and the write-up. Every member must be able to explain all of it.

## References

List the base paper, the later papers named in section 4.3, repositories, and any dataset. Add an AI-assistance note if tools were used to draft this proposal.
