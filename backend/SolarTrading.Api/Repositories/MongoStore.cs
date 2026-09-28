/* SE4040 Smart Solar Microgrid Trading System.
 * MongoDB collections and transaction boundary. A replica set is required.
 */
using MongoDB.Driver;
using SolarTrading.Api.Models;

namespace SolarTrading.Api.Repositories;

public sealed class MongoStore
{
    public MongoClient Client { get; }
    public IMongoDatabase Database { get; }
    public IMongoCollection<User> Users { get; }
    public IMongoCollection<Station> Stations { get; }
    public IMongoCollection<EnergySlot> Slots { get; }
    public IMongoCollection<Reservation> Reservations { get; }
    public IMongoCollection<AuditEntry> Audit { get; }

    // Create one reusable Mongo client and the required named collections.
    public MongoStore(IConfiguration config)
    {
        var settings = MongoClientSettings.FromConnectionString(config["Mongo:ConnectionString"]);
        settings.ServerSelectionTimeout = TimeSpan.FromSeconds(5);
        Client = new MongoClient(settings);
        Database = Client.GetDatabase(config["Mongo:Database"] ?? "SolarTrading");
        Users = Database.GetCollection<User>("Users");
        Stations = Database.GetCollection<Station>("SolarStationInfo");
        Slots = Database.GetCollection<EnergySlot>("EnergyBookingSlots");
        Reservations = Database.GetCollection<Reservation>("EnergyReservations");
        Audit = Database.GetCollection<AuditEntry>("AuditLog");
    }

    // Retry transaction conflicts so bookings, counters and audit records commit together.
    public async Task<T> Transaction<T>(Func<IClientSessionHandle, CancellationToken, Task<T>> action,
        CancellationToken ct)
    {
        using var session = await Client.StartSessionAsync(cancellationToken: ct);
        return await session.WithTransactionAsync(action,
            new TransactionOptions(readConcern: ReadConcern.Snapshot, writeConcern: WriteConcern.WMajority), ct);
    }

    // Persist a transaction-scoped audit event alongside its business operation.
    public Task Log(IClientSessionHandle session, string actor, string action, string entity,
        CancellationToken ct) => Audit.InsertOneAsync(session,
            new AuditEntry { ActorId = actor, Action = action, EntityId = entity }, cancellationToken: ct);
}
