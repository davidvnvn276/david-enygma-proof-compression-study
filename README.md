# Does Compressing a ZK Proof Save Gas? A Rayls Enygma Experiment

[![Reproduce Enygma study](https://github.com/davidvnvn276/david-enygma-proof-compression-study/actions/workflows/verify-enygma.yml/badge.svg)](https://github.com/davidvnvn276/david-enygma-proof-compression-study/actions/workflows/verify-enygma.yml)

This repository contains the data, pinned source artifacts and executable harnesses for a **local Enygma verifier benchmark**. Readers can check the saved observations, replay Solidity verification against the same proofs, and generate a separate set of fresh proofs.

The original benchmark covers five circuit profiles, three proof-generation processes and three local EVM processes. The proof representation shrank from 256 to 128 bytes, but all 150 paired compressed-versus-direct calls consumed more transaction gas under the recorded configuration. Complete calldata fell by 15.31% at k=2 and 6.88% at k=6.

This is a component benchmark. It does not measure Rayls mainnet USDr fees, complete Enygma payments, live relayer or Hub execution, production throughput, or privacy strength.

The supplement adds 15 synthetic witness variants and 45 newly generated proofs, verified natively and through all three Solidity entry points. All 45 extra pairs also increased gas. Fifteen selected paired traces show five additional modular-exponentiation calls costing 6,701 callee gas, compared with 2,024–2,060 gas saved by shorter calldata. Original and supplemental statistics remain separate.

## 0. First time checking a research repository?

Choose the route that fits your starting point:

| Starting point | Recommended route |
|---|---|
| I want to inspect a result without installing software | Read CLAIM_MAP.md and the actual GitHub Actions run |
| I want to check saved evidence on my computer | Download/extract the source, install Python, run verify_all.py |
| I want to execute cryptographic tests without a local toolchain | Fork the repository and run its GitHub Actions workflow |
| I already have a Linux development environment | Follow sections 4–7 and the supplemental command |

### A. Inspect a public run in a browser

1. Open the repository's **Actions** tab.
2. Select **Reproduce Enygma study**, then select a run.
3. Note its commit SHA, run URL and conclusion.
4. Open **Check saved evidence**. All four saved-evidence/content checks must pass.
5. Open **Replay Solidity and regenerate native proofs**. Look for 450 accepted calls, 48 rejection controls, 150 matched gas pairs and 50 separately regenerated native proofs.
6. Open **Generate variant proofs and verify them in Solidity**. Look for 45 generated proofs, 135 accepted Solidity calls, 60 rejection controls, ten rejected constraint controls and 15 traced pairs.
7. Inspect the run's artifact for the generated reports and logs. Artifact downloads require GitHub sign-in and are retained for a limited period.

A failed conclusion or skipped execution stage is not a completed reproduction. Reading a successful run inspects a public execution record; personally rerunning it is a separate action.

### B. Run the saved-data check on Windows

1. Open **Code → Download ZIP** on the chosen repository revision.
2. In File Explorer, right-click the downloaded ZIP and select **Extract All**.
3. Open the extracted directory until README.md and verify_all.py are visible together.
4. Install Python from the [official Windows downloads page](https://www.python.org/downloads/windows/) if it is not already installed. The checks use standard-library modules; the recorded review used Python 3.12.
5. Click File Explorer's address bar, type **cmd**, then press Enter. This opens a command window in that directory.
6. Run the first command below and press Enter, then run the second:

~~~powershell
py --version
py verify_all.py
~~~

Expected messages include:

~~~text
PASS: distribution_integrity
PASS: original_and_replay_evidence
PASS: supplemental_native_to_evm_evidence
PASS: article_and_figure_consistency
All saved-evidence checks passed.
~~~

The command also prints original and supplemental counts and explains its limit. It checks captured records and arithmetic; it does not execute Solidity or generate new proofs.

If py is not recognized, complete the official Python installation, reopen the command window and check py --version. If a checksum fails, retain the error and compare with an untouched checkout of the same revision. No expected checksum needs editing for a normal run.

### C. Run the cryptographic tests on GitHub

1. Sign in to GitHub.
2. Use **Fork** to create a copy of the repository under your account.
3. In the fork, open **Actions** and enable workflows if GitHub asks.
4. Select **Reproduce Enygma study → Run workflow**.
5. Select the branch, start the run, and wait for the execution stages to finish.
6. Inspect the actual outcomes and artifact using route A above.

This route installs the pinned toolchains on the hosted Linux runner. No local Go, Node.js, Anvil, wallet or private key is needed. GitHub hosting does not turn the local-EVM tests into live Rayls tests.

### What does PASS mean?

- A **manifest** lists file fingerprints. A match means the listed bytes have the expected identities.
- A **saved audit** binds captured inputs, transactions, receipts, traces and calculations.
- A **fresh execution** reruns native proof generation/verification or Solidity contracts.
- A **successful receipt** means the outer transaction completed; the boolean verification result must still be checked.

CLAIM_MAP.md links each article finding to its evidence and verification command.

## 1. Get a reproducible checkout

With Git installed:

~~~bash
git clone https://github.com/davidvnvn276/david-enygma-proof-compression-study.git
cd david-enygma-proof-compression-study
git rev-parse HEAD
~~~

Record the commit printed by the last command with any verification report. To reproduce a specific published revision, select its full commit SHA:

~~~bash
git checkout <full-commit-sha>
~~~

Alternatively, choose **Code → Download ZIP** on the repository page, extract the archive, and open a terminal in the directory containing this README, reproduce.py, original/ and reviewer/. A GitHub source archive and a clone contain the same tracked research files for that revision.

The repository's .gitattributes disables automatic text conversion so manifest-covered files retain their exact bytes across platforms. In particular, the two original CSV tables retain their original CRLF record endings.

## 2. Choose a verification stage

| Check | Requirements | What is executed |
|---|---|---|
| Saved evidence | Python 3.12 standard library | File hashes, recorded receipt/input bindings, arithmetic, coverage and checker controls |
| Fresh Solidity replay | Python, Node.js 24.22.1 and Anvil 1.3.1 | Five verifier deployments per process; 450 accepted verification transactions and 48 rejection controls across three fresh local EVMs |
| Fresh native generation | Python and Go 1.26.2 | Rebuild five circuits, check their identities, generate and natively verify 50 new recorded proofs |
| Supplemental native-to-Solidity test | Python, Go, Node.js and Anvil | Generate 45 proofs and verify them in 135 accepted calls; inspect 60 rejection controls and 15 traced pairs |
| Combined reproduction | All of the above | Saved checks, Solidity replay and native generation |
| GitHub Actions | Browser for inspection; a GitHub account for a personal rerun | The combined reproduction on a hosted Linux runner |

Python 3.12 and Linux amd64 were used for execution testing. The saved-only commands can also be invoked with the Windows Python launcher. Full native Windows and macOS execution has not been validated here.

No command requires a wallet, private key, funded account, mainnet RPC credential or mainnet transaction submission. Initial dependency and toolchain installation requires internet access.

## 3. Check the saved evidence first

From the repository root:

~~~bash
python3 verify_all.py
~~~

Or inspect the four component reports individually:

~~~bash
python3 verify_integrity.py
python3 reviewer/audit_saved.py
python3 supplemental/audit.py
python3 check_article_figures.py
~~~

On Windows, with Python installed through the Python launcher:

~~~powershell
py verify_all.py
~~~

Or inspect each component:

~~~powershell
py verify_integrity.py
py reviewer/audit_saved.py
py supplemental/audit.py
py check_article_figures.py
~~~

The verify_integrity.py component must report **status: passed** with an empty mismatches list. Its file count is the number of entries in MANIFEST_SHA256.json for the checked revision.

The reviewer/audit_saved.py component reports these selected fields:

~~~json
{
  "status": "passed",
  "original_manifest_files": 54,
  "replayed_valid_transactions": 450,
  "replayed_rejection_controls": 48,
  "paired_gas_results_exactly_reproduced": 150,
  "regenerated_proofs_in_native_check": 50
}
~~~

It also reports four copied-record mutations, all rejected. These controls alter a copied receipt's gas, a public input, a route label and an acceptance flag. They exercise the evidence checker; they are not four additional protocol vulnerabilities.

The saved-only stage checks consistency of preserved observations. It does not execute Groth16 verification or generate new proofs. Actual proof verification is rerun in the Solidity and native stages below.

The unchanged original package has its own 54-entry manifest, original/SHA256SUMS.txt. Both manifest layers are checked without accepting line-ending normalization as an equivalent byte match. Hash consistency alone does not authenticate a production chain or a trusted setup.

The supplemental report separately checks 45 new native proofs, 135 accepted Solidity calls, 60 rejection controls and 15 traced pairs. It also verifies ten recorded native constraint controls and four additional copied-record mutations. Counts from these categories are not interchangeable or added to the original medians.

## 4. Install the recorded toolchain

| Component | Fixed version or setting |
|---|---|
| Python | 3.12 used for the review |
| Node.js | 24.22.1 |
| ethers | 6.15.0, installed by the preserved npm lock |
| solc-js | 0.8.30, installed by the preserved npm lock |
| Anvil | 1.3.1 |
| Go | 1.26.2 |
| Local chain ID | 31337 |
| EVM hardfork and compiler target | Shanghai |
| Solidity optimizer | Enabled, 200 runs |

Install Node.js and Go from their official distributions: [Node.js downloads](https://nodejs.org/en/download) and [Go downloads](https://go.dev/dl/). Select the versions above when reproducing this fixed benchmark.

Check the installed versions:

~~~bash
python3 --version
node --version
npm --version
go version
~~~

Go is only needed for native generation. Node.js and Anvil are only needed for the EVM stage. No third-party Python package is required.

On Linux amd64, download the pinned official Anvil archive through the included checksum-verifying helper:

~~~bash
python3 reviewer/install_anvil.py --output tools/anvil
tools/anvil --version
~~~

The expected archive SHA-256 is:

~~~text
baad3e1b06d6f310d210c93e95258a03d923fe610f8d0742138f2245f94abd7c
~~~

This archive identity was compared with official release metadata during review. The helper is Linux amd64 only; the downloaded binary is not a native Windows executable.

## 5. Replay the preserved proofs in fresh local EVMs

From the repository root:

~~~bash
python3 reproduce.py --evm --anvil tools/anvil --output runs/evm-1
~~~

The launcher first checks both manifest layers and the saved observations. It then creates a new working copy, installs locked npm dependencies, deploys the five verifiers in each of three fresh Anvil processes, and submits the original proofs through all three verifier entry points.

Expected results:

- 450 accepted verification transactions.
- 48 rejected-proof controls: 33 reverted transactions and 15 successful wrapper receipts with a false verification result.
- 150 exact matches for the original paired calldata and gas results.
- A final reproduction-summary.json with status set to passed.

The same preserved proof bytes should reproduce gas under the fixed compiler and hardfork. Transaction hashes and timestamps can differ. Those differences alone are not proof or gas mismatches.

The process uses localhost ports 18546, 18547 and 18548. The original/ and reviewer/ directories are not overwritten. Existing output directories are rejected; select a new output name for another run.

## 6. Generate and verify fresh native proofs

With Go 1.26.2 on PATH:

~~~bash
python3 reproduce.py --native --output runs/native-1
~~~

For an explicitly selected Go executable:

~~~bash
python3 reproduce.py --native --go /absolute/path/to/go --output runs/native-2
~~~

The launcher extracts the included pinned source archive into the new output directory. It restores the included published proving/verifying keys, places the authored test fixture in the upstream package tree, and executes the Go test.

The test recompiles the five unmodified circuit profiles and checks their serialized R1CS identities and constraint counts against the manifest. It generates two excluded warmups and ten recorded proofs per profile, then verifies the proofs natively.

Expected results:

- Five matching circuit profiles, k=2 through k=6.
- Constraint counts of 15,938; 21,190; 26,442; 31,694; and 36,946.
- 50 new recorded proofs and ten excluded warmups.
- A final reproduction-summary.json with status set to passed.

New proofs are randomized and need not match the original proof bytes. This stage checks native validity. It does not submit the new proofs to Solidity, and the new proofs are not added to the original 150-pair gas statistics. It does not perform a new trusted setup or independently replay the ceremony.

### 6.1 Generate variant proofs and verify those same proofs in Solidity

With the same toolchains:

~~~bash
python3 supplemental/reproduce.py --anvil tools/anvil --output runs/variants-1
~~~

Add --go /absolute/path/to/go if Go is not on PATH. The command:

1. Runs all saved-evidence checks.
2. Creates a new output directory and extracts the pinned source.
3. Rebuilds the five circuits and checks their manifest identities.
4. Generates and natively verifies three randomized proofs for each of 15 synthetic witness variants.
5. Rejects ten invalid witnesses through the native constraint solver.
6. Deploys the unchanged pinned Solidity verifiers on a fresh local Anvil process.
7. Verifies the newly generated proofs through all three entry points, reversing route order on alternate trials.
8. Executes 60 invalid-proof controls and captures 30 call traces for 15 selected pairs.
9. Binds native records to calldata, raw receipts, observed runtime and traces, then recalculates paired costs.

Expected: 45 new proofs, 135 accepted verification transactions, 60 rejected-proof calls (40 reverted receipts and 20 wrapper receipts returning false), ten rejected constraint controls and 15 traced pairs.

The three variants are moved_sender, full_balance and all_receivers. The last has k−1 positive recipients; k=2 still has one recipient. They are isolated synthetic witness cases, not a sequence of application payments. They reuse the upstream helper's public test secrets and are not production identities.

The supplemental process uses localhost port 18549. Outputs include native-proofs.json, evm-report.json, analysis.json, native-generation.log, evm-execution.log, fresh-audit.log and reproduction-summary.json. New randomized proofs need not match saved bytes or sample-level gas; their own paired costs are recomputed.

The original medians remain unchanged. The 50-proof regeneration in section 6 is native-only; this 45-proof stage explicitly connects native generation to Solidity.

## 7. Run the original reproduction and the supplement

With Go 1.26.2 on PATH:

~~~bash
python3 reproduce.py --evm --native --anvil tools/anvil --output runs/complete-1
~~~

Alternatively, add --go /absolute/path/to/go. The EVM stage replays the original 150 proofs; the native stage generates a separate 50-proof set.

Then run the supplemental command from section 6.1 using a new output directory. GitHub Actions executes both launchers in that order. The source scripts and captured records for these two experiments remain separate.

Inspect the outputs under the requested output directory:

| Output | Meaning |
|---|---|
| integrity.log | Reviewed-distribution file identity check |
| saved-audit.log | Original manifest and recorded observation checks |
| npm-install.log | Locked EVM dependency installation |
| evm-replay.log | Fresh local EVM execution |
| replayed-analysis.log | Recomputed analysis of the replay |
| evm-study/results/evm-run-*.json | Fresh reports with raw transactions and receipts |
| native-generation.log | Circuit rebuild and native proof verification |
| regenerated-proofs.json | Fresh native proof records |
| reproduction-summary.json | Completed stages, counts and final outcome |

A command failure exits nonzero and names its log. Missing stages or a missing final summary do not establish a complete pass. Run without Python's -O flag because the unchanged original analyzer uses assertions.

## 8. Inspect or rerun public CI

Open [Reproduce Enygma study in GitHub Actions](https://github.com/davidvnvn276/david-enygma-proof-compression-study/actions/workflows/verify-enygma.yml). Select a run and record its commit SHA, conclusion and logs. A workflow file or a status badge alone is not evidence that every historical revision passed.

The workflow uses immutable action commit pins, recorded Node/Go versions and the checksum-verified Anvil release. It runs all saved checks, original Solidity replay, the separate 50-proof native regeneration, and the supplemental native-to-Solidity experiment. Its final artifact contains run logs, proof records, replay reports, call traces and reproduction summaries when those files were produced.

To rerun independently in a personal GitHub environment:

1. Fork this repository to an account with GitHub Actions available.
2. Enable Actions for the fork if GitHub requests it.
3. Open Actions → Reproduce Enygma study → Run workflow.
4. Select the revision's branch and start the run.
5. Inspect the actual conclusion, step logs and artifact. Record the commit and run URL with the result.

On this repository, manually starting a run requires write access. Existing public logs can be inspected without local toolchain installation. Downloading workflow artifacts requires a signed-in GitHub account, and artifacts have a limited retention period.

CI is another reproducibility environment for this local component benchmark. It is not live Rayls transport, Hub or production testing.

## 9. Map the article's claims to the evidence

| Claim | Evidence |
|---|---|
| 150 original randomized recorded proofs | original/results/proofs-run-1.json through proofs-run-3.json |
| 450 accepted original verification calls and 48 rejection controls | original/results/evm-run-1.json through evm-run-3.json |
| Per-profile medians | original/results/summary.json and profile-summary.csv |
| All 150 paired gas calculations | original/results/paired-comparisons.csv |
| Raw replay receipt, calldata and deployed-runtime bindings | reviewer/evm-run-*.json and reviewer/audit_saved.py |
| Separate 50-proof native regeneration | reviewer/regenerated-proofs.json and native-regeneration.log |
| Published-key and verifier artifact identities | reviewer/source-and-artifact-checks.json and original/gnark-reference/ceremony/manifest.json |
| Pinned source archive identities | reviewer/source-archive-checks.json and github-gnark-tree.json |
| Contracts-repository verifier identities | original/contract-verifier-source-index.json |
| Caller checks the wrapper boolean | original/contract-source-context/EnygmaV1.sol, verifyTransferProof |
| Solidity compiler inputs | original/results/solc-input.json |
| Review scope and implementation notes | REVIEW.md |
| Illustrated article | ARTICLE.md and ARTICLE.html |
| Supplemental proof-to-Solidity result | supplemental/results/native-proofs.json and evm-report.json |
| Fifteen selected paired call traces | raw_call_trace in supplemental/results/evm-report.json |
| Supplemental paired costs and trace counts | supplemental/results/analysis.json |
| Article paragraph to command mapping | CLAIM_MAP.md |

The circuit source is pinned to [be20e7fb1fcbafccbc5450d0b5900e27c2e53788](https://github.com/raylsnetwork/rayls-sovereign-gnark-api/tree/be20e7fb1fcbafccbc5450d0b5900e27c2e53788). Contract sources are pinned to [ed8863885c8ed5d5d317d47a34c063907192687a](https://github.com/raylsnetwork/rayls-sovereign-contracts/tree/ed8863885c8ed5d5d317d47a34c063907192687a).

The review compared five verifier sources, 82 Go/source-manifest blobs and 15 published key/generated-verifier artifacts against the recorded source/release identities. These checks establish artifact consistency, not production deployment or secret-material deletion.

## 10. Interpret the measurements

The same synthetic fixture sends 30 of 100 test units from circuit position 0 to position 1, with other transfer positions zero. There are 8k+2 public inputs. The parameter k counts participant positions; the study does not quantify anonymity or privacy strength.

The original benchmark has three fresh Go processes, 150 recorded proofs and 30 excluded warmups. Each recorded proof is checked through three Solidity routes. These are 150 paired cost observations of one fixture family, not 150 independent financial workflows.

Complete calldata contains four selector bytes, a 256- or 128-byte proof, and 32 bytes per public input. Under the tested Shanghai rules:

**Intrinsic transaction gas = 21,000 + 4 × zero calldata bytes + 16 × nonzero calldata bytes.**

**Compressed-route total gas increase = extra execution gas − saved intrinsic gas.**

The execution difference includes both entry-point implementations. It is not an isolated opcode-level cost of decompression. Compression was computed through a local read-only call; measured transactions exclude a separate compression transaction.

Paired percentages are calculated for each proof before taking the median. A fractional median averages two integer gas observations; individual transactions consume integer gas.

For altered-input controls, the direct and compressed routes revert. The boolean wrapper returns false without necessarily reverting its outer transaction. A successful receipt alone does not establish proof acceptance. The inspected EnygmaV1 caller requires the boolean result to be true; that full caller was source-inspected, not executed here.

The pinned caller selects the uncompressed verifyProof wrapper. Comparing the available compressed entry point does not establish that a current production payment uses that route.

The public-input-at-field-modulus control was exercised through the direct route once per EVM process. It is not a field-boundary test of all three routes.

The supplemental traces are selected as trial zero of each of 15 variants. The direct and compressed sides have the same ECADD/ECMUL counts and one pairing call; the compressed side adds five calls to address 0x05, totaling 6,701 callee gas in the captured traces. This is not the full entry-point or decompression overhead.

For an explicit hypothetical linear model, an extra uniform calldata charge d would change a pair's compressed-minus-direct cost by -128d. The original 10,075-gas example would break even at 10,075/128 = 78.7109375 extra gas-equivalent units per byte. This is a calculated counterfactual, not a network quote or an executed repricing experiment.

## 11. Troubleshooting

| Symptom | Interpretation and next check |
|---|---|
| Missing original/ or reviewer/ | Run from a complete checkout or extracted source archive |
| CSV checksum mismatch | Compare with tracked bytes; the preserved CSV records use CRLF. Do not change expected hashes to accept an unexplained file change |
| Other manifest mismatch | Record the revision and modified path; retry from an untouched checkout |
| Missing npm packages | The launcher runs npm ci from the preserved lock in its working copy |
| Anvil cannot execute | Check OS/CPU and release version; the supplied installer is Linux amd64 only |
| Local port already used | Use a clean environment or stop an earlier local test process |
| Output directory already exists | Use a new --output path; previous runs are retained |
| Go version or circuit-identity mismatch | Confirm Go 1.26.2 and the pinned source/key artifacts |
| Dependency download fails | Preserve the log; an unavailable dependency is not a rejected proof |
| Wrapper receipt has status 1 | Inspect the verification return value before interpreting acceptance |
| New native proof bytes differ | Randomized proof generation is expected; verify validity and circuit identities |
| CI stops before replay/native execution | Inspect the failed step; skipped stages do not count as completed tests |

## 12. Figures and their numerical checks

The package includes a 5:2 banner and four 16:9 internal figures as 3200-pixel-wide PNGs and editable SVGs. IMAGE_PLACEMENT.md maps them to article sections. The full article HTML embeds all five images.

The article/content checker compares both numerical tables with the saved analysis, checks all PNG dimensions, and verifies that every SVG embeds the original Rayls mark unchanged. It is included in verify_all.py.

Optional figure regeneration, in a separate working copy:

~~~bash
python3 -m pip install Pillow==12.3.0
python3 figures/build.py
~~~

The recorded renderer was Inkscape 1.2.2 with DejaVu fonts on Linux. The builder requires an inkscape executable on PATH and the DejaVu font files under /usr/share/fonts/truetype/dejavu. It reads the saved numerical results; it does not change any proof or receipt data. Previews are written under runs/figure-previews/.

Rendering can change PNG byte identities across renderer/font versions. Use an untouched checkout for the shipped-file manifest check. Numerical reproduction and pixel-identical rendering are separate checks.

## 13. Boundaries and provenance

The original 55-file research package is preserved under original/, including its unchanged 54-entry manifest. The separate review adds raw replay evidence, native regeneration, consistency checks and reproduction tooling.

The compression/computation trade-off is established engineering. The contribution here is a measured comparison for pinned Rayls artifacts with explicit inputs and reproducible controls.

The study does not execute a complete Enygma payment, live relayer, cross-chain transport, Hub settlement or a mapped production deployment. It does not establish mainnet pricing, production latency, a privacy guarantee, ceremony soundness or deletion of secret setup material. Native timings are shared-machine context.

Upstream source license headers and included LICENSE/NOTICE files retain their original scope. The authored benchmark, fixtures and review records are research additions; they are not official Rayls test results.

