/* Bundles the app into ONE self-contained HTML file (three.js stays on a CDN):  node tools/build.js  →  dist/image-to-cad.html */
const fs = require('fs'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8');
let html = rd('index.html');
const order = ['core/geo.js', 'core/units.js', 'core/csg.js', 'core/checks.js', 'core/spec.js', 'core/exporter.js', 'ai/vision.js', 'ui/guide.js', 'ui/app.js'];
const examples = {}; JSON.parse(rd('examples/index.json')).forEach(e => { examples[e.id] = JSON.parse(rd('examples/' + e.file)); });
const js = 'window.EXAMPLES=' + JSON.stringify(examples) + ';\n' + order.map(f => rd('src/' + f)).join('\n');
html = html.replace('<link rel="stylesheet" href="src/ui/style.css">', () => '<style>' + rd('src/ui/style.css') + '</style>');
html = html.replace(/<script src="src\/[^"]+"><\/script>\n?/g, '').replace('</body>', () => '<script>\n' + js.replace(/<\/script>/gi, '<\\/script>') + '\n</script>\n</body>');
fs.mkdirSync(path.join(root, 'dist'), { recursive: true }); fs.writeFileSync(path.join(root, 'dist/image-to-cad.html'), html); fs.writeFileSync(path.join(root, 'dist/index.html'), html);
console.log('wrote dist/image-to-cad.html', (html.length / 1024).toFixed(0) + ' KB,', Object.keys(examples).length + ' examples embedded');
