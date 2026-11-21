const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {build}=require('./workflows.cjs');
const root=path.resolve(__dirname,'..'),command=process.argv[2];
const args={};for(let i=3;i<process.argv.length;i+=2)args[process.argv[i].replace(/^--/,'')]=process.argv[i+1];
const read=f=>JSON.parse(fs.readFileSync(f,'utf8').replace(/^\uFEFF/,''));
const write=(f,v)=>{fs.mkdirSync(path.dirname(f),{recursive:true});fs.writeFileSync(f,typeof v==='string'?v:JSON.stringify(v,null,2)+'\n');};
const hash=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
if(command==='prepare'){
 const projectPath=path.resolve(args.project),p=read(projectPath),settings=read(path.join(root,'config/pipeline.json')),out=path.resolve(args.out);
 if(fs.existsSync(out))throw Error('Run folder already exists; use a new attempt folder.');
 if(!/^[a-z0-9_]+$/.test(p.project_id))throw Error('Use a stable project_id with lowercase letters, digits and underscores.');
 const source=path.resolve(path.dirname(projectPath),p.source),stamp=Date.now().toString(36),run={schema_version:1,project_id:p.project_id,purpose:p.purpose||'',source:'Reference/original.png',source_sha256:hash(source),source_path:source,assembly_mode:'PARTIAL_CALIBRATION_ONLY',assets:[],fidelity_target:settings.fidelity.target,percentage_metric_defined:false,editor_tested:false};
 fs.mkdirSync(out,{recursive:true});fs.mkdirSync(path.join(out,'Reference'),{recursive:true});fs.copyFileSync(source,path.join(out,run.source));
 write(path.join(out,'project.snapshot.json'),p);write(path.join(out,'settings.snapshot.json'),settings);
 const seen=new Set();
 for(const asset of p.assets){
  if(!/^[a-z0-9_]+$/.test(asset.id)||seen.has(asset.id))throw Error('Asset ID invalid or duplicate '+asset.id);seen.add(asset.id);
  if(!['extract','repair','rebuild'].includes(asset.route))throw Error('Unknown route '+asset.route);
  if(asset.alpha_source==='contour'&&!asset.outline)throw Error('Contour source needs an outline '+asset.id);
  if(asset.route==='repair'&&(!asset.repair||!asset.prompt))throw Error('Repair needs a region and a prompt '+asset.id);
  if(asset.route==='rebuild'&&!asset.prompt)throw Error('Rebuild needs a prompt '+asset.id);
  const prefix='UIAssets_'+p.project_id+'_'+asset.id+'_'+stamp;
  const names={source:prefix+'_source.png',contour:prefix+'_contour.png',edit:prefix+'_edit.png',blend:prefix+'_blend.png'};
  const a={...asset,padding:asset.padding??settings.defaults.padding,feather_px:asset.feather_px??settings.defaults.feather_px,outline:asset.outline||'',repair:asset.repair||'',alpha_source:asset.alpha_source||'contour',include_in_layout:asset.include_in_layout??asset.route!=='rebuild',input:'Inputs/'+names.source,contour:'Inputs/'+names.contour,edit_mask:'Inputs/'+names.edit,blend_mask:'Inputs/'+names.blend,workflow:'Workflows/'+asset.id+'.API.json',unity_png:'Unity/'+asset.id+'.png',technical_status:'PENDING',fidelity_status:'REVIEW',status:'PENDING',issues:['No candidate exported or reviewed yet']};
  write(path.join(out,a.workflow),build(asset.route,a,settings,names,'UIAssets/'+p.project_id+'/'+stamp+'/'+asset.id));run.assets.push(a);
 }
 write(path.join(out,'run.json'),run);write(path.join(out,'candidates.json'),{});write(path.join(out,'reviews.json'),{});
 write(path.join(out,'jobs.json'),run.assets.map(a=>({id:a.id,route:a.route,workflow:path.join(out,a.workflow),input_files:[a.input,a.contour,a.edit_mask,a.blend_mask].map(f=>path.join(out,f)),status:'PREPARED'})));
 console.log(JSON.stringify({run:out,jobs:run.assets.length,source_sha256:run.source_sha256}));
}else if(command==='review'){
 const out=path.resolve(args.run),m=read(path.join(out,'run.json')),a=m.assets.find(a=>a.id===args.asset);
 if(!a||!['PASS','REVIEW'].includes(args.decision)||!args.note)throw Error('Review needs an asset, PASS/REVIEW decision and a concrete note.');
 if(!fs.existsSync(path.join(out,a.unity_png)))throw Error('Review an actual exported PNG.');
 const r=read(path.join(out,'reviews.json'));r[a.id]={decision:args.decision,note:args.note,reviewer:args.reviewer||'agent',result_sha256:hash(path.join(out,a.unity_png))};write(path.join(out,'reviews.json'),r);console.log(JSON.stringify(r[a.id]));
}else if(command==='report'){
 const out=path.resolve(args.run),m=read(path.join(out,'run.json')),r=read(path.join(out,'reviews.json')),checks=fs.existsSync(path.join(out,'Checks.json'))?read(path.join(out,'Checks.json')):[];
 if(hash(path.join(out,m.source))!==m.source_sha256)throw Error('Immutable source changed.');
 const checkList=Array.isArray(checks)?checks:[checks];
 for(const a of m.assets){
  const c=checkList.find(c=>c.id===a.id);if(!c){a.technical_status='PENDING';a.fidelity_status='REVIEW';a.status='PENDING';continue;}
  a.checks=c;a.sha256=hash(path.join(out,a.unity_png));a.technical_status=c.foreground_pixels>0&&c.protected_changed_pixels===0&&c.candidate_contour_disagreement_pixels===0?'PASS':'FAIL';
  const review=r[a.id];a.fidelity_status=review&&review.result_sha256===a.sha256?review.decision:'REVIEW';a.visual_review=review&&review.result_sha256===a.sha256?review:null;
  a.status=a.technical_status==='PASS'&&a.fidelity_status==='PASS'?'READY':'REVIEW';a.issues=[];
  if(a.technical_status!=='PASS')a.issues.push('Technical source-preservation or alpha check failed.');
  if(a.fidelity_status!=='PASS')a.issues.push(a.visual_review?.note||(review?'Export changed since the recorded review; inspect the current PNG.':'Visual fidelity has not been accepted.'));
 }
 write(path.join(out,'run.json'),m);write(path.join(out,'manifest.json'),m);
 const count={assets:m.assets.length,ready:m.assets.filter(a=>a.status==='READY').length,review:m.assets.filter(a=>a.status==='REVIEW').length,pending:m.assets.filter(a=>a.status==='PENDING').length,percentage_similarity_measured:false,assembly_mode:m.assembly_mode};write(path.join(out,'Counts.json'),count);
 const panel=(file,label)=>`<figure><a href="${esc(file)}"><img loading="lazy" src="${esc(file)}" alt="${esc(label)}"></a><figcaption>${esc(label)}</figcaption></figure>`;
 let h=`<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Unity UI Assets · проверка</title><style>:root{color-scheme:dark;font:16px/1.5 system-ui;background:#19212b;color:#eaf1f8}body{max-width:1500px;margin:auto;padding:26px}a{color:#a9dcff}figure{margin:0;min-width:0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}img{width:100%;max-height:600px;object-fit:contain;background:repeating-conic-gradient(#273340 0 25%,#354352 0 50%) 0/24px 24px}article{border:1px solid #607486;border-radius:10px;padding:16px;margin-top:20px}.review{color:#ffc66d}.ready{color:#a6e29d}figcaption{padding:7px}.notice{background:#3a3025;padding:14px;border-left:4px solid #ffc66d}button{padding:8px;margin:4px;cursor:pointer}@media(max-width:850px){.pair{grid-template-columns:1fr}}</style><h1>Unity UI Assets · контрольный прогон</h1><p class="notice">Это проверка отдельных классов объектов, не полностью разобранный UI. Сходство в процентах не измерялось. Технический успех не присваивает READY автоматически.</p><p>READY: ${count.ready} · REVIEW: ${count.review} · PENDING: ${count.pending}</p><p><a href="run.json">Конфиг и проверки</a> · <a href="QA.md">QA</a></p>`;
 if(fs.existsSync(path.join(out,'Preview/Parts-Only.png')))h+=`<h2>Комплектность пилота</h2><div class="pair">${panel('Preview/Parts-Only.png','Только подготовленные части; пустое место не скрывается')}${panel('Preview/Partial-Overlay.png','Частичное наложение на исходник; не полная пересборка UI')}</div>`;
 for(const a of m.assets){h+=`<article><h2>${esc(a.id)} · ${esc(a.route)}</h2><p class="${a.status==='READY'?'ready':'review'}">${a.status} · technical ${a.technical_status} · fidelity ${a.fidelity_status}</p><div class="pair">${panel(a.input,'Исходный фрагмент')}${fs.existsSync(path.join(out,a.unity_png))?panel(a.unity_png,'Экспорт для проверки'):'<p>Экспорт ожидается</p>'}</div><p>${esc(a.issues.join(' '))}</p>${a.visual_review?'<p>'+esc(a.visual_review.note)+'</p>':''}<ul>${(a.review_criteria||[]).map(s=>'<li>'+esc(s)+'</li>').join('')}</ul>${a.checks?'<p>Сохранённых пикселей: '+a.checks.protected_pixels+'; изменённых вне ремонта: '+a.checks.protected_changed_pixels+'</p>':''}</article>`;}
 h+='<h2>Края на трёх фонах</h2><p>Светлый, тёмный и контрастный фон. Крупные объекты в этой полосе уменьшены до 640 px; оригинальный PNG доступен выше.</p>';
 for(const a of m.assets){const plate='Preview/'+a.id+'-Mattes.png';if(fs.existsSync(path.join(out,plate)))h+=panel(plate,a.id+' · проверка альфы');}
 h+='<h2>Неизменённый исходник</h2>'+panel(m.source,'Оригинальный макет');
 h+='</html>';write(path.join(out,'Gallery.html'),h);
 const missing=[];for(const x of h.matchAll(/(?:src|href)="([^"]+)"/g)){if(x[1]==='QA.md')continue;if(!fs.existsSync(path.join(out,x[1])))missing.push(x[1]);}if(missing.length)throw Error('Broken gallery links '+JSON.stringify(missing));
 write(path.join(out,'QA.md'),`# Проверка контрольного прогона\n\n${JSON.stringify(count,null,2)}\n\nТехнические проверки: непустая альфа, сохранение исходных пикселей вне ремонта, согласованная маска извлечения. READY требует отдельной записи визуального решения, привязанной к SHA256 экспортированного PNG.\n\n${m.assets.map(a=>'- '+a.id+': '+a.status+'. '+a.issues.join(' ')).join('\n')}\n\nПроцент художественного сходства не вычислялся. Превью частичное: это не полный UI-пак. Unity Editor не запускался.\n`);
 console.log(JSON.stringify(count));
}else throw Error('Commands: prepare --project FILE --out DIR; report --run DIR; review --run DIR --asset ID --decision PASS|REVIEW --note TEXT');
