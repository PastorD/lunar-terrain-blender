const fs=require('fs'),path=require('path'),vm=require('vm');
const root=path.resolve(__dirname,'..');const file=path.join(root,'lunar_terrain/data/Lunar_DEM_Map.html');
const html=fs.readFileSync(file,'utf8');const data=html.match(/<script type="application\/json" id="catalog">([\s\S]*?)<\/script>/)[1];
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const elements={};const stub=()=>({value:'0',textContent:'',addEventListener(){},replaceChildren(){},append(){}});
const document={getElementById(id){return elements[id]||(elements[id]=stub());},createElement:stub};
document.getElementById('catalog').textContent=data;document.getElementById('lat').value='20.1908';document.getElementById('lon').value='30.7717';
const ctx=vm.createContext({document});vm.runInContext(script,ctx);
const rows=[];for(const [lat,lon,grid] of [[20.1908,30.7717,2],[-41.6385,206.0148,4],[-89.438788,222.844980,2],[18.5623,61.8103,3],[-69.373,32.319,3]]){const v=ctx.lookup(lat,lon)[0];if(Math.abs(v.posting_m-grid)>1e-8)throw Error('Incorrect map lookup');rows.push({lat,lon,grid_m:v.posting_m,source:v.id});}
const photos=fs.readFileSync(path.join(root,'lunar_terrain/data/Chandrayaan3_References.html'),'utf8');if((photos.match(/<article class="card">/g)||[]).length!==13)throw Error('Incorrect photo card count');if(!photos.includes('2603.26802'))throw Error('Missing additional 2026 views');
const result={passed:true,scope:'Node VM executes the actual offline map script with a minimal DOM; not a browser rendering test',map_queries:rows,photo_cards:13,additional_2026_paper:true};fs.writeFileSync(path.join(root,'tests/map_lookup_results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
