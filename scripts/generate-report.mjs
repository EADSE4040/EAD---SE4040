import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ignored = new Set(['.git','.tools','node_modules','bin','obj','build','dist','.gradle','artifacts','tmp','output','.codex','.agents']);
async function filesIn(directory) {
  const result = [];
  for (const item of await fs.readdir(directory, { withFileTypes:true })) {
    if (ignored.has(item.name)) continue;
    const filename = path.join(directory,item.name);
    if (item.isDirectory()) result.push(...await filesIn(filename)); else result.push(filename);
  }
  return result;
}
// Expand the same reviewed report manuscript used by the PDF generator.
let report = '# SOLARA - Technical Project Report\n\nSE4040 | September 2026\n\n';
report += await fs.readFile(path.join(repo,'docs/report.md'),'utf8');
report = report.replaceAll(/\[diagram:([^\]]+)\]/g, (_, name) => `![${name}](docs/diagrams/${name}.svg)`);
report = report.replace('[verification]', await fs.readFile(path.join(repo,'docs/report-verification.md'),'utf8'));
report = report.replace('[contributions]', await fs.readFile(path.join(repo,'docs/contributions.md'),'utf8'));
let screenshots = '';
for (const filename of (await fs.readdir(path.join(repo,'docs/screenshots'))).filter(x=>x.endsWith('.png')).sort()) {
  screenshots += `### ${filename.replace('.png','').replaceAll('-',' ')}\n\n![${filename}](docs/screenshots/${filename})\n\n`;
}
report = report.replace('[screenshots]', screenshots);
const readme = await fs.readFile(path.join(repo,'README.md'),'utf8');
report = report.replace('[references]', readme.split('## References')[1]);
let source = '';
for (const filename of (await filesIn(repo)).filter(x=>/\.(cs|java|jsx|js|css|xml|gradle|csproj)$/.test(x)).sort()) {
  const relative=path.relative(repo,filename).replaceAll('\\','/');
  source += `### ${relative}\n\n\`\`\`\`${path.extname(filename).slice(1)}\n${await fs.readFile(filename,'utf8')}\n\`\`\`\`\n\n`;
}
report = report.replace('[source]', source);
await fs.mkdir(path.join(repo,'artifacts'),{recursive:true});
await fs.writeFile(path.join(repo,'artifacts/report-with-source.md'),report);
console.log('Generated artifacts/report-with-source.md with design, verification, team details, screenshots, references and source as text.');
