// Supplemental research fixtures; upstream circuits and paytest helpers are unchanged.
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
    "github.com/raylsnetwork/rayls-sovereign-gnark-api/pkg/circuits/enygma/enygma-payments/internal/paytest"
)

type variantFixture struct {
    ID string `json:"id"`
    K int `json:"k"`
    Sender int `json:"sender_position"`
    Previous int64 `json:"sender_previous_units"`
    Amount int64 `json:"transfer_units"`
    Credits []int64 `json:"recipient_units_by_position"`
}
type variantSample struct {
    K int `json:"k"`
    CaseID string `json:"case_id"`
    Trial int `json:"trial"`
    ProofHex string `json:"proof_hex"`
    PublicSignals []string `json:"public_signals"`
}
type variantControl struct {
    K int `json:"k"`
    Name string `json:"name"`
    Rejected bool `json:"rejected"`
    SolverError string `json:"solver_error"`
}
type variantReport struct {
    Scope string `json:"scope"`
    SourceCommit string `json:"source_commit"`
    Started string `json:"started_utc"`
    GoVersion string `json:"go_version"`
    Profiles []circuitProfile `json:"profiles"`
    Fixtures []variantFixture `json:"fixtures"`
    Samples []variantSample `json:"samples"`
    Controls []variantControl `json:"constraint_controls"`
    Recorded int `json:"recorded_proofs"`
}

func buildVariant(t *testing.T, f variantFixture, unbalanced bool) frontend.Circuit {
    a := newCircuit(f.K)
    p := paytest.New(t, f.K, f.Sender, f.Previous, f.Amount)
    values := make([]*big.Int, f.K)
    for i, v := range f.Credits { values[i] = big.NewInt(v) }
    values[f.Sender] = paytest.Neg(big.NewInt(f.Amount))
    if unbalanced {
        recipient := (f.Sender+1)%f.K
        values[recipient] = new(big.Int).Add(values[recipient], big.NewInt(1))
    }
    p.SetTxValues(values...)
    p.Assign(t, a)
    return a
}

func TestSupplementalFixtures(t *testing.T) {
    runtime.GOMAXPROCS(2)
    root, out := os.Getenv("DAVID_GNARK_ROOT"), os.Getenv("DAVID_COST_OUTPUT")
    if root=="" || out=="" { t.Fatal("Set DAVID_GNARK_ROOT and DAVID_COST_OUTPUT") }
    report := variantReport{
        Scope:"Supplemental synthetic witness variants, native generation followed by standalone Solidity verification; not payment execution.",
        SourceCommit:"be20e7fb1fcbafccbc5450d0b5900e27c2e53788",
        Started:time.Now().UTC().Format(time.RFC3339Nano), GoVersion:runtime.Version(),
    }
    var manifest struct { Circuits []struct { Name string `json:"name"`; Hash string `json:"r1cs_sha256"`; Constraints int `json:"constraints"` } `json:"circuits"` }
    data, err := os.ReadFile(filepath.Join(root,"ceremony/manifest.json")); if err!=nil {t.Fatal(err)}
    if err=json.Unmarshal(data,&manifest);err!=nil {t.Fatal(err)}
    for k:=2;k<=6;k++ {
        ccs,err:=frontend.Compile(ecc.BN254.ScalarField(),r1cs.NewBuilder,newCircuit(k));if err!=nil {t.Fatal(err)}
        var encoded bytes.Buffer
        if _,err=ccs.WriteTo(&encoded);err!=nil {t.Fatal(err)}
        h:=sha256.Sum256(encoded.Bytes());hash:=hex.EncodeToString(h[:])
        matched:=false
        for _,m:=range manifest.Circuits {if m.Name==fmt.Sprintf("Enygmak%d",k) {matched=m.Hash==hash&&m.Constraints==ccs.GetNbConstraints()}}
        if !matched {t.Fatalf("Circuit identity mismatch k=%d",k)}
        pk,vk:=groth16.NewProvingKey(ecc.BN254),groth16.NewVerifyingKey(ecc.BN254)
        for _,item:=range []struct{name string;read func(*bytes.Reader)(int64,error)}{
            {fmt.Sprintf("Enygmak%dPk.key",k),func(r *bytes.Reader)(int64,error){return pk.ReadFrom(r)}},
            {fmt.Sprintf("Enygmak%dVk.key",k),func(r *bytes.Reader)(int64,error){return vk.ReadFrom(r)}},
        } {
            b,e:=os.ReadFile(filepath.Join(root,"last_build/keys",item.name));if e!=nil {t.Fatal(e)}
            r:=bytes.NewReader(b);if _,e=item.read(r);e!=nil {t.Fatal(e)};if r.Len()!=0 {t.Fatal("Unread key bytes")}
        }
        moved:=variantFixture{ID:"moved_sender",K:k,Sender:k-1,Previous:1000,Amount:1,Credits:make([]int64,k)};moved.Credits[0]=1
        full:=variantFixture{ID:"full_balance",K:k,Sender:0,Previous:100,Amount:100,Credits:make([]int64,k)};full.Credits[k-1]=100
        dense:=variantFixture{ID:"all_receivers",K:k,Sender:0,Previous:1000,Amount:60,Credits:make([]int64,k)}
        for i:=1;i<k;i++ {dense.Credits[i]=60/int64(k-1)}
        for _,f:=range []variantFixture{moved,full,dense} {
            report.Fixtures=append(report.Fixtures,f)
            assignment:=buildVariant(t,f,false)
            witness,e:=frontend.NewWitness(assignment,ecc.BN254.ScalarField());if e!=nil {t.Fatal(e)}
            public,e:=witness.Public();if e!=nil {t.Fatal(e)}
            vector:=public.Vector().(fr.Vector);signals:=make([]string,len(vector))
            for i:=range vector {signals[i]=vector[i].String()}
            if len(signals)!=8*k+2 {t.Fatal("Public input count")}
            for trial:=0;trial<3;trial++ {
                proof,e:=groth16.Prove(ccs,pk,witness);if e!=nil {t.Fatalf("k=%d case=%s: %v",k,f.ID,e)}
                if e=groth16.Verify(proof,vk,public);e!=nil {t.Fatal(e)}
                raw:=proof.(*native.Proof).MarshalSolidity();if len(raw)!=256 {t.Fatal("Proof encoding length")}
                report.Samples=append(report.Samples,variantSample{K:k,CaseID:f.ID,Trial:trial,ProofHex:"0x"+hex.EncodeToString(raw),PublicSignals:signals})
            }
        }
        // These are constraint-solver controls, not onchain transactions.
        insufficient:=variantFixture{ID:"insufficient_balance",K:k,Sender:0,Previous:9,Amount:10,Credits:make([]int64,k)};insufficient.Credits[1]=10
        for _,c:=range []struct{name string;fixture variantFixture;unbalanced bool}{
            {"insufficient_sender_balance",insufficient,false},
            {"nonzero_sum_transfer",dense,true},
        } {
            w,e:=frontend.NewWitness(buildVariant(t,c.fixture,c.unbalanced),ecc.BN254.ScalarField());if e!=nil {t.Fatal(e)}
            e=ccs.IsSolved(w)
            if e==nil {t.Fatalf("Invalid witness was not rejected: k=%d %s",k,c.name)}
            report.Controls=append(report.Controls,variantControl{K:k,Name:c.name,Rejected:true,SolverError:e.Error()})
        }
        report.Profiles=append(report.Profiles,circuitProfile{K:k,Constraints:ccs.GetNbConstraints(),PublicInputs:8*k+2,R1CSHash:hash,ProofBytes:256})
        t.Logf("k=%d: three fixture variants, nine native proofs, two rejected constraint controls",k)
    }
    report.Recorded=len(report.Samples)
    if report.Recorded!=45||len(report.Fixtures)!=15||len(report.Controls)!=10 {t.Fatal("Coverage mismatch")}
    b,err:=json.MarshalIndent(report,"","  ");if err!=nil {t.Fatal(err)}
    if err=os.MkdirAll(filepath.Dir(out),0755);err!=nil {t.Fatal(err)}
    if err=os.WriteFile(out,append(b,'\n'),0644);err!=nil {t.Fatal(err)}
}
