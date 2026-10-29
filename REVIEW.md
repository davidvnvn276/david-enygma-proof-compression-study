# Reproducibility review

## Scope

The question is whether the available compressed and uncompressed entry points of five pinned Rayls Enygma verifiers differ in complete calldata and transaction gas. The executed environment is a local Shanghai EVM. Full Enygma payment execution, relayers, Hub settlement, mainnet prices and a production deployment mapping are outside the experiment.

## Original experiment and first review

The original 55-file research package remains unchanged under original/, including its 54-entry manifest.

The original analysis reconciled 150 randomized proofs, 450 accepted Solidity calls and 48 rejection controls across three fresh EVM processes. A separate replay repeated the calls with raw transaction/receipt capture and matched every original calldata and gas result.

Five contract verifier sources matched the pinned contracts repository. The source archive matched 82 Go/source-manifest blobs. Fifteen key/generated-verifier artifacts matched ceremony release 2, and numeric constant assignments matched across the two verifier-source locations. The first review also generated and natively verified another 50 proofs. Those 50 were native-only checks.

## Additional executed experiment

The original study repeatedly used one witness family per profile. The supplement adds three variants for each k=2 through k=6:

- Move the sender to the final participant position and send one of 1,000 units to position zero.
- Spend all 100 units, with the final position receiving 100.
- Send 60 units equally to all k−1 recipient positions. At k=2 there is one recipient; the larger profiles exercise multiple positive recipients.

Three randomized proofs per variant produced 45 new native proofs. The same proof bytes and public signals were then submitted through each of the three unmodified Solidity verifier entry points.

The captured supplement contains 135 accepted verification transactions and 45 paired compressed/direct comparisons. All 45 pairs increased transaction gas, by 9,615–10,175 gas. Submission order reverses on alternate trials.

These are 15 synthetic witness variants, not 45 distinct institutional workflows. Fixtures reuse the upstream helper's public test secrets and are isolated cases rather than an application-level sequence.

## Execution traces

Trial zero of every supplemental variant was selected for tracing: 15 pairs and 30 transactions.

Both routes made 8k+2 elliptic-curve addition calls, 8k+2 scalar multiplication calls and one pairing-precompile call in each traced sample. The compressed route made five additional calls to modular exponentiation at address 0x05.

The five calls consumed 6,701 callee gas in every selected compressed trace. The paired intrinsic calldata savings were 2,024–2,060 gas, so the extra exponentiation cost alone exceeded the saving in those samples.

Raw call traces are bound to the transaction input, target and receipt gas. Callee gas excludes surrounding opcodes and other entry-point differences. This is not a claim that 6,701 gas is the entire cost of decompression or that every proof was traced.

## Controls and evidence bindings

The supplement adds 60 mined rejection controls:

- 45 altered-public-input calls: five profiles × three witness cases × three entry points.
- 15 wrong-profile-proof calls: five profiles × three entry points.

All rejected the proof. Forty receipts reverted; 20 boolean-wrapper receipts succeeded while the verification returned false.

Ten separate native constraint controls rejected insufficient sender balances and nonzero-sum transfers. They are solver observations, not mined transactions.

The saved checker verifies exact fixture coverage, published circuit identities, native report hashes, proof/public-input/ABI bindings, raw receipt and transaction identities, recipient and block bindings, runtime identity, gas decomposition and selected trace counts. Four copied-record mutations exercise this supplementary checker. They are not four protocol vulnerabilities.

The original review checker was strengthened with explicit ABI selectors and additional raw receipt, decoded-error, recipient and block checks. Existing original records pass these additional checks.

## Source-level caller boundary

The inspected EnygmaV1 transfer flow selects the uncompressed verifyProof wrapper and requires its boolean result to be true. Available compressed-verifier entry points were compared in isolation. Their existence does not establish that the compressed route is selected by a mapped production payment.

A valid standalone proof does not alone establish the full caller's state, nullifier, participant, message or transport requirements. No full-payment acceptance or invalid-payment bypass is claimed.

## Article, figures and reader instructions

The revised article separates original and supplemental observations, explains the traced computation and labels the hypothetical uniform-data-charge calculation as a model rather than executed repricing.

The five figures contain a 5:2 cover and four 16:9 internal graphics. Numerical tables are checked against the saved results; the original Rayls logo is embedded unchanged. The new trace figure identifies its 15-pair scope and distinguishes callee cost from full execution overhead.

The reader README explains browser inspection, Windows saved-data checks, hosted GitHub execution and local Linux reproduction. verify_all.py provides a standard-library entry point for saved-data and content checks. It does not execute cryptographic verification itself.

## Repository integrity and CI

The initial public revision, 50b088bcb4f9846970fe1c08a8275ed2673e8082, contained all 95 initially distributed files. Two CSVs had only CRLF-to-LF changes relative to the reviewed ZIP. Restoring the original bytes restored the original expected hashes without changing any numeric cell or original manifest entry. The included .gitattributes preserves stored bytes across Git platforms.

The workflow is configured to execute both original and supplemental launchers, with pinned actions/toolchains and retained run artifacts. A local success or the existence of that workflow is not a public CI success. Public status must be checked for the actual run and commit.

## Remaining limitations

The general compression/computation trade-off is known. The contribution is measured behavior for the pinned Rayls artifacts with explicit paired inputs, witness variants, call traces and reproducible records.

Only one compiler/hardfork configuration and a small set of synthetic witness variants were examined. No diverse commercial workload, current production fee schedule, privacy strength or production performance was established.

Artifact identities do not independently validate the trusted-setup ceremony or establish deletion of secret setup material. A hosted rerun can improve reproducibility but does not convert this component benchmark into live network or full-payment testing.

