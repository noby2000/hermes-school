import fs from "fs";
const env=Object.fromEntries(fs.readFileSync(process.env.HOME+"/.openclaw/.env","utf8").split("\n").filter(l=>l.includes("=")).map(l=>[l.slice(0,l.indexOf("=")),l.slice(l.indexOf("=")+1)]));
const H={"Authorization":"Bearer "+env.OMNIROUTE_API_KEY,"content-type":"application/json"};
const tools=[{type:"function",function:{name:"get_weather",description:"Get weather for a city",parameters:{type:"object",properties:{city:{type:"string"}},required:["city"]}}}];
async function call(model,withTools){const t=Date.now();
 const body={model,messages:[{role:"user",content:withTools?"What is the weather in Paris? Use the tool.":"Reply with the single word: ok"}],max_tokens:400};
 if(withTools){body.tools=tools;body.tool_choice="auto";}
 try{const r=await fetch("http://127.0.0.1:20128/v1/chat/completions",{method:"POST",headers:H,body:JSON.stringify(body),signal:AbortSignal.timeout(90000)});
 const j=await r.json().catch(()=>({}));const m=j.choices?.[0]?.message||{};
 const out=withTools?(m.tool_calls?.[0]?.function?JSON.stringify(m.tool_calls[0].function).slice(0,80):"NO_TOOL "+(m.content||"").slice(0,40)):(m.content||"").trim().slice(0,30);
 console.log(model.padEnd(42),r.status,((Date.now()-t)/1000).toFixed(1)+"s",j.model||"",out||JSON.stringify(j.error||j).slice(0,140));}catch(e){console.log(model,"ERR",e.message)}}
const models=process.argv.slice(2);
for(const m of models){ if(m.startsWith("T:")) await call(m.slice(2),true); else await call(m,false); }
