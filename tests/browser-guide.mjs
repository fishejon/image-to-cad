import chromium from '@sparticuz/chromium'; import puppeteer from 'puppeteer-core'; import fs from 'fs'; import path from 'path';
import { fileURLToPath } from 'url'; const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const browser = await puppeteer.launch({ executablePath: await chromium.executablePath(), args: [...chromium.args, '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox'], headless: 'shell', defaultViewport: { width: 1500, height: 900 } });
const page = await browser.newPage(), errs=[]; page.on('pageerror', e => errs.push(e.message)); page.on('console',m=>{if(m.type()==='error'&&!/Failed to load/.test(m.text()))errs.push(m.text())});
await page.setRequestInterception(true); const nm=root+'/node_modules/three';
page.on('request', r => { const u=r.url(); if(u.includes('three.min.js')) return r.respond({status:200,contentType:'application/javascript',body:fs.readFileSync(nm+'/build/three.min.js')}); if(u.includes('OrbitControls.js')) return r.respond({status:200,contentType:'application/javascript',body:fs.readFileSync(nm+'/examples/js/controls/OrbitControls.js')}); if(u.startsWith('file:')) return r.continue(); r.abort(); });
await page.goto('file://'+root+'/dist/image-to-cad.html'); await page.waitForFunction(()=>window.__cad&&document.getElementById('loading').style.display==='none',{timeout:120000});
for (const [id,pgs] of [['bookshelf',[1,3,6,9]],['stool',[3,4]]]) {
  await page.evaluate(id=>__cad.loadExample(id),id); await new Promise(r=>setTimeout(r,800));
  const n=await page.evaluate(async()=>{ await window.__guide.generate(()=>{}); document.getElementById('guide').style.display='flex'; return window.__guide.pages().length; });
  const titles=await page.evaluate(()=>window.__guide.steps().map(s=>s.n+'. '+s.kind+' · '+s.title.replace(/&amp;/g,'&')));
  console.log(id,'pages',n); console.log(titles.join('\n'));
  for(const i of pgs){ if(i>=n) continue; await page.evaluate(i=>window.__guide.show(i),i); await new Promise(r=>setTimeout(r,350)); await page.screenshot({path:`${root}/tests/out/guide_${id}_${i+1}.png`}); }
}
console.log('errors',errs); await browser.close();
