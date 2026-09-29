import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

// Synthetic demo data, created through the API to preserve all business rules.
// Keep credentials and resumable progress in the ignored .tools directory.
const base = process.env.API_URL || 'http://localhost:5080/api';
const stateFile = new URL('../.tools/sample-data.json', import.meta.url);
const config = JSON.parse(await fs.readFile(new URL('../backend/SolarTrading.Api/appsettings.Local.json', import.meta.url), 'utf8'));
let state;
try { state = JSON.parse(await fs.readFile(stateFile, 'utf8')); }
catch (error) { if (error.code !== 'ENOENT') throw error; state = { accounts: [], slots: [], bookings: [] }; }
const save = () => fs.writeFile(stateFile, JSON.stringify(state, null, 2));
async function call(path, method = 'GET', body, token) {
  const response = await fetch(base + path, {
    method, signal: AbortSignal.timeout(60000),
    headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {})
  });
  const value = await response.json().catch(() => null);
  if (!response.ok) throw new Error(`${method} ${path}: ${value?.title || response.status}`);
  return value;
}
await call('/health');
const admin = await call('/auth/login', 'POST', { email: config.Bootstrap.Email, password: config.Bootstrap.Password });
let users = await call('/users', 'GET', undefined, admin.token);
const people = [
  ['Nimal Perera', 'GridOperator'], ['Kavitha Rajan', 'GridOperator'],
  ['Arun Selvarajah', 'Prosumer'], ['Dilani Fernando', 'Prosumer'],
  ['Mohamed Farhan', 'Prosumer'], ['Tharushi Silva', 'Prosumer'], ['Sanjay Kumar', 'Pending']
];
for (const [index, [name, role]] of people.entries()) {
  const email = `${name.toLowerCase().replaceAll(' ', '.')}@demo.example.test`;
  if (users.some(user => user.email === email)) continue;
  let account = state.accounts.find(item => item.email === email);
  if (!account) {
    account = { name: `${name} (Demo)`, email, password: crypto.randomBytes(18).toString('base64url'), role };
    state.accounts.push(account); await save();
  }
  const body = { ...account, nic: `99990000000${index}`, phone: `000000000${index}`, address: 'Synthetic demo household, Sri Lanka' };
  const user = await call(role === 'GridOperator' ? '/users/staff' : role === 'Pending' ? '/auth/register' : '/users/prosumers', 'POST', body, admin.token);
  users.push(user);
}
const hubs = [
  ['Colombo Community Solar Hub (Demo)', 'Colombo 07, Sri Lanka (synthetic site)', 6.9061, 79.8696, 120, 8],
  ['Jaffna Solar Exchange (Demo)', 'Jaffna, Sri Lanka (synthetic site)', 9.6615, 80.0255, 90, 6],
  ['Kandy Green Energy Hub (Demo)', 'Kandy, Sri Lanka (synthetic site)', 7.2906, 80.6337, 75, 5],
  ['Galle Coastal Microgrid (Demo)', 'Galle, Sri Lanka (synthetic site)', 6.0535, 80.221, 100, 7]
];
let stations = await call('/stations?includeInactive=true', 'GET', undefined, admin.token);
const existingSlots = await call('/slots?includePast=true', 'GET', undefined, admin.token);
const tomorrow = new Date();
tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
tomorrow.setUTCHours(3, 30, 0, 0); // 09:00 Sri Lanka time.
for (const [name, address, latitude, longitude, capacityKw, batterySlots] of hubs) {
  let station = stations.find(item => item.name === name);
  if (!station) {
    station = await call('/stations', 'POST', { name, address, latitude, longitude, capacityKw, batterySlots, schedule: 'Daily 08:00-18:00 (Asia/Colombo)' }, admin.token);
    stations.push(station);
  }
  for (let day = 0; day < 3; day++) {
    for (const hour of [0, 4]) {
      const start = new Date(tomorrow.getTime() + day * 86400000 + hour * 3600000).toISOString();
      let slot = existingSlots.find(item => item.stationId === station.id && Date.parse(item.start) === Date.parse(start));
      if (!slot) {
        slot = await call(`/stations/${station.id}/slots`, 'POST', { start, end: new Date(Date.parse(start) + 7200000).toISOString(), capacityKwh: capacityKw, maxBookings: batterySlots }, admin.token);
        existingSlots.push(slot);
      }
      if (!state.slots.some(item => item.id === slot.id)) { state.slots.push(slot); await save(); }
    }
  }
}
const prosumers = users.filter(user => user.role === 'Prosumer' && user.status === 'Active' && user.email.endsWith('@demo.example.test'));
const bookings = (await call('/reservations?pageSize=100', 'GET', undefined, admin.token)).items;
const sampleSlots = state.slots.filter(slot => Date.parse(slot.start) > Date.now() + 12 * 3600000);
for (let index = 0; index < 12; index++) {
  const slot = sampleSlots[index];
  if (!slot) break;
  const prosumer = prosumers[index % prosumers.length];
  let booking = bookings.find(item => item.slotId === slot.id && item.prosumerId === prosumer.id);
  if (!booking) {
    booking = await call('/reservations', 'POST', { slotId: slot.id, prosumerId: prosumer.id, energyKwh: [8, 12, 18, 24][index % 4], direction: index % 2 ? 'Charging' : 'DropOff' }, admin.token);
    bookings.push(booking);
  }
  const action = [null, 'approve', 'reject', 'cancel'][index % 4];
  if (action && booking.status === 'Pending') booking = await call(`/reservations/${booking.id}/${action}`, 'POST', undefined, admin.token);
  if (!state.bookings.some(item => item.id === booking.id)) state.bookings.push(booking);
  await save();
}
// Verify persisted records and reservation capacity totals via the API.
const verifiedSlots = await call('/slots?includePast=true', 'GET', undefined, admin.token);
const verifiedBookings = (await call('/reservations?pageSize=100', 'GET', undefined, admin.token)).items;
for (const slot of verifiedSlots.filter(item => state.slots.some(saved => saved.id === item.id))) {
  const held = verifiedBookings.filter(item => item.slotId === slot.id && ['Pending', 'Approved'].includes(item.status));
  assert.equal(slot.reservedCount, held.length);
  assert.equal(slot.reservedKwh, held.reduce((sum, item) => sum + item.energyKwh, 0));
}
console.log(JSON.stringify({ sampleAccounts: state.accounts.length, sampleStations: hubs.length, sampleSlots: state.slots.length, sampleBookings: state.bookings.length, dashboard: await call('/reservations/dashboard', 'GET', undefined, admin.token) }, null, 2));
console.log('Sample login credentials saved privately in .tools/sample-data.json. Capacity counters verified.');
