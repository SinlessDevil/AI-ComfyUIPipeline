const fs=require('fs'),path=require('path'),{build}=require('./workflows.cjs');
const root=path.resolve(__dirname,'..'),run=path.resolve(process.argv[2]);
const read=f=>JSON.parse(fs.readFileSync(f,'utf8').replace(/^\uFEFF/,''));
const m=read(path.join(run,'run.json')),settings=read(path.join(run,'settings.snapshot.json'));
const templates=new Map();
for(const file of ['GameArt_UI_Asset_Extract.json','GameArt_Retouch_Final.json','GameArt_Text_Final.json']){const w=read(path.join(process.env.COMFY_PIPELINE_ROOT||path.resolve(root,'../..'),'Workflows/GameArt',file));for(const n of w.nodes)if(!templates.has(n.type))templates.set(n.type,n);}
function ui(api,title){
 const nodes=[],links=[],outputs=new Map(),ranks=new Map();let linkId=0;
 function rank(id){if(ranks.has(id))return ranks.get(id);let r=0;for(const value of Object.values(api[id].inputs))if(Array.isArray(value))r=Math.max(r,rank(String(value[0]))+1);ranks.set(id,r);return r;}
 const columnY=new Map();
 for(const [id,a] of Object.entries(api)){
  const template=templates.get(a.class_type);if(!template)throw Error('UI node template missing '+a.class_type);
  const n=structuredClone(template);n.id=+id;n.title=a._meta.title;n.mode=0;n.flags={};n.order=nodes.length;
  const r=rank(id),y=columnY.get(r)||0;n.pos=[r*430,y];n.size=[370,Math.max(125,template.size?.[1]||150)];columnY.set(r,y+n.size[1]+65);
  for(const input of n.inputs||[])input.link=null;for(const output of n.outputs||[])output.links=[];
  const widgetNames=n.widgets_values_named?Object.keys(n.widgets_values_named):(n.inputs||[]).filter(i=>i.widget).map(i=>i.name);
  for(let i=0;i<widgetNames.length;i++){const key=widgetNames[i];if(Object.prototype.hasOwnProperty.call(a.inputs,key)&&!Array.isArray(a.inputs[key])){if(n.widgets_values&&i<n.widgets_values.length)n.widgets_values[i]=a.inputs[key];if(n.widgets_values_named)n.widgets_values_named[key]=a.inputs[key];}}
  n.properties={...(n.properties||{}),'Node name for S&R':a.class_type};nodes.push(n);outputs.set(id,n);
 }
 for(const [id,a] of Object.entries(api))if(a.class_type==='ComfySwitchNode'){
  const edge=a.inputs.on_true||a.inputs.on_false,kind=outputs.get(String(edge[0])).outputs[edge[1]].type,n=outputs.get(id);
  n.outputs[0].type=kind;for(const input of n.inputs)if(input.name==='on_true'||input.name==='on_false')input.type=kind;
 }
 for(const [id,a] of Object.entries(api))for(const [name,value] of Object.entries(a.inputs))if(Array.isArray(value)){
  const n=outputs.get(id),from=outputs.get(String(value[0])),slot=(n.inputs||[]).findIndex(i=>i.name===name);
  if(slot<0)throw Error('UI input slot missing '+a.class_type+'.'+name);
  const output=from.outputs[value[1]];if(!output)throw Error('Output slot missing '+value);
  const type=output.type==='COMFY_MATCHTYPE_V3'?n.inputs[slot].type:output.type;
  const link=[++linkId,+value[0],value[1],+id,slot,type];links.push(link);n.inputs[slot].link=linkId;output.links.push(linkId);
 }
 return {last_node_id:Math.max(...nodes.map(n=>n.id)),last_link_id:linkId,nodes,links,groups:[],config:{},extra:{ds:{scale:.55,offset:[30,30]},pipeline:'Unity UI Assets',title},version:.4};
}
fs.mkdirSync(path.join(root,'workflows/API'),{recursive:true});fs.mkdirSync(path.join(root,'workflows/UI'),{recursive:true});
const names={extract:'01_Extract_Source',repair:'02_Repair_Masked',rebuild:'03_Rebuild_Object'};
for(const route of Object.keys(names)){
 const a=m.assets.find(a=>a.route===route),inputs={source:path.basename(a.input),contour:path.basename(a.contour),edit:path.basename(a.edit_mask),blend:path.basename(a.blend_mask)};
 const api=build(route,a,settings,inputs,'UIAssets/Manual/'+a.id);
 fs.writeFileSync(path.join(root,'workflows/API',names[route]+'_API.json'),JSON.stringify(api,null,2));
 fs.writeFileSync(path.join(root,'workflows/UI',names[route]+'.json'),JSON.stringify(ui(api,names[route]),null,2));
}
console.log('Three compact API/UI routes created from existing node definitions');
