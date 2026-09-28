import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ignored = new Set(['.git','.tools','node_modules','bin','obj','build','dist','.gradle','artifacts']);
async function filesIn(directory) {
  const result = [];
  for (const item of await fs.readdir(directory, { withFileTypes:true })) {
    if (ignored.has(item.name)) continue;
    const filename = path.join(directory,item.name);
    if (item.isDirectory()) result.push(...await filesIn(filename)); else result.push(filename);
  }
  return result;
}
let report = '# Smart Solar Microgrid Trading System — Project Report Draft\n\nRepository: https://github.com/EADSE4040/EAD---SE4040\n\n';
for (const filename of ['docs/design.md','docs/contributions.md','docs/verification.md','docs/deployment/iis.md','docs/submission.md']) {
  report += await fs.readFile(path.join(repo,filename),'utf8') + '\n\n';
}
report += '# Web UI screenshots\n\n';
for (const filename of (await fs.readdir(path.join(repo,'docs/screenshots'))).filter(x=>x.endsWith('.png')).sort()) {
  report += `## ${filename.replace('.png','').replaceAll('-',' ')}\n\n![${filename}](docs/screenshots/${filename})\n\n`;
}
report += '# References\n\n';
const readme = await fs.readFile(path.join(repo,'README.md'),'utf8');
report += readme.split('## References')[1] + '\n\n# Source code appendix\n\n';
for (const filename of (await filesIn(repo)).filter(x=>/\.(cs|java|jsx|js|css|xml|gradle|csproj)$/.test(x)).sort()) {
  const relative=path.relative(repo,filename).replaceAll('\\','/');
  report += `## ${relative}\n\n\`\`\`\`${path.extname(filename).slice(1)}\n${await fs.readFile(filename,'utf8')}\n\`\`\`\`\n\n`;
}
await fs.mkdir(path.join(repo,'artifacts'),{recursive:true});
await fs.writeFile(path.join(repo,'artifacts/report-with-source.md'),report);
console.log('Generated artifacts/report-with-source.md with design, verification, team details, screenshots, references and source as text.');
