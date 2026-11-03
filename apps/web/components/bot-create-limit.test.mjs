import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import test from "node:test";
const source=readFileSync(new URL("./bot-create-dialog.tsx",import.meta.url),"utf8");
const effect=source.slice(source.indexOf("  useEffect(() => {"),source.indexOf("  const nluModelOptions"));
function subject({policy={limit:1,used:0,remaining:1,allowed:true,reason:"available"},fail=false,session=true}={}){
 const state={allowed:false,policy:null,error:"",navigation:[]};let cleanup;let resolve,reject;
 const result=new Promise((a,b)=>{resolve=a;reject=b;});
 const bindings={useEffect:fn=>{cleanup=fn();},loadAuthSession:()=>session?{access_token:"synthetic-token"}:null,fetchStudioBotCreationPolicy:()=>result,router:{replace:url=>state.navigation.push(url)},copy:{loginRequired:"login",createError:"failed"},setCreationAllowed:value=>state.allowed=value,setCreationPolicy:value=>state.policy=value,setErrorMessage:value=>state.error=value};
 new Function(...Object.keys(bindings),effect)(...Object.values(bindings));
 return {state,cleanup:()=>cleanup?.(),settle:async()=>{fail?reject(new Error("lookup failed")):resolve(policy);await new Promise(setImmediate);}};
}
test("quota one keeps original creation form and blocks full quota",async()=>{const s=subject({policy:{limit:1,used:1,remaining:0,allowed:false,reason:"quota_reached"}});await s.settle();assert.deepEqual(s.state.navigation,[]);assert.equal(s.state.policy.used,1);assert.equal(s.state.allowed,false);});
test("quota two enables another bot despite existing ownership",async()=>{const s=subject({policy:{limit:2,used:1,remaining:1,allowed:true,reason:"available"}});await s.settle();assert.equal(s.state.allowed,true);assert.equal(s.state.policy.limit,2);});
test("zero expired or invalid quota never enables creation",async()=>{for(const reason of ["quota_reached","license_expired","bot_limit_invalid"]){const s=subject({policy:{limit:0,used:0,remaining:0,allowed:false,reason}});await s.settle();assert.equal(s.state.allowed,false);}});
test("policy lookup failure remains blocked",async()=>{const s=subject({fail:true});await s.settle();assert.equal(s.state.allowed,false);assert.equal(s.state.error,"lookup failed");});
test("disposed policy cannot change state",async()=>{const s=subject();s.cleanup();await s.settle();assert.equal(s.state.allowed,false);assert.equal(s.state.policy,null);});
test("license notice and submit guard stay wired without a hardcoded bot count",()=>{assert.ok(source.includes('copy.botLicenseUsage'));assert.ok(source.includes('role="status"'));assert.ok(source.includes('if (!creationAllowed) return;'));assert.ok(source.includes('disabled={isSubmitting || !creationAllowed}'));assert.ok(!source.includes('bots.length > 0'));});
