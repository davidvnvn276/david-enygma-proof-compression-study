# Does Compressing a ZK Proof Save Gas? A Rayls Enygma Experiment

A smaller zero-knowledge proof does not automatically mean a cheaper verification transaction.

In this local experiment with published Rayls Enygma artifacts, compression reduced the proof component from 256 to 128 bytes. However, total verifier calldata fell by only 6.88% to 15.31%, and compressed verification consumed more gas in all 150 paired comparisons under the tested Shanghai EVM configuration.

The useful question is where the saving occurs, and what computation is needed to obtain it.

## What I measured

Rayls documents Enygma as a mechanism for moving value between Sovereign chains while the Private Network Hub verifies proofs over committed balances. A complete payment includes encrypted messages and other processing as well as proof verification. [1]

I isolated the verifier to answer one narrower question: for the same valid proof and public inputs, how do compressed and uncompressed verification differ in calldata size and transaction gas?

The study covers five transfer profiles, k=2 through k=6. Here, k is the number of participant positions in the transfer circuit, including zero-valued positions. It is not a transaction count or a measure of privacy strength.

For each profile, the synthetic fixture starts the sender with 100 units and transfers 30 to one recipient. Remaining positions have zero transfer values. These are test units, not real deposits or mainnet funds.

I ran three fresh Go processes. Each generated two warmup proofs per profile, excluded from the measurements, followed by ten recorded proofs per profile. That produced 150 recorded proofs, each checked natively before Solidity verification.

Each recorded proof then went through three entry points on locally deployed Rayls verifiers: direct uncompressed verification, compressed verification, and the Rayls-facing uncompressed boolean wrapper. Across three fresh local EVM processes, that produced 450 accepted proof-verification transactions and 150 paired compression comparisons.

The proofs are randomized repetitions of one fixture per profile. They are not 150 different payment scenarios.

## The proof halves, but the public inputs remain

A BN254 Groth16 proof contains two G1 points and one G2 point. The uncompressed representation used here occupies 256 bytes; the compressed representation occupies 128. Recovering the omitted coordinates requires computation. This size-versus-computation trade-off is established cryptographic engineering, described by the verifier-template author, Remco Bloemen. [4]

In these Enygma profiles, the number of public inputs is 8k + 2. Compression does not remove them.

The complete verifier calldata therefore includes a four-byte function selector, the proof representation, and 32 bytes for each public input.

| Profile | Public inputs | Uncompressed calldata | Compressed calldata | Calldata reduction |
| --- | ---: | ---: | ---: | ---: |
| k=2 | 18 | 836 bytes | 708 bytes | 15.31% |
| k=3 | 26 | 1,092 bytes | 964 bytes | 11.72% |
| k=4 | 34 | 1,348 bytes | 1,220 bytes | 9.50% |
| k=5 | 42 | 1,604 bytes | 1,476 bytes | 7.98% |
| k=6 | 50 | 1,860 bytes | 1,732 bytes | 6.88% |

Each profile saves exactly 128 calldata bytes. As public inputs grow, those 128 bytes become a smaller fraction of the call.

This is why a claim about a 50% smaller proof must not become a claim about a 50% smaller transaction.

## Less calldata, more verification gas in this configuration

Gas was taken from mined local transaction receipts. The figures below are medians across 30 recorded proofs per profile.

| Profile | Direct uncompressed gas | Compressed gas | Median paired increase |
| --- | ---: | ---: | ---: |
| k=2 | 332,197 | 342,100 | 2.98% |
| k=3 | 387,577 | 397,388 | 2.53% |
| k=4 | 442,975 | 452,913.5 | 2.24% |
| k=5 | 498,449 | 508,383.5 | 1.99% |
| k=6 | 553,865 | 563,741 | 1.78% |

The percentage column is the median of each proof's paired percentage change. It is not calculated by subtracting the two column medians. A half-gas median results from averaging the two middle observations; individual transactions consume integer gas units.

All 150 compressed-versus-direct comparisons increased gas. The compressed route also consumed more gas than the uncompressed boolean-wrapper route in every recorded comparison.

One k=2 pair makes the accounting concrete. The uncompressed call consumed 332,209 gas and the compressed call consumed 342,284 gas. The shorter calldata saved 2,048 intrinsic gas, while execution excluding intrinsic gas increased by 12,123. The net change was therefore:

12,123 additional execution gas minus 2,048 saved intrinsic gas = 10,075 additional total gas.

The reconciliation script checks this identity for every recorded pair. The execution difference includes the differences between the two verifier entry points; it is not an isolated opcode-level measurement of decompression alone.

Compression was obtained through a read-only local call. These figures exclude any separate transaction to compress a proof.

The result does not establish that compression is always uneconomic. Different execution or data-pricing rules can change the trade-off. It establishes the outcome for these pinned contracts under the specified EVM configuration.

## Checking that the measured proofs were accepted

The test used published proving and verifying keys, rather than a newly generated setup. Selected key and generated-verifier artifact hashes match the published ceremony manifest's release 2. Recompiled circuit hashes and constraint counts match the manifest for all five profiles. [2]

I also compared the numeric constant assignments in the generated verifiers with the corresponding contracts-repository verifiers. They match across all five profiles. The actual Solidity contracts deployed for the benchmark came from the pinned contracts repository. [3]

These checks establish artifact consistency. They do not independently validate the trusted-setup ceremony or prove that its secret material was destroyed.

There were 48 additional rejection controls. Changing a public input while retaining the proof was rejected by each verification route. A separate out-of-field input control was also rejected in each local EVM run.

The outcome needs careful interpretation: 33 control transactions reverted, while 15 calls to the boolean wrapper returned false despite successful transaction receipts. The wrapper catches verification failure. Its receipt status alone therefore does not establish proof acceptance.

The pinned EnygmaV1 caller explicitly requires that wrapper's return value to be true. This control is not evidence that an invalid proof can authorize a payment. The full payment caller was inspected in source, not executed in this benchmark.

## What this tells an institution evaluating private settlement

The relevant engineering distinction is between proof size, complete call size, verifier computation and complete payment cost.

This experiment measures the first three. It shows exactly how a fixed 128-byte saving becomes less significant as the public-input component grows, and how computation can outweigh the associated calldata-gas saving.

It does not price an institutional transfer. Enygma's documented flow also involves encrypted messages, relayers and Hub processing. None of those are included in these standalone verifier transactions. [1]

For the same reason, the reported gas units must not be presented as Rayls mainnet USDr fees, production throughput, settlement latency or the cost of an entire private payment.

## Reproduce the result

The evidence package contains the 150 preserved proofs and their public inputs, native run logs, three local EVM reports, five verifier sources, published key artifacts, compiler input, source pins, paired comparisons and a Python reconciliation script.

The README explains how to check the saved calculations, rerun Solidity verification with the preserved proofs, and regenerate proofs from the pinned upstream repository. No funded wallet or live-network transaction is required for this local experiment.

Recorded configuration: Anvil 1.3.1, Shanghai hardfork, chain ID 31337; Solidity 0.8.30 with optimizer enabled for 200 runs and Shanghai target; Go 1.26.2, gnark 0.14.0 and gnark-crypto 0.19.2. Measurements were captured on October 27, 2026. Native proof-generation timings are retained as context, but the shared-machine timings do not support a production performance claim.

The practical finding is specific: for these Rayls Enygma verifier profiles, halving the proof representation reduced calldata, while increasing local verification gas. A cost comparison needs both measurements.

## Sources

[1] Rayls documentation, How Enygma works:
https://docs.rayls.com/docs/how-enygma-works

[2] Published proof-generation source and ceremony manifest, pinned commit be20e7fb1fcbafccbc5450d0b5900e27c2e53788:
https://github.com/raylsnetwork/rayls-sovereign-gnark-api/tree/be20e7fb1fcbafccbc5450d0b5900e27c2e53788
https://github.com/raylsnetwork/rayls-sovereign-gnark-api/blob/be20e7fb1fcbafccbc5450d0b5900e27c2e53788/ceremony/manifest.json

[3] Rayls contract source, pinned commit ed8863885c8ed5d5d317d47a34c063907192687a:
https://github.com/raylsnetwork/rayls-sovereign-contracts/tree/ed8863885c8ed5d5d317d47a34c063907192687a/src/rayls-protocol/Enygma/Enygma-Payments

[4] Remco Bloemen, BN254 Point Compression for L2s:
https://xn--2-umb.com/23/bn254-compression/
