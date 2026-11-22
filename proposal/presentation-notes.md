# Milestone 2 defense (5 minutes)

The written proposal is `proposal.tex`. The deck is `slides/presentation.pptx` (PDF export: `slides/presentation.pdf`); every slide also carries these points in its speaker notes. Talk for about four minutes and leave time for one question.

| Time | Slide | Say this |
|---|---|---|
| 0:00–0:10 | 1. Title | Group, paper 44, and the catalogue task in one line. |
| 0:10–0:45 | 2. The problem | Betweenness is the probability a vertex lies strictly inside a random shortest path. Brandes is O(nm) with a SETH lower bound, so we approximate to additive error λ with probability 1 − δ. |
| 0:45–1:35 | 3. How KADABRA works | Cap ω, pilot then freeze the budgets, sample and credit intermediate vertices, stop when f and g are below λ or at ω. Earlier methods applied a fixed-τ bound at a random time; the cap plus the martingale argument is what makes early stopping legal. |
| 1:35–2:05 | 4. Contributions and review | Rigorous adaptive stopping and the balanced bidirectional BFS. Limits: probabilistic guarantee, frozen budgets, the diameter bound, a model-specific BFS bound, σ overflow. |
| 2:05–2:35 | 5. Scope | Our sampler with Brandes, the plain OpenMP barrier loop, then our predicted check interval, with a schedule comparison on the side. The 2019 lock-free method and their tuned N = 1000 are cited as baselines, not claimed. Stretch: rebuild their local-frame only to measure it. |
| 2:35–3:00 | 6. Why this is hard | Biased backtracking, disconnected pairs, partial snapshots, uneven BFS cost, how often to check. |
| 3:00–3:35 | 7. Parallel design | Private counts merged at a barrier every k samples; the stop test sees only that prefix, so the guarantee holds. 2019 fixed k at 1000 for every graph. Checks cost (M/k)·C and the stop is seen about k/2 samples late, so k* = √(2MCT/s): bigger for big graphs and more threads, smaller for costly samples. We estimate it from KADABRA's own pilot and test it against a sweep, 1000, and 11. The charts are shapes, not results. |
| 3:35–4:10 | 8. Evaluation | Failure rate ≤ δ against Brandes in the same normalization; fixed-budget speedup and adaptive time-to-stop; main risk is a flat curve, which we still explain. |
| 4:10–4:20 | 9. Thank you | One-line recap (sample paths, run them in parallel, stay within λ of Brandes), then take questions. |

Each slide builds itself automatically when it opens (about 4–5 seconds), so start talking straight away. Clicking during a build skips to the finished slide.

The full reference list is in the proposal PDF.

Be ready for: why endpoints get no credit, why a disconnected pair still counts as a sample, why checking every k samples does not break the proof (k is fixed from the discarded pilot before the main loop, so the stop still depends only on a prefix), how this differs from the 2019 paper (they tuned one constant; we predict it per graph and thread count and test the prediction), why local-frame is a stretch rather than the contribution (rebuilding it is their method; measuring whether it helps on a laptop is useful but secondary), and what each person is building in week two.
