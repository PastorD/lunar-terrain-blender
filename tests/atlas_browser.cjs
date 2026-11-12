/* npm install playwright@1.62.1; node tests/atlas_browser.cjs [--local-previews] */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
let pw;try{pw=require('playwright');}catch{pw=require(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES+'/playwright');}
const root=path.resolve(__dirname,'..'),out=path.join(root,'build/atlas'),local=process.argv.includes('--local-previews');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await pw.chromium.launch({...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 if(local)await page.route('**/releases/download/v1.6.0/*.png',route=>{const name=new URL(route.request().url()).pathname.split('/').pop(),file=path.join(root,name==='Polar_Context.png'?'build/atlas':'examples/renders',name);return fs.existsSync(file)?route.fulfill({path:file,contentType:'image/png'}):route.continue();});
 await page.goto('file://'+path.join(root,'docs/index.html'),{waitUntil:'domcontentloaded'});assert.equal(await page.evaluate(()=>lunarAtlas.selected),'viper');
 const projections=await page.evaluate(()=>{const f=lunarAtlas.project;return{centre:f({lat:-90,lon:0},'polar'),north:f({lat:-80,lon:0},'polar'),east:f({lat:-80,lon:90},'polar'),origin:f({lat:0,lon:0},'global')};});
 for(const [k,expected]of Object.entries({centre:[300,300],north:[300,55],east:[545,300],origin:[500,250]}))projections[k].forEach((v,i)=>assert.ok(Math.abs(v-expected[i])<1e-8));
 const sites=await page.evaluate(()=>lunarAtlas.sites),rows=[];
 for(const s of sites){
  await page.locator(`#site-list button[data-site="${s.id}"]`).click();assert.equal(await page.locator('#site-name').textContent(),s.name);
  await page.waitForFunction(()=>['photo','render'].every(id=>document.getElementById(id).complete),null,{timeout:60000});
  const images=await page.evaluate(()=>Object.fromEntries(['photo','render'].map(id=>{const i=document.getElementById(id);return[id,{width:i.naturalWidth,height:i.naturalHeight,url:i.currentSrc}]})));
  assert.ok(images.photo.width>100,JSON.stringify({site:s.id,failed:images.photo}));assert.ok(images.render.width>100,JSON.stringify({site:s.id,failed:images.render}));
  const download=page.waitForEvent('download');await page.locator('#download-preset').click();const d=await download,payload=JSON.parse(fs.readFileSync(await d.path(),'utf8'));
  assert.equal(payload.schema,'lunar-terrain-location-v1');assert.equal(payload.preset,s.preset);rows.push({site:s.id,images,location_download:true});
 }
 await page.locator('#polar-toggle').click();await page.locator('#map [data-site="viper"]').click();assert.equal(await page.evaluate(()=>lunarAtlas.selected),'viper');
 await page.locator('#map [data-site="malapert"]').focus();await page.keyboard.press('Enter');assert.equal(await page.evaluate(()=>lunarAtlas.selected),'malapert');
 await page.locator('#map [data-site="nobile2"]').focus();await page.keyboard.press('Space');assert.equal(await page.evaluate(()=>lunarAtlas.selected),'nobile2');
 await page.waitForFunction(()=>['photo','render'].every(id=>document.getElementById(id).complete));await page.screenshot({path:path.join(out,'Atlas_Desktop.png'),fullPage:true});
 await page.locator('#global-toggle').click();await page.locator('#map [data-site="apollo17"]').click();assert.equal(await page.evaluate(()=>lunarAtlas.selected),'apollo17');
 await page.waitForFunction(()=>['photo','render'].every(id=>document.getElementById(id).complete));await page.screenshot({path:path.join(out,'Atlas_Global.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.locator('#site-list button[data-site="chandrayaan3"]').click();
 await page.waitForFunction(()=>['photo','render'].every(id=>document.getElementById(id).complete));assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,'Atlas_Mobile.png'),fullPage:true});
 assert.deepEqual(errors,[]);await page.reload({waitUntil:'domcontentloaded'});assert.equal(await page.evaluate(()=>lunarAtlas.selected),'chandrayaan3');
 const result={passed:true,browser:await browser.version(),checked:new Date().toISOString(),local_preview_routes:local,locations:rows,projection_checks:projections,keyboard_map_selection:true,mobile_no_overflow:true,hash_reload:true};
 fs.writeFileSync(path.join(out,'Atlas_Browser_validation.json'),JSON.stringify(result,null,2)+'\n');console.log('ATLAS BROWSER PASS',rows.length,'photo/render pairs, maps, keyboard, JSON downloads, mobile');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
