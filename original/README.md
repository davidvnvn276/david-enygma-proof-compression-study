# Does Compressing a ZK Proof Save Gas? A Rayls Enygma Experiment

Research captured on 27 October 2026. This is a local verifier benchmark, not Rayls mainnet fees or a complete Enygma payment.

## Publication files

ARTICLE.md contains the complete English article. ARTICLE.txt contains the same text for copying. All supporting evidence is included below.

## Findings

150 recorded proofs across five transfer profiles (k=2 through k=6), three fresh Go processes, and three fresh Anvil processes. Each proof was verified through three entry points: 450 accepted local verification transactions. Another 30 warmup proofs were excluded from measurements.

The proof component shrank from 256 to 128 bytes. Full verifier calldata shrank by 15.31% at k=2 and 6.88% at k=6. All 150 paired compressed-versus-direct comparisons consumed more gas under the recorded Shanghai EVM configuration. This is a known compression/computation trade-off measured here for pinned Rayls artifacts, not a new cryptographic discovery or a vulnerability.

## Verify the saved calculations

1. Extract this ZIP into a new folder.
2. Install Python 3 if necessary.
3. Open a terminal in the extracted folder containing analyze.py.
4. Run `python3 analyze.py` (Windows: `py analyze.py`). This uses only the Python standard library.
5. Inspect results/summary.json and both CSV files. The script checks proof-to-EVM file hashes, calldata sizes and public inputs, transaction outcomes, and gas decomposition.
6. Original proof data and selected transaction receipt fields remain in the six run JSON files. The analysis regenerates derived summaries; keep a copy first if comparing files.

## Rerun local Solidity verification

1. Install Node.js (recorded version 24.22.1) and Anvil 1.3.1 from the official Foundry release.
2. Open a terminal in evm-harness and run `npm ci` to install the locked dependencies.
3. Set DAVID_STUDY_ROOT to the absolute extracted study directory and DAVID_ANVIL_PATH to the absolute Anvil executable.
4. Run `node run.mjs`. The script creates three temporary local chains on ports 18546 through 18548 and overwrites the EVM reports using preserved real proofs. Keep original results separately first.
5. Run the Python analysis again. This reruns Solidity proof verification, not proof generation. Randomly regenerated proofs may have slightly different calldata gas.

## Regenerate proofs

The authored Go harness is included as cost_test.go. Clone https://github.com/raylsnetwork/rayls-sovereign-gnark-api and check out be20e7fb1fcbafccbc5450d0b5900e27c2e53788. Place cost_test.go in pkg/circuits/enygma/enygma-payments/david-cost-study/. Copy the included published-artifacts files into that checkout's last_build directory, preserving relative paths. Install Go 1.26.2. For each run i=1,2,3, set DAVID_GNARK_ROOT to the checkout's absolute path, DAVID_COST_RUN_ID to run-i, and DAVID_COST_OUTPUT to the study's absolute results/proofs-run-i.json path. From the checkout run `go test -count=1 -timeout=10m -v ./pkg/circuits/enygma/enygma-payments/david-cost-study`. Run each as a separate process. The harness recompiles unmodified circuits, checks their manifest hashes and constraint counts, loads published keys, generates proofs and verifies them natively. It does not create a new trusted setup. Then rerun the Node harness and analysis. Linux was tested; Windows setup was not tested here.

## Method and limits

Published ceremony epoch 2 / release 2 artifacts are hash-checked, not an independent replay of the ceremony or evidence of toxic-waste deletion. The synthetic fixture sends 30 of 100 units from position 0 to position 1, with zero-valued remaining positions. Repeated randomized proofs use the same fixture; these are not 150 distinct financial workflows.

Compiler: solc 0.8.30, optimizer 200 runs, Shanghai target. Anvil 1.3.1, chain ID 31337, Shanghai hardfork. Compression was computed via a read-only local call; reported verification gas excludes a separate compression transaction. Public inputs remain unchanged. The benchmark excludes encrypted messages, token state changes, relayers, transport, Hub settlement and network pricing. No live deployment equivalence is asserted.

48 controls rejected invalid proofs: 33 transactions reverted, while 15 legacy-wrapper calls returned false with successful receipts. A successful receipt is not proof acceptance. The pinned EnygmaV1 caller checks the boolean return; this is not evidence of an acceptance bypass. Full caller execution was not tested.

Proof-generation timings are noisy context from a shared machine, not TPS, latency guarantees or scaling conclusions. Results describe the pinned implementation under this EVM configuration.

## Primary sources

- https://docs.rayls.com/docs/how-enygma-works
- https://github.com/raylsnetwork/rayls-sovereign-gnark-api/tree/be20e7fb1fcbafccbc5450d0b5900e27c2e53788
- https://github.com/raylsnetwork/rayls-sovereign-contracts/tree/ed8863885c8ed5d5d317d47a34c063907192687a
- https://xn--2-umb.com/23/bn254-compression/

Upstream license headers remain in copied files. Gnark LICENSE and NOTICE and the contracts repository LICENSE are included. Original benchmark scripts and data are research additions, not official Rayls outputs.
