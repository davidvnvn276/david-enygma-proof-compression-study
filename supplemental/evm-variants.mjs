import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn} from 'node:child_process';
import solc from 'solc';
import {JsonRpcProvider,ContractFactory} from 'ethers';

const root=path.resolve(process.env.DAVID_STUDY_ROOT);
const proofPath=path.resolve(process.env.DAVID_VARIANTS_PROOFS);
const output=path.resolve(process.env.DAVID_VARIANTS_OUTPUT);
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const require=(x,m)=>{if(!x)throw new Error(m);};
const R=21888242871839275222246405745257275088548364400416034343698204186575808495617n;
const proofs=JSON.parse(fs.readFileSync(proofPath,'utf8'));
require(proofs.samples.length===45&&proofs.fixtures.length===15,'Supplemental proof coverage');
const sources={};
for(let k=2;k<=6;k++){
 const name=`EnygmaVerifierk${k}.sol`;
 sources[name]={content:fs.readFileSync(path.join(root,'contract-verifiers',name),'utf8')};
}
const input={language:'Solidity',sources,settings:{optimizer:{enabled:true,runs:200},evmVersion:'shanghai',outputSelection:{'*':{'*':['abi','evm.bytecode.object','evm.deployedBytecode.object']}}}};
const built=JSON.parse(solc.compile(JSON.stringify(input)));
require(!(built.errors||[]).some(e=>e.severity==='error'),'Solidity compile failure');
const executable=process.env.DAVID_ANVIL_PATH;
const url='http://127.0.0.1:18549';
const local=spawn(executable,['--host','127.0.0.1','--port','18549','--chain-id','31337','--hardfork','shanghai','--accounts','2','--gas-limit','30000000','--silent'],{stdio:['ignore','ignore','pipe']});
let stderr='';local.stderr.on('data',b=>stderr+=b.toString());
let online=false;
for(let i=0;i<100;i++){
 if(local.exitCode!==null)throw new Error('Anvil exited: '+stderr);
 try{
  const response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:1,method:'eth_chainId',params:[]})});
  if((await response.json()).result==='0x7a69'){online=true;break;}
 }catch{}
 await new Promise(r=>setTimeout(r,100));
}
require(online,'Anvil startup failed');
const provider=new JsonRpcProvider(url,31337,{staticNetwork:true,cacheTimeout:-1});provider.pollingInterval=10;
try{
 const signer=await provider.getSigner();
 const report={scope:'Supplemental synthetic fixtures; standalone local verifier execution, not Enygma payment or live transport.',
   started_utc:new Date().toISOString(),contract_source_commit:'ed8863885c8ed5d5d317d47a34c063907192687a',
   native_proofs_sha256:sha(fs.readFileSync(proofPath)),solc_version:solc.version(),compiler_settings:input.settings,
   compiler_input_sha256:sha(Buffer.from(JSON.stringify(input,null,2)+'\n')),
   observed_client:await provider.send('web3_clientVersion',[]),observed_chain:await provider.send('eth_chainId',[]),
   deployments:[],verification_transactions:[],controls:[]};
 const contracts={};
 for(let k=2;k<=6;k++){
  const a=built.contracts[`EnygmaVerifierk${k}.sol`][`EnygmaVerifierk${k}`];
  const c=await new ContractFactory(a.abi,'0x'+a.evm.bytecode.object,signer).deploy();await c.waitForDeployment();contracts[k]=c;
  const receipt=await c.deploymentTransaction().wait();
  const code=await provider.getCode(await c.getAddress());
  require(code==='0x'+a.evm.deployedBytecode.object,'Observed runtime mismatch');
  report.deployments.push({k,address:await c.getAddress(),runtime_bytecode:code,runtime_sha256:sha(Buffer.from(code.slice(2),'hex')),raw_receipt:await provider.send('eth_getTransactionReceipt',[receipt.hash])});
 }
 const points=s=>Array.from({length:8},(_,i)=>BigInt('0x'+s.proof_hex.slice(2+64*i,2+64*(i+1))));
 const routeDefinitions=(proof,compressed)=>[
   {mode:'direct_uncompressed',fn:'verifyProofInternal',size:256,args:x=>[proof,x]},
   {mode:'compressed',fn:'verifyCompressedProof',size:128,args:x=>[compressed,x]},
   {mode:'legacy_uncompressed',fn:'verifyProof',size:256,bool:true,args:x=>[proof.slice(0,2),[proof.slice(2,4),proof.slice(4,6)],proof.slice(6,8),x]}
 ];
 function decodedError(c,e){
  for(const d of [e?.data,e?.info?.error?.data?.result,e?.info?.error?.data]){
   if(typeof d==='string'&&d.startsWith('0x')){try{return c.interface.parseError(d)?.name;}catch{}}
  }return null;
 }
 async function send(c,route,args,metadata){
  const data=c.interface.encodeFunctionData(route.fn,args);
  const tx=await signer.sendTransaction({to:await c.getAddress(),data,gasLimit:5000000n});
  let receipt;try{receipt=await tx.wait();}catch(e){receipt=e.receipt;if(!receipt)throw e;}
  const bytes=Buffer.from(data.slice(2),'hex'),zero=[...bytes].filter(x=>x===0).length;
  const intrinsic=21000+4*zero+16*(bytes.length-zero);
  return {...metadata,mode:route.mode,function:route.fn,status:receipt.status,gas_used:Number(receipt.gasUsed),
    transaction_hash:receipt.hash,calldata:data,calldata_bytes:bytes.length,zero_bytes:zero,nonzero_bytes:bytes.length-zero,
    intrinsic_gas:intrinsic,execution_gas:Number(receipt.gasUsed)-intrinsic,
    raw_receipt:await provider.send('eth_getTransactionReceipt',[receipt.hash]),
    raw_transaction:await provider.send('eth_getTransactionByHash',[receipt.hash])};
 }
 async function reject(c,route,signals,metadata){
  let answer,error=null;
  try{answer=await c[route.fn].staticCall(...route.args(signals));}catch(e){error=decodedError(c,e);}
  require(route.bool?answer===false:error==='ProofInvalid','Invalid proof acceptance/error: '+JSON.stringify(metadata));
  const row=await send(c,route,route.args(signals),{...metadata,proof_accepted:false,read_only_result:route.bool?'false':'reverted',decoded_error:error});
  require(row.status===(route.bool?1:0),'Control receipt mismatch');
  report.controls.push(row);
 }
 for(const sample of proofs.samples){
  const c=contracts[sample.k],proof=points(sample),signals=sample.public_signals.map(BigInt);
  const compressed=Array.from(await c.compressProof.staticCall(proof));
  const routes=routeDefinitions(proof,compressed);
  // Reverse alternate trials. Each measurement is a separate transaction.
  const ordered=sample.trial%2?[...routes].reverse():routes;
  for(const route of ordered){
   const answer=await c[route.fn].staticCall(...route.args(signals));
   require(!route.bool||answer===true,'Valid native proof rejected by wrapper');
   const row=await send(c,route,route.args(signals),{
    k:sample.k,case_id:sample.case_id,trial:sample.trial,proof_accepted:true,
    read_only_result:route.bool?'true':'returned without revert',proof_bytes:route.size,
    public_input_count:signals.length,compressed_words:compressed.map(String),route_order:ordered.map(x=>x.mode)
   });
   require(row.status===1,'Valid native proof transaction reverted');
   require(row.calldata_bytes===4+route.size+signals.length*32,'ABI calldata size mismatch');
   if(sample.trial===0&&route.mode!=='legacy_uncompressed'){
    row.raw_call_trace=await provider.send('debug_traceTransaction',[row.transaction_hash,{tracer:'callTracer'}]);
   }
   report.verification_transactions.push(row);
  }
  if(sample.trial===0){
   const altered=[...signals];altered[0]=(altered[0]+1n)%R;
   for(const route of routes)await reject(c,route,altered,{k:sample.k,case_id:sample.case_id,trial:0,control:'altered_public_input'});
  }
 }
 // A valid proof from a different circuit profile is not valid under this profile's key.
 for(let k=2;k<=6;k++){
  const own=proofs.samples.find(x=>x.k===k&&x.case_id==='moved_sender'&&x.trial===0);
  const other=proofs.samples.find(x=>x.k===(k===6?2:k+1)&&x.case_id==='moved_sender'&&x.trial===0);
  const c=contracts[k],proof=points(other),compressed=Array.from(await c.compressProof.staticCall(proof));
  for(const route of routeDefinitions(proof,compressed)){
   await reject(c,route,own.public_signals.map(BigInt),{k,case_id:'moved_sender',trial:0,control:'wrong_profile_proof',proof_from_k:other.k});
  }
 }
 require(report.verification_transactions.length===135,'Valid transaction coverage');
 require(report.controls.length===60,'Control coverage');
 fs.mkdirSync(path.dirname(output),{recursive:true});
 fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({accepted_verification_transactions:135,rejected_proof_controls:60,traced_transactions:report.verification_transactions.filter(x=>x.raw_call_trace).length},null,2));
}finally{
 await provider.destroy();
 local.kill('SIGTERM');
}
