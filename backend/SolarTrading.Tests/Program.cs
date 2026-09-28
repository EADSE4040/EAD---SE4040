/* SE4040 Smart Solar Microgrid Trading System.
 * Executable integration suite against a real disposable MongoDB database.
 * Run with MONGO_TEST_URL pointing to a development replica set. No production data is accessed.
 */
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using MongoDB.Bson;
using MongoDB.Driver;
using SolarTrading.Api.DTOs;
using SolarTrading.Api.Models;
using SolarTrading.Api.Repositories;
using SolarTrading.Api.Services;

var url = Environment.GetEnvironmentVariable("MONGO_TEST_URL") ?? "mongodb://127.0.0.1:27018/?replicaSet=rs0";
if (args.Contains("--init"))
{
    // Initialize only the explicitly local development replica set used by this suite.
    var client = new MongoClient("mongodb://127.0.0.1:27018/?directConnection=true");
    try
    {
        await client.GetDatabase("admin").RunCommandAsync<BsonDocument>(new BsonDocument("replSetInitiate", new BsonDocument
    { { "_id", "rs0" }, { "members", new BsonArray { new BsonDocument { { "_id", 0 }, { "host", "127.0.0.1:27018" } } } } }));
    }
    catch (MongoCommandException e) when (e.Code == 23) { Console.WriteLine("Development replica set already initialized."); }
    Console.WriteLine("Development replica set initialized.");
    return;
}
var name = "SolarTradingTest_" + Guid.NewGuid().ToString("N");
var config = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
{
    ["Mongo:ConnectionString"] = url,
    ["Mongo:Database"] = name,
    ["Jwt:Key"] = "test-only-signing-secret-at-least-32-bytes",
    ["Qr:Key"] = "test-only-qr-secret-different-at-least-32-bytes",
    ["Jwt:Issuer"] = "SolarTrading",
    ["Jwt:Audience"] = "SolarTradingClients"
}).Build();
var db = new MongoStore(config);
var clock = new ControlledClock(new DateTimeOffset(2026, 9, 28, 0, 0, 0, TimeSpan.Zero));
var grid = new GridService(db, clock);
var accounts = new AccountService(db, config);
var bookings = new ReservationService(db, grid, clock, config);
int passed = 0;

// Assert an observable condition and emit named evidence for every checked scenario.
void Check(bool condition, string scenario)
{
    if (!condition) throw new Exception("FAIL: " + scenario);
    passed++; Console.WriteLine("PASS: " + scenario);
}

// Require the exact domain rejection status instead of treating any failure as success.
async Task Reject(Func<Task> operation, int expected, string scenario)
{
    try { await operation(); }
    catch (DomainException e) when (e.Status == expected)
    { Check(true, scenario); return; }
    throw new Exception("FAIL: " + scenario + " did not reject with " + expected);
}

try
{
    await new DatabaseInitializer(db, config, NullLogger<DatabaseInitializer>.Instance).StartAsync(default);
    var p = await accounts.Register(new RegisterRequest("199812345678", "Test Prosumer", "prosumer@example.test",
        "Independent-Test-Pass!", "0771234567", "Test address"), false, default);
    Check(p.Status == "Pending" && p.Id == p.Nic, "NIC primary key and pending registration");
    await Reject(() => accounts.Login(new LoginRequest(p.Email, "Independent-Test-Pass!"), default), 403, "Pending account cannot log in");
    await Reject(() => accounts.Register(new RegisterRequest(p.Id, "Duplicate", p.Email, "Independent-Test-Pass!", "0771234567", "Address"), true, default), 409, "Duplicate NIC/email is rejected");
    await accounts.SetStatus(p.Id, "Active", "admin", default);
    Check(await accounts.Login(new LoginRequest(p.Email, "Independent-Test-Pass!"), default) is not null, "Activated account can log in");
    await Reject(() => accounts.Login(new LoginRequest(p.Email, "wrong password"), default), 401, "Incorrect password rejected");
    var station = await grid.Create(new StationRequest("Test node", "Colombo", 6.9271, 79.8612, 100, 3, "Daily 06:00-22:00"), default);
    Check((await grid.Stations(false, default, 6.9271, 79.8612, 1)).Count == 1, "Nearby station returned from persisted GPS data");
    Check((await grid.Stations(false, default, 0, 0, 1)).Count == 0, "Distant station excluded from nearby search");
    var start = clock.GetUtcNow().AddHours(24);
    var slot = await grid.CreateSlot(station.Id, new SlotRequest(start, start.AddHours(1), 30, 3), "admin", default);
    Check(slot.ReservedCount == 0, "Published slot starts with zero held capacity");
    await Reject(() => grid.CreateSlot(station.Id, new SlotRequest(start.AddMinutes(15), start.AddHours(2), 20, 2), "admin", default), 409, "Overlapping slots rejected");
    var r = await bookings.Create(new ReservationRequest(slot.Id, 10, "DropOff"), p.Id, Roles.Prosumer, default);
    Check(r.Status == "Pending", "Booking starts pending");
    await Reject(() => grid.Active(station.Id, false, "admin", default), 409, "Node with active reservation cannot deactivate");
    await Reject(() => grid.UpdateSlot(slot.Id, new SlotRequest(start, start.AddHours(1), 20, 2), "admin", default), 409, "Reserved slot cannot be edited");
    await Reject(() => bookings.Update(r.Id, new ReservationRequest(slot.Id, 12, "DropOff"), "someone-else", Roles.Prosumer, default), 403, "Prosumer cannot update another owner's booking");
    r = await bookings.Decide(r.Id, true, "operator", default);
    Check(r.Status == "Approved", "Operator approval");
    var qr = System.Text.Json.JsonSerializer.SerializeToElement(await bookings.Qr(r.Id, p.Id, Roles.Prosumer, default)).GetProperty("qrCode").GetString()!;
    Check((await bookings.Verify(qr, default)).Id == r.Id, "Signed QR verified against server record");
    await Reject(() => bookings.Verify(qr[..^1] + (qr[^1] == '0' ? '1' : '0'), default), 400, "Tampered QR rejected");
    await Reject(() => bookings.Complete(new CompleteRequest(qr, 10), "operator", default), 409, "Completion before scheduled window rejected");
    r = await bookings.Update(r.Id, new ReservationRequest(slot.Id, 12, "Charging"), p.Id, Roles.Prosumer, default);
    Check(r.Status == "Pending", "Modification requires new approval");
    await Reject(() => bookings.Verify(qr, default), 409, "Old QR invalidated after modification");
    var capacity = await db.Slots.Find(x => x.Id == slot.Id).FirstAsync();
    Check(capacity.ReservedCount == 1 && Math.Abs(capacity.ReservedKwh - 12) < 0.001, "Modification releases previous capacity atomically");
    await bookings.Cancel(r.Id, p.Id, Roles.Prosumer, default);
    capacity = await db.Slots.Find(x => x.Id == slot.Id).FirstAsync();
    Check(capacity.ReservedCount == 0 && Math.Abs(capacity.ReservedKwh) < 0.001, "Cancellation releases all held capacity");
    await Reject(() => bookings.Cancel(r.Id, p.Id, Roles.Prosumer, default), 409, "Repeated cancellation rejected");
    var distant = await grid.CreateSlot(station.Id, new SlotRequest(start.AddDays(8), start.AddDays(8).AddHours(1), 20, 2), "admin", default);
    await Reject(() => bookings.Create(new ReservationRequest(distant.Id, 5, "DropOff"), p.Id, Roles.Prosumer, default), 400, "Booking beyond seven days rejected");
    var boundary = await grid.CreateSlot(station.Id, new SlotRequest(clock.GetUtcNow().AddDays(7), clock.GetUtcNow().AddDays(7).AddHours(1), 20, 2), "admin", default);
    var edge = await bookings.Create(new ReservationRequest(boundary.Id, 5, "DropOff"), p.Id, Roles.Prosumer, default);
    Check(edge.Status == "Pending", "Exactly seven days accepted");
    await bookings.Cancel(edge.Id, p.Id, Roles.Prosumer, default);
    var near = await grid.CreateSlot(station.Id, new SlotRequest(clock.GetUtcNow().AddHours(12), clock.GetUtcNow().AddHours(13), 10, 1), "admin", default);
    var nearBooking = await bookings.Create(new ReservationRequest(near.Id, 5, "DropOff"), p.Id, Roles.Prosumer, default);
    await bookings.Cancel(nearBooking.Id, p.Id, Roles.Prosumer, default);
    Check(true, "Exactly twelve hours' cancellation notice accepted");
    var soon = await grid.CreateSlot(station.Id, new SlotRequest(clock.GetUtcNow().AddHours(10), clock.GetUtcNow().AddHours(11), 10, 1), "admin", default);
    var soonBooking = await bookings.Create(new ReservationRequest(soon.Id, 5, "DropOff"), p.Id, Roles.Prosumer, default);
    await Reject(() => bookings.Cancel(soonBooking.Id, p.Id, Roles.Prosumer, default), 409, "Cancellation inside twelve hours rejected");
    await Reject(() => bookings.Update(soonBooking.Id, new ReservationRequest(soon.Id, 4, "Charging"), p.Id, Roles.Prosumer, default), 409, "Modification inside twelve hours rejected");
    await bookings.Decide(soonBooking.Id, false, "operator", default);
    var exclusive = await grid.CreateSlot(station.Id, new SlotRequest(start.AddHours(2), start.AddHours(3), 5, 1), "admin", default);
    var tasks = Enumerable.Range(0, 10).Select(async _ =>
    {
        // Race real transactions for the last battery slot and observe exactly one successful booking.
        try { return await bookings.Create(new ReservationRequest(exclusive.Id, 5, "DropOff"), p.Id, Roles.Prosumer, default); }
        catch (DomainException e) when (e.Status == 409) { return null; }
    });
    var results = await Task.WhenAll(tasks);
    Check(results.Count(x => x is not null) == 1, "Concurrent requests cannot overbook final capacity");
    var winner = results.Single(x => x is not null)!;
    await bookings.Decide(winner.Id, true, "operator", default);
    var payload = System.Text.Json.JsonSerializer.SerializeToElement(await bookings.Qr(winner.Id, p.Id, Roles.Prosumer, default)).GetProperty("qrCode").GetString()!;
    clock.Now = start.AddHours(2).AddMinutes(10);
    await Reject(() => bookings.Complete(new CompleteRequest(payload, 6), "operator", default), 400, "Transfer cannot exceed reserved energy");
    var complete = await bookings.Complete(new CompleteRequest(payload, 4.5), "operator", default);
    Check(complete.Status == "Completed" && complete.TransferredKwh == 4.5, "Scheduled transfer completes with measured energy");
    await Reject(() => bookings.Complete(new CompleteRequest(payload, 4.5), "operator", default), 409, "QR replay cannot complete a transfer twice");
    Check(await grid.Active(station.Id, false, "admin", default) == false, "Node can deactivate after active bookings are resolved");
    var expiryNode = await grid.Create(new StationRequest("Expiry node", "Test", 6.9, 79.8, 20, 1, "Daily"), default);
    var expiryStart = clock.GetUtcNow().AddHours(1);
    var expirySlot = await grid.CreateSlot(expiryNode.Id, new SlotRequest(expiryStart, expiryStart.AddHours(1), 5, 1), "admin", default);
    var expiryBooking = await bookings.Create(new ReservationRequest(expirySlot.Id, 5, "DropOff"), p.Id, Roles.Prosumer, default);
    clock.Now = expiryStart.AddHours(2);
    using var worker = new ReservationExpiryService(db, clock, NullLogger<ReservationExpiryService>.Instance);
    await worker.StartAsync(default);
    for (var attempt = 0; attempt < 50; attempt++)
    {
        // Poll the specific running expiry job until its transaction has resolved the test booking.
        if ((await db.Reservations.Find(x => x.Id == expiryBooking.Id).FirstAsync()).Status == "Expired") break;
        await Task.Delay(100);
    }
    await worker.StopAsync(default);
    var expired = await db.Reservations.Find(x => x.Id == expiryBooking.Id).FirstAsync();
    var released = await db.Slots.Find(x => x.Id == expirySlot.Id).FirstAsync();
    Check(expired.Status == "Expired" && released.ReservedCount == 0 && released.ReservedKwh == 0, "Expired reservation releases capacity transactionally");
    await accounts.DeactivateSelf(p.Id, default);
    await Reject(() => accounts.Login(new LoginRequest(p.Email, "Independent-Test-Pass!"), default), 403, "Deactivated account cannot log in");
    Check((await accounts.Get(p.Id, default)).TokenVersion > 0, "Account status changes revoke existing token versions");
    Console.WriteLine($"All {passed} checks passed against real MongoDB transactions.");
}
finally
{
    // Remove only the randomly named test database created by this run.
    await db.Client.DropDatabaseAsync(name);
}

public sealed class ControlledClock(DateTimeOffset now) : TimeProvider
{
    public DateTimeOffset Now { get; set; } = now;
    // Provide deterministic server time for booking boundaries and scheduled QR completion.
    public override DateTimeOffset GetUtcNow() => Now;
}
