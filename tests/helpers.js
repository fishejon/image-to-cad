const fs = require('fs'), vm = require('vm'), path = require('path');
const root = path.join(__dirname, '..');
global.THREE = require('three'); global.window = global;
for (const f of ['src/core/geo.js', 'src/core/units.js', 'src/core/csg.js', 'src/core/checks.js', 'src/core/spec.js', 'src/core/exporter.js']) vm.runInThisContext(fs.readFileSync(path.join(root, f), 'utf8'), { filename: f });
module.exports = { CAD: global.CAD, THREE, root, load: n => JSON.parse(fs.readFileSync(path.join(root, 'examples', n + '.json'), 'utf8')), examples: () => fs.readdirSync(path.join(root, 'examples')).filter(f => f.endsWith('.json') && f !== 'index.json').map(f => f.replace('.json', '')) };
