const fs=require('node:fs'),path=require('node:path');
const APP=process.env.COOPANION_APP_DIR || 'D:/pet/coo1/Coopanion/resources/app';
const esbuild=require(APP+'/node_modules/esbuild');
(async()=>{
 await esbuild.build({entryPoints:[APP+'/node_modules/cortico-world-desktop-pet/src/packs.ts'],bundle:true,platform:'node',format:'esm',outfile:__dirname+'/preview/native-parser.mjs',plugins:[{name:'local-cortico',setup(build){build.onResolve({filter:/^cortico\//},args=>({path:path.join(APP,'build/cortico/src',args.path.slice(8))}));}}]});
 const m=await import('./preview/native-parser.mjs'),skipped=[];
 const r=m.readManifest(__dirname+'/baie-native',false,skipped);
 if(typeof r==='string')throw new Error(r);
 const report={id:r.id,api:r.api,manifest:r.manifest,words:r.vocab.length,skipped};
 fs.writeFileSync(__dirname+'/preview/native-manifest-verification.json',JSON.stringify(report,null,2));
 console.log(report);
 if(skipped.length)process.exitCode=1;
 await esbuild.build({entryPoints:[APP+'/node_modules/cortico-world-desktop-pet/src/pack-import.ts'],bundle:true,platform:'node',format:'esm',outfile:__dirname+'/preview/native-importer.mjs',plugins:[{name:'local-cortico',setup(build){build.onResolve({filter:/^cortico\//},args=>({path:path.join(APP,'build/cortico/src',args.path.slice(8))}));}}]});
 const imp=await import('./preview/native-importer.mjs');
 const zip=fs.readdirSync(__dirname+'/dist').find(n=>n.endsWith('.zip'));
 const files=imp.filesFromZip(fs.readFileSync(path.join(__dirname,'dist',zip)));
 if(typeof files==='string')throw new Error(files);
 const importer=new imp.PackImporter({packDir:()=>__dirname+'/preview/isolated-install',packs:()=>[]});
 try{
   const staged=await importer.stage(files,false);
   if(staged.error||staged.problems.length||staged.packs.length!==1)throw new Error(JSON.stringify(staged));
   const summary={zip,files:files.length,pack:staged.packs[0].id,words:staged.packs[0].words,problems:staged.problems,skipped:staged.packs[0].skipped,installedIntoUserApp:false};
   fs.writeFileSync(__dirname+'/preview/native-zip-verification.json',JSON.stringify(summary,null,2));
   console.log('Native ZIP staging PASS:',summary.pack,summary.files,'files');
 }finally{await importer.cancel();}
})();
