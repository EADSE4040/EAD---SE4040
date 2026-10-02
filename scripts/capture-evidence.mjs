// Read-only snapshot of real MongoDB records and HTTP deployment responses.
// Install mongodb under .tools/report-tools before running this local evidence utility.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(path.join(root,'.tools/report-tools/package.json'));
const {MongoClient}=require('mongodb');
const local=JSON.parse(await fs.readFile(path.join(root,'backend/SolarTrading.Api/appsettings.Local.json'),'utf8'));
const defaults=JSON.parse(await fs.readFile(path.join(root,'backend/SolarTrading.Api/appsettings.json'),'utf8'));
const client=new MongoClient(process.env.EVIDENCE_MONGO_URL || local.Mongo.ConnectionString, { serverSelectionTimeoutMS: 10000 });
const evidence={capturedUtc:new Date().toISOString(),description:'Read-only evidence from the running local deployment; this is a generated snapshot, not the MongoDB administration UI.'};
try {
 await client.connect(); const db=client.db(process.env.EVIDENCE_MONGO_DATABASE||local.Mongo.Database||defaults.Mongo.Database);
 evidence.database=db.databaseName;
 evidence.replicaSet=(await db.admin().command({hello:1})).setName;
 evidence.collections=[];
 for(const name of ['Users','SolarStationInfo','EnergyBookingSlots','EnergyReservations','AuditLog']) {
   const c=db.collection(name);
   evidence.collections.push({name,count:await c.countDocuments(),indexes:(await c.listIndexes().toArray()).map(x=>({name:x.name,key:x.key,unique:x.name==='_id_'||Boolean(x.unique)}))});
 }
 // Omit identities, password hashes, token versions, QR nonces and secrets.
 evidence.stations=await db.collection('SolarStationInfo').find({},{projection:{_id:0,Name:1,Latitude:1,Longitude:1,CapacityKw:1,BatterySlots:1,Active:1}}).limit(10).toArray();
 evidence.reservationStates=await db.collection('EnergyReservations').aggregate([{$group:{_id:'$Status',count:{$sum:1}}},{$sort:{_id:1}}]).toArray();
} finally {await client.close();}
evidence.http=[];
for(const url of ['http://127.0.0.1:8080/api/health','http://127.0.0.1:8081']) {
 const response=await fetch(url);
 evidence.http.push({url,status:response.status,server:response.headers.get('server'),...(url.endsWith('/health')?{body:await response.json()}:{})});
}
await fs.mkdir(path.join(root,'docs/evidence'),{recursive:true});
await fs.writeFile(path.join(root,'docs/evidence/deployment.json'),JSON.stringify(evidence,null,2)+'\n');
const escape=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const rows=evidence.collections.map(c=>`<tr><td>${escape(c.name)}</td><td>${c.count}</td><td>${escape(c.indexes.map(i=>i.name).join(', '))}</td></tr>`).join('');
const http=evidence.http.map(h=>`<li><b>${escape(h.url)}</b><br>HTTP ${h.status} | ${escape(h.server)}${h.body?`<pre>${escape(JSON.stringify(h.body,null,2))}</pre>`:''}</li>`).join('');
const html=`<!doctype html><html><meta charset="utf-8"><title>Solara - deployment evidence</title><style>body{font:16px system-ui;background:#f5f7f1;color:#24372f;margin:36px auto;max-width:1100px}h1,h2{color:#205d46}section{background:white;padding:24px;border-radius:14px;margin:18px 0}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:12px;border-bottom:1px solid #ddd}th{background:#edf3ec}small{color:#52685b}li{margin:14px 0}pre{font-size:13px;white-space:pre-wrap}</style><h1>Solara | Deployment evidence</h1><small>Captured ${escape(evidence.capturedUtc)}. Read-only generated snapshot of actual local services.</small><section><h2>IIS health and reachability</h2><ul>${http}</ul></section><section><h2>MongoDB: ${escape(evidence.database)} / replica set ${escape(evidence.replicaSet)}</h2><table><tr><th>Collection</th><th>Records</th><th>Indexes</th></tr>${rows}</table></section><section><h2>Reservation states</h2><pre>${escape(JSON.stringify(evidence.reservationStates,null,2))}</pre><small>Synthetic demonstration records. Sensitive fields are excluded.</small></section></html>`;
await fs.writeFile(path.join(root,'docs/evidence/deployment.html'),html);
console.log('Saved actual HTTP and MongoDB evidence under docs/evidence (sensitive fields excluded).');
