function build(route,asset,settings,names,prefix){
 const model=settings.models,d=settings.defaults,w={};
 const node=(id,type,inputs,title)=>w[id]={class_type:type,inputs,_meta:{title}};
 if(route==='extract'){
  node('1','LoadImage',{image:names.source},'Original prepared crop');
  node('2','LoadImage',{image:names.contour},'Contour: opaque object, transparent outside');
  node('3','LoadBackgroundRemovalModel',{bg_removal_name:model.background_removal},'Automatic foreground mask');
  node('4','RemoveBackground',{bg_removal_model:['3',0],image:['1',0]},'Estimate foreground from original RGB');
  node('5','InvertMask',{mask:['4',0]},'Convert to Comfy transparency mask');
  node('6','ComfySwitchNode',{switch:asset.alpha_source==='contour',on_false:['5',0],on_true:['2',1]},'Use traced contour / otherwise automatic');
  node('7','GameArtCutoutFinish',{image:['1',0],alpha:['6',0],mode:asset.finish_mode||d.finish_mode,blackpoint:.01,whitepoint:.99,max_iterations:1000,outer_margin:2,edge_width:1,min_component_fraction:0},'Refine mask; original RGB retained');
  node('8','JoinImageWithAlpha',{image:['7',0],alpha:['7',1]},'Original pixels + selected alpha');
  node('9','SaveImage',{images:['8',0],filename_prefix:prefix+'/candidate'},'Candidate; requires visual review');
  return w;
 }
 node('1','UNETLoader',{unet_name:model.diffusion,weight_dtype:'default'},'Existing local editing model');
 node('2','CLIPLoader',{clip_name:model.encoder,type:'flux2',device:'default'},'Compatible encoder');
 node('3','VAELoader',{vae_name:model.vae},'Compatible VAE');
 node('4','CLIPTextEncode',{text:asset.prompt,clip:['2',0]},'Asset-specific edit; no blanket material preset');
 node('16','LoadImage',{image:names.source},'Immutable original crop');
 node('21','ImageScaleToTotalPixels',{image:['16',0],upscale_method:'lanczos',megapixels:asset.reference_megapixels||d.reference_megapixels,resolution_steps:32},'Model reference size; export stays native');
 node('17','VAEEncode',{pixels:['21',0],vae:['3',0]},'Encode reference');
 node('18','ReferenceLatent',{conditioning:['4',0],latent:['17',0]},'Reference-conditioned generation');
 node('9','RandomNoise',{noise_seed:asset.seed||202611200},'Recorded seed');
 node('10','KSamplerSelect',{sampler_name:'euler'},'Model sampler');
 node('11','BasicGuider',{model:['1',0],conditioning:['18',0]},'Reference guidance');
 if(route==='repair'){
  node('20','LoadImage',{image:names.edit},'Edit mask: TRANSPARENT means editable');
  node('22','GetImageSize',{image:['21',0]},'Model canvas');
  node('23','SetLatentNoiseMask',{samples:['17',0],mask:['20',1]},'Noise only in the intended region');
  node('8','Flux2Scheduler',{steps:asset.steps||d.steps,width:['22',0],height:['22',1]},'Distilled sampling schedule');
  node('12','SamplerCustomAdvanced',{noise:['9',0],guider:['11',0],sampler:['10',0],sigmas:['8',0],latent_image:['23',0]},'Masked local reconstruction');
  node('13','VAEDecode',{samples:['12',0],vae:['3',0]},'Raw edited RGB');
  node('24','LoadImage',{image:names.blend},'Prepared native-size feathered edit mask');
  node('28','ImageCompositeMasked',{destination:['16',0],source:['13',0],x:0,y:0,resize_source:true,mask:['24',1]},'Restore original outside local repair');
  node('25','LoadImage',{image:names.contour},'Native export silhouette');
  node('29','JoinImageWithAlpha',{image:['28',0],alpha:['25',1]},'Local composite + traced contour');
  node('15','SaveImage',{images:['29',0],filename_prefix:prefix+'/candidate'},'Native composite; visual review still required');
  node('30','SaveImage',{images:['13',0],filename_prefix:prefix+'/raw_edit'},'Diagnostic model output');
 }else if(route==='rebuild'){
  const nativeW=asset.crop[2]-asset.crop[0],nativeH=asset.crop[3]-asset.crop[1],scale=Math.min(1,Math.sqrt((asset.generation_megapixels||d.generation_megapixels)*1000000/(nativeW*nativeH)));
  const ww=Math.max(16,Math.round(nativeW*scale/16)*16),hh=Math.max(16,Math.round(nativeH*scale/16)*16);
  node('7','EmptyFlux2LatentImage',{width:ww,height:hh,batch_size:1},'Whole-object candidate canvas');
  node('8','Flux2Scheduler',{steps:asset.steps||d.steps,width:ww,height:hh},'Distilled sampling schedule');
  node('12','SamplerCustomAdvanced',{noise:['9',0],guider:['11',0],sampler:['10',0],sigmas:['8',0],latent_image:['7',0]},'Reconstruct coherent hidden structure');
  node('13','VAEDecode',{samples:['12',0],vae:['3',0]},'New object RGB');
  node('34','LoadBackgroundRemovalModel',{bg_removal_name:model.background_removal},'Foreground model');
  node('35','RemoveBackground',{bg_removal_model:['34',0],image:['13',0]},'Estimate generated object foreground');
  node('36','InvertMask',{mask:['35',0]},'Comfy transparency mask');
  node('37','GameArtCutoutFinish',{image:['13',0],alpha:['36',0],mode:'alpha_only',blackpoint:.01,whitepoint:.99,max_iterations:1000,outer_margin:2,edge_width:1,min_component_fraction:0},'Alpha refinement; inspect dark rim and holes');
  node('38','JoinImageWithAlpha',{image:['37',0],alpha:['37',1]},'Generated whole-object candidate');
  node('15','SaveImage',{images:['38',0],filename_prefix:prefix+'/candidate'},'Candidate; never automatic READY');
  node('42','SaveImage',{images:['13',0],filename_prefix:prefix+'/raw_rgb'},'Diagnostic pre-cutout RGB');
 }else throw Error('Unknown route '+route);
 return w;
}
module.exports={build};
