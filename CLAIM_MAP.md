# Claim-to-evidence map

All gas below is local Shanghai EVM transaction gas. No row establishes mainnet fees or full Enygma payment execution.

| Article finding | Preserved evidence | How to check | Boundary |
|---|---|---|---|
| 150 original paired compressed/direct comparisons | original/results/proofs-run-*.json and evm-run-*.json | python3 reviewer/audit_saved.py; fresh root reproduce.py --evm | Randomized repetitions of one fixture per circuit profile |
| Proof 256 to 128 bytes; full calldata 836/708 through 1860/1732 bytes | Original raw calldata and profile-summary.csv | Audit decodes lengths, proof words, selectors and public inputs | Public inputs stay unchanged |
| All 150 original pairs used more compressed-route gas | original/results/paired-comparisons.csv | Recalculate receipt gas and each paired delta | Fixed compiler, hardfork and five pinned verifiers |
| Original example: 12123 extra execution - 2048 saved intrinsic = 10075 extra total gas | Original run 1, k=2, trial 0 direct and compressed rows | Raw gasUsed and byte composition | The execution difference includes both entry points |
| 45 new native proofs subsequently accepted by all three Solidity entry points | supplemental/results/native-proofs.json and evm-report.json | python3 supplemental/audit.py; fresh supplemental/reproduce.py | Fifteen synthetic witness variants, three proofs each; not full payment workflows |
| All 45 supplemental pairs also used more compressed-route gas | supplemental/results/analysis.json, pairs | Recompute gas decomposition for each native proof identity | Separate result set; original medians are unchanged |
| Same EC addition/multiplication counts and one pairing call in 15 traced pairs | raw_call_trace on trial-0 direct/compressed supplemental rows | Audit recursively counts calls to precompile addresses 0x06, 0x07 and 0x08 | Thirty traced transactions selected by a declared rule |
| Compressed side adds five modexp calls costing 6701 callee gas | The same raw call traces; address 0x05 | Sum the five gasUsed values and compare with intrinsic savings | Callee cost is not the full decompression or entry-point overhead |
| Original 48 and supplemental 60 rejected-proof controls | Original/review and supplemental controls arrays | Bind raw receipts, returned booleans, expected error, ABI selector and proof/input identity | A successful wrapper receipt can accompany false; caller is source-inspected |
| Ten additional invalid witnesses were rejected | supplemental/results/native-proofs.json, constraint_controls; native-generation.log | Rerun TestSupplementalFixtures | Constraint-solver controls, not mined transactions |
| Extra uniform data charge could change the comparison | Original paired rows and supplemental analysis, delta/128 | Divide the measured total-gas delta by 128 saved bytes | Explicit hypothetical linear model, not a network quote |

## Verification levels

1. **Reading:** open tables and raw records. This inspects a report.
2. **Saved audit:** run python3 verify_all.py. This checks file identities, bindings and calculations.
3. **Fresh baseline execution:** run reproduce.py --evm --native with the recorded toolchains.
4. **Fresh variant execution:** run supplemental/reproduce.py with those toolchains. New proof bytes need not match the saved randomized proofs.
5. **Public execution record:** inspect the actual GitHub Actions run, revision and artifact. A workflow definition alone does not establish execution.

The separate original 50-proof native regeneration check remains in reviewer/. It was native-only and is not counted as a supplemental Solidity result.

The pinned EnygmaV1 verifyTransferProof function selects the uncompressed verifyProof wrapper and requires a true result. This is a source-level observation, not a mapped or executed production deployment.
