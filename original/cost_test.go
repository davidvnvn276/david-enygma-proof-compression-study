// Research harness added locally; upstream circuits and fixture helpers are unchanged.
package davidcoststudy

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math/big"
	"os"
	"path/filepath"
	"runtime"
	"testing"
	"time"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark-crypto/ecc/bn254/fr"
	"github.com/consensys/gnark/backend/groth16"
	native "github.com/consensys/gnark/backend/groth16/bn254"
	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/frontend/cs/r1cs"
	enygma "github.com/raylsnetwork/rayls-sovereign-gnark-api/pkg/circuits/enygma/enygma-payments/enygma-transfer"
	"github.com/raylsnetwork/rayls-sovereign-gnark-api/pkg/circuits/enygma/enygma-payments/internal/paytest"
)

type circuitProfile struct {
	K            int    `json:"k"`
	Constraints  int    `json:"constraints"`
	PublicInputs int    `json:"public_inputs"`
	R1CSHash     string `json:"r1cs_sha256"`
	ProofBytes   int    `json:"uncompressed_solidity_proof_bytes"`
}
type sample struct {
	K             int      `json:"k"`
	Trial         int      `json:"trial"`
	ProveNS       int64    `json:"prove_ns"`
	VerifyNS      int64    `json:"native_verify_ns"`
	ProofHex      string   `json:"proof_hex"`
	PublicSignals []string `json:"public_signals"`
}
type run struct {
	Scope      string           `json:"scope"`
	RunID      string           `json:"run_id"`
	Started    string           `json:"started_utc"`
	GoVersion  string           `json:"go_version"`
	GOMAXPROCS int              `json:"gomaxprocs"`
	CPUCount   int              `json:"logical_cpus_visible"`
	Warmups    int              `json:"warmups_per_profile"`
	Recorded   int              `json:"recorded_trials_per_profile"`
	SourcePin  string           `json:"source_commit"`
	Profiles   []circuitProfile `json:"profiles"`
	Samples    []sample         `json:"samples"`
}

func newCircuit(k int) frontend.Circuit {
	switch k {
	case 2:
		return &enygma.Enygmak2Circuit{}
	case 3:
		return &enygma.Enygmak3Circuit{}
	case 4:
		return &enygma.Enygmak4Circuit{}
	case 5:
		return &enygma.Enygmak5Circuit{}
	case 6:
		return &enygma.Enygmak6Circuit{}
	default:
		panic("unsupported k")
	}
}

func TestCostStudy(t *testing.T) {
	runtime.GOMAXPROCS(2)
	root := os.Getenv("DAVID_GNARK_ROOT")
	out := os.Getenv("DAVID_COST_OUTPUT")
	id := os.Getenv("DAVID_COST_RUN_ID")
	if root == "" || out == "" || id == "" {
		t.Fatal("Set DAVID_GNARK_ROOT, DAVID_COST_OUTPUT and DAVID_COST_RUN_ID")
	}
	const warmups = 2
	const recorded = 10
	report := run{Scope: "Local proof generation and native verification with published keys; no Rayls node or relayer", RunID: id, Started: time.Now().UTC().Format(time.RFC3339Nano), GoVersion: runtime.Version(), GOMAXPROCS: runtime.GOMAXPROCS(0), CPUCount: runtime.NumCPU(), Warmups: warmups, Recorded: recorded, SourcePin: "be20e7fb1fcbafccbc5450d0b5900e27c2e53788"}
	manifestData, err := os.ReadFile(filepath.Join(root, "ceremony/manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	var manifest struct {
		Circuits []struct {
			Name        string `json:"name"`
			Hash        string `json:"r1cs_sha256"`
			Constraints int    `json:"constraints"`
		} `json:"circuits"`
	}
	if err = json.Unmarshal(manifestData, &manifest); err != nil {
		t.Fatal(err)
	}
	for k := 2; k <= 6; k++ {
		circuit := newCircuit(k)
		ccs, err := frontend.Compile(ecc.BN254.ScalarField(), r1cs.NewBuilder, circuit)
		if err != nil {
			t.Fatal(err)
		}
		var serialized bytes.Buffer
		if _, err = ccs.WriteTo(&serialized); err != nil {
			t.Fatal(err)
		}
		digest := sha256.Sum256(serialized.Bytes())
		hash := hex.EncodeToString(digest[:])
		expected := ""
		expectedConstraints := 0
		for _, record := range manifest.Circuits {
			if record.Name == fmt.Sprintf("Enygmak%d", k) {
				expected = record.Hash
				expectedConstraints = record.Constraints
			}
		}
		if hash != expected || ccs.GetNbConstraints() != expectedConstraints {
			t.Fatalf("compiled circuit k=%d differs from published manifest", k)
		}
		pk := groth16.NewProvingKey(ecc.BN254)
		vk := groth16.NewVerifyingKey(ecc.BN254)
		for _, item := range []struct {
			path string
			read func(*bytes.Reader) (int64, error)
		}{
			{filepath.Join(root, fmt.Sprintf("last_build/keys/Enygmak%dPk.key", k)), func(r *bytes.Reader) (int64, error) { return pk.ReadFrom(r) }},
			{filepath.Join(root, fmt.Sprintf("last_build/keys/Enygmak%dVk.key", k)), func(r *bytes.Reader) (int64, error) { return vk.ReadFrom(r) }},
		} {
			data, err := os.ReadFile(item.path)
			if err != nil {
				t.Fatal(err)
			}
			reader := bytes.NewReader(data)
			if _, err = item.read(reader); err != nil {
				t.Fatal(err)
			}
			if reader.Len() != 0 {
				t.Fatal("unread key bytes")
			}
		}
		assignment := newCircuit(k)
		fixture := paytest.New(t, k, 0, 100, 30)
		values := make([]*big.Int, k)
		values[0] = paytest.Neg(big.NewInt(30))
		values[1] = big.NewInt(30)
		fixture.SetTxValues(values...)
		fixture.Assign(t, assignment)
		full, err := frontend.NewWitness(assignment, ecc.BN254.ScalarField())
		if err != nil {
			t.Fatal(err)
		}
		public, err := full.Public()
		if err != nil {
			t.Fatal(err)
		}
		vector := public.Vector().(fr.Vector)
		signals := make([]string, len(vector))
		for i := range vector {
			signals[i] = vector[i].String()
		}
		if len(signals) != 8*k+2 {
			t.Fatalf("unexpected public input count %d", len(signals))
		}
		profile := circuitProfile{K: k, Constraints: ccs.GetNbConstraints(), PublicInputs: len(signals), R1CSHash: hash}
		for trial := -warmups; trial < recorded; trial++ {
			started := time.Now()
			proof, err := groth16.Prove(ccs, pk, full)
			proveTime := time.Since(started).Nanoseconds()
			if err != nil {
				t.Fatal(err)
			}
			started = time.Now()
			err = groth16.Verify(proof, vk, public)
			verifyTime := time.Since(started).Nanoseconds()
			if err != nil {
				t.Fatal(err)
			}
			raw := proof.(*native.Proof).MarshalSolidity()
			if len(raw) != 256 {
				t.Fatalf("unexpected proof length %d", len(raw))
			}
			profile.ProofBytes = len(raw)
			if trial >= 0 {
				report.Samples = append(report.Samples, sample{K: k, Trial: trial, ProveNS: proveTime, VerifyNS: verifyTime, ProofHex: "0x" + hex.EncodeToString(raw), PublicSignals: signals})
			}
		}
		report.Profiles = append(report.Profiles, profile)
		t.Logf("run=%s k=%d constraints=%d public_inputs=%d recorded_proofs=%d", id, k, profile.Constraints, len(signals), recorded)
	}
	data, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err = os.MkdirAll(filepath.Dir(out), 0755); err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(out, append(data, '\n'), 0644); err != nil {
		t.Fatal(err)
	}
}
