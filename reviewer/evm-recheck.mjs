import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn} from 'node:child_process';
import solc from 'solc';
import {JsonRpcProvider,ContractFactory} from 'ethers';

const root=path.resolve(process.env.DAVID_STUDY_ROOT||'..');
const directory=path.join(root,'results');
const R=21888242871839275222246405745257275088548364400416034343698204186575808495617n;
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const assert=(condition,message)=>{if(!condition)throw new Error(message);};
const allContracts={};
const sources={};
for(let k=2;k<=6;k++){
 const filename=`EnygmaVerifierk${k}.sol`;
 const content=fs.readFileSync(path.join(root,'contract-verifiers',filename),'utf8');
 sources[filename]={content};
}
const input={language:'Solidity',sources,settings:{optimizer:{enabled:true,runs:200},evmVersion:'shanghai',outputSelection:{'*':{'*':['abi','evm.bytecode.object','evm.deployedBytecode.object']}}}};
const built=JSON.parse(solc.compile(JSON.stringify(input)));
const errors=(built.errors||[]).filter(x=>x.severity==='error');assert(!errors.length,JSON.stringify(errors));
fs.writeFileSync(path.join(directory,'solc-input.json'),JSON.stringify(input,null,2)+'\n');
fs.writeFileSync(path.join(directory,'solc-diagnostics.json'),JSON.stringify(built.errors||[],null,2)+'\n');
for(let k=2;k<=6;k++)allContracts[k]=built.contracts[`EnygmaVerifierk${k}.sol`][`EnygmaVerifierk${k}`];

function bytesInfo(data){
 const b=Buffer.from(data.slice(2),'hex');let zeros=0;
 for(const x of b)if(x===0)zeros++;
 return {calldata_bytes:b.length,calldata_zero_bytes:zeros,calldata_nonzero_bytes:b.length-zeros,intrinsic_gas:21000+zeros*4+(b.length-zeros)*16};
}
function errorData(error){
 const candidates=[error?.data,error?.info?.error?.data?.result,error?.info?.error?.data,error?.error?.data];
 for(const x of candidates)if(typeof x==='string'&&x.startsWith('0x'))return x;
 return null;
}

for(let runIndex=1;runIndex<=3;runIndex++){
 const proofFile=path.join(directory,`proofs-run-${runIndex}.json`);
 assert(fs.existsSync(proofFile),`Missing ${proofFile}`);
 const proofRun=JSON.parse(fs.readFileSync(proofFile,'utf8'));
 const port=18545+runIndex;
 const url=`http://127.0.0.1:${port}`;
 const executable=process.env.DAVID_ANVIL_PATH||path.join(root,'toolchain','foundry',process.platform==='win32'?'anvil.exe':'anvil');
 const local=spawn(executable,['--host','127.0.0.1','--port',String(port),'--chain-id','31337','--hardfork','shanghai','--accounts','2','--gas-limit','30000000','--silent'],{stdio:['ignore','ignore','pipe']});
 let stderr='';local.stderr.on('data',x=>{stderr+=x.toString();});
 let online=false;
 for(let attempt=0;attempt<50;attempt++){
  if(local.exitCode!==null)throw new Error('Anvil exited: '+stderr);
  try{const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:1,method:'eth_chainId',params:[]})});const b=await r.json();if(b.result==='0x7a69'){online=true;break;}}catch{}
  await new Promise(resolve=>setTimeout(resolve,100));
 }
 assert(online,'Local Anvil did not start: '+stderr);
 const provider=new JsonRpcProvider(url,31337,{staticNetwork:true,cacheTimeout:-1});provider.pollingInterval=10;
 try{
 const signer=await provider.getSigner();
 const observedClient=await provider.send('web3_clientVersion',[]);
 const observedChain=await provider.send('eth_chainId',[]);
 const contracts={};
 const report={reviewer_observed_client:observedClient,reviewer_observed_chain:observedChain,scope:'Local Shanghai EVM verifier-only transactions using pinned Rayls contract-repository verifiers; not Rayls mainnet gas, USDr fees or end-to-end private payments',contract_source_commit:'ed8863885c8ed5d5d317d47a34c063907192687a',run_id:`run-${runIndex}`,started_utc:new Date().toISOString(),solc_version:solc.version(),compiler_settings:input.settings,chain_id:31337,hardfork:'shanghai',anvil_version:'1.3.1',proof_source_sha256:sha(fs.readFileSync(proofFile)),compression_scope:'compressProof was evaluated by a local read-only call; reported gas excludes any separate compression transaction',deployments:[],verification_transactions:[],controls:[]};
 for(let k=2;k<=6;k++){
  const artifact=allContracts[k];
  const factory=new ContractFactory(artifact.abi,'0x'+artifact.evm.bytecode.object,signer);
  const c=await factory.deploy();await c.waitForDeployment();contracts[k]=c;
  const receipt=await c.deploymentTransaction().wait();
  const deployedCode=await provider.getCode(await c.getAddress());
  assert(deployedCode==='0x'+artifact.evm.deployedBytecode.object,'Deployed runtime mismatch');
  report.deployments.push({observed_runtime_bytecode:deployedCode,k,address:await c.getAddress(),transaction_hash:receipt.hash,status:receipt.status,gas_used:receipt.gasUsed.toString(),runtime_bytecode_sha256:sha(Buffer.from(artifact.evm.deployedBytecode.object,'hex'))});
 }
 async function transact(contract,functionName,args,extra={}){
  const data=contract.interface.encodeFunctionData(functionName,args);
  const tx=await signer.sendTransaction({to:await contract.getAddress(),data,gasLimit:5000000n});
  let receipt;try{receipt=await tx.wait();}catch(e){receipt=e.receipt;if(!receipt)throw e;}
  const rawReceipt=await provider.send('eth_getTransactionReceipt',[receipt.hash]);
  const rawTransaction=await provider.send('eth_getTransactionByHash',[receipt.hash]);
  const info=bytesInfo(data);
  return {raw_receipt:rawReceipt,raw_transaction:rawTransaction,function:functionName,transaction_hash:receipt.hash,block_number:receipt.blockNumber,status:receipt.status,gas_used:receipt.gasUsed.toString(),...info,execution_gas_excluding_intrinsic:(receipt.gasUsed-BigInt(info.intrinsic_gas)).toString(),calldata:data,...extra};
 }
 for(const sample of proofRun.samples){
  const k=sample.k,c=contracts[k];
  const raw=sample.proof_hex.slice(2);
  const proof=Array.from({length:8},(_,i)=>BigInt('0x'+raw.slice(64*i,64*(i+1))));
  const publicInputs=sample.public_signals.map(BigInt);
  const compressed=Array.from(await c.compressProof.staticCall(proof));
  assert(compressed.length===4,'Unexpected compressed proof length');
  const routes=[
   {mode:'direct_uncompressed',functionName:'verifyProofInternal',proofBytes:256,args:inputs=>[proof,inputs]},
   {mode:'compressed',functionName:'verifyCompressedProof',proofBytes:128,args:inputs=>[compressed,inputs]},
   {mode:'legacy_uncompressed',functionName:'verifyProof',proofBytes:256,args:inputs=>[proof.slice(0,2),[proof.slice(2,4),proof.slice(4,6)],proof.slice(6,8),inputs],returnsBool:true},
  ];
  for(const route of routes){
   const {functionName,proofBytes}=route;
   const answer=await c[functionName].staticCall(...route.args(publicInputs));
   if(route.returnsBool)assert(answer===true,'Legacy wrapper did not return true for a valid proof');
   const row=await transact(c,functionName,route.args(publicInputs),{mode:route.mode,k,trial:sample.trial,proof_accepted:true,read_only_result:route.returnsBool?'true':'returned without revert',proof_component_bytes:proofBytes,public_input_count:publicInputs.length,public_input_component_bytes:publicInputs.length*32,compressed_words:compressed.map(String)});
   assert(row.status===1,`Valid proof transaction failed: k=${k}`);
   assert(row.calldata_bytes===4+proofBytes+publicInputs.length*32,'Unexpected calldata size');
   report.verification_transactions.push(row);
  }
  if(sample.trial===0){
   const altered=[...publicInputs];altered[0]=(altered[0]+1n)%R;
   for(const route of routes){
    const {functionName}=route;let parsed,answer;
    try{answer=await c[functionName].staticCall(...route.args(altered));}catch(e){const data=errorData(e);if(data)parsed=c.interface.parseError(data)?.name;}
    if(route.returnsBool)assert(answer===false,'Legacy wrapper accepted altered public input');
    else assert(parsed==='ProofInvalid',`Altered public input did not decode as ProofInvalid: ${parsed}`);
    const row=await transact(c,functionName,route.args(altered),{mode:route.mode,k,control:'altered public input with original proof',proof_accepted:false,read_only_result:route.returnsBool?'false':'reverted',decoded_error:parsed||null});
    assert(row.status===(route.returnsBool?1:0),'Unexpected transaction receipt for rejected proof');report.controls.push(row);
   }
  }
 }
 // A noncanonical public scalar must be rejected before it can be treated as a valid input.
 {
  const sample=proofRun.samples.find(x=>x.k===2&&x.trial===0),c=contracts[2];
  const raw=sample.proof_hex.slice(2);const points=Array.from({length:8},(_,i)=>BigInt('0x'+raw.slice(64*i,64*(i+1))));
  const inputs=sample.public_signals.map(BigInt);inputs[0]=R;
  let parsed;try{await c.verifyProofInternal.staticCall(points,inputs);}catch(e){const data=errorData(e);if(data)parsed=c.interface.parseError(data)?.name;}
  assert(parsed==='PublicInputNotInField',`Range control error: ${parsed}`);
  const row=await transact(c,'verifyProofInternal',[points,inputs],{mode:'direct_uncompressed',k:2,control:'public input equal to scalar-field modulus',proof_accepted:false,read_only_result:'reverted',decoded_error:parsed});
  assert(row.status===0,'Out-of-field input unexpectedly accepted');report.controls.push(row);
 }
 assert(report.verification_transactions.length===150,'Unexpected number of successful verification transactions');
 assert(report.controls.length===16,'Unexpected number of negative controls');
 const out=path.join(directory,`evm-run-${runIndex}.json`);fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({run:runIndex,accepted_proof_transactions:report.verification_transactions.length,rejected_proof_controls:report.controls.length,reverted_control_transactions:report.controls.filter(x=>x.status===0).length,successful_receipts_returning_false:report.controls.filter(x=>x.status===1).length,deployments:report.deployments.length}));
 }finally{await provider.destroy();local.kill('SIGTERM');}
}
