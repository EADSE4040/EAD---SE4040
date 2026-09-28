/* SE4040 Smart Solar Microgrid Trading System.
 * Node and slot lifecycle with transaction-safe reservation protection.
 */
using MongoDB.Driver;
using SolarTrading.Api.DTOs;
using SolarTrading.Api.Models;
using SolarTrading.Api.Repositories;

namespace SolarTrading.Api.Services;

public sealed class GridService(MongoStore db, TimeProvider clock)
{
    // List actual persisted stations for both dashboards and map clients.
    public async Task<List<Station>> Stations(bool includeInactive, CancellationToken ct,
        double? latitude = null, double? longitude = null, double radiusKm = 25)
    {
        var nodes = await db.Stations.Find(x => includeInactive || x.Active).SortBy(x => x.Name).Limit(500).ToListAsync(ct);
        if (!latitude.HasValue && !longitude.HasValue) return nodes;
        if (!latitude.HasValue || !longitude.HasValue || !double.IsFinite(latitude.Value) ||
            !double.IsFinite(longitude.Value) || Math.Abs(latitude.Value) > 90 || Math.Abs(longitude.Value) > 180 ||
            !double.IsFinite(radiusKm) || radiusKm <= 0 || radiusKm > 500)
            throw new DomainException(400, "Provide valid latitude, longitude and a radius between zero and 500 km.");
        return nodes.Select(node => new { Node = node, Distance = DistanceKm(latitude.Value, longitude.Value, node.Latitude, node.Longitude) })
            .Where(item => item.Distance <= radiusKm).OrderBy(item => item.Distance).Select(item => item.Node).ToList();
    }

    // Calculate great-circle distance centrally so both clients use the same nearby-node criteria.
    private static double DistanceKm(double lat1, double lon1, double lat2, double lon2)
    {
        const double radians = Math.PI / 180;
        var a = Math.Pow(Math.Sin((lat2 - lat1) * radians / 2), 2) + Math.Cos(lat1 * radians)
            * Math.Cos(lat2 * radians) * Math.Pow(Math.Sin((lon2 - lon1) * radians / 2), 2);
        return 6371 * 2 * Math.Atan2(Math.Sqrt(a), Math.Sqrt(Math.Max(0, 1 - a)));
    }

    // Create a node with validated GPS, electrical and storage specifications.
    public async Task<Station> Create(StationRequest input, CancellationToken ct)
    {
        Validate(input);
        var station = new Station
        {
            Name = input.Name.Trim(),
            Address = input.Address.Trim(),
            Latitude = input.Latitude,
            Longitude = input.Longitude,
            CapacityKw = input.CapacityKw,
            BatterySlots = input.BatterySlots,
            Schedule = input.Schedule.Trim()
        };
        await db.Stations.InsertOneAsync(station, cancellationToken: ct);
        return station;
    }

    // Update node specifications while preserving existing slot storage limits.
    public Task<Station> Update(string id, StationRequest input, string actor, CancellationToken ct)
    {
        Validate(input);
        return db.Transaction(async (session, token) =>
        {
            if (await db.Slots.Find(session, x => x.StationId == id && x.Active &&
                x.MaxBookings > input.BatterySlots).AnyAsync(token))
                throw new DomainException(409, "Reduce slot booking limits before reducing battery storage.");
            var result = await db.Stations.FindOneAndUpdateAsync<Station>(session, x => x.Id == id,
                Builders<Station>.Update.Set(x => x.Name, input.Name.Trim()).Set(x => x.Address, input.Address.Trim())
                    .Set(x => x.Latitude, input.Latitude).Set(x => x.Longitude, input.Longitude)
                    .Set(x => x.CapacityKw, input.CapacityKw).Set(x => x.BatterySlots, input.BatterySlots)
                    .Set(x => x.Schedule, input.Schedule.Trim()).Inc(x => x.Revision, 1),
                new FindOneAndUpdateOptions<Station> { ReturnDocument = ReturnDocument.After }, token)
                ?? throw new DomainException(404, "Node not found.");
            await db.Log(session, actor, "Node:Update", id, token);
            return result;
        }, ct);
    }

    // Block node deactivation with pending or approved reservations and conflict with concurrent bookings.
    public Task<bool> Active(string id, bool active, string actor, CancellationToken ct) =>
        db.Transaction(async (session, token) =>
        {
            if (!active && await db.Reservations.Find(session, x => x.StationId == id &&
                (x.Status == "Pending" || x.Status == "Approved")).AnyAsync(token))
                throw new DomainException(409, "Node has active reservations and cannot be deactivated.");
            var result = await db.Stations.UpdateOneAsync(session, x => x.Id == id,
                Builders<Station>.Update.Set(x => x.Active, active).Inc(x => x.Revision, 1), cancellationToken: token);
            if (result.MatchedCount == 0) throw new DomainException(404, "Node not found.");
            await db.Log(session, actor, active ? "Node:Activate" : "Node:Deactivate", id, token);
            return active;
        }, ct);

    // Return future slots from active stations with available capacity counters.
    public async Task<List<EnergySlot>> Slots(string? stationId, bool includePast, CancellationToken ct)
    {
        var nodes = await db.Stations.Find(x => x.Active).Project(x => x.Id).ToListAsync(ct);
        var filter = Builders<EnergySlot>.Filter.In(x => x.StationId, nodes)
            & Builders<EnergySlot>.Filter.Eq(x => x.Active, true);
        if (!string.IsNullOrEmpty(stationId)) filter &= Builders<EnergySlot>.Filter.Eq(x => x.StationId, stationId);
        if (!includePast) filter &= Builders<EnergySlot>.Filter.Gt(x => x.Start, clock.GetUtcNow().UtcDateTime);
        return await db.Slots.Find(filter).SortBy(x => x.Start).Limit(500).ToListAsync(ct);
    }

    // Create a future non-overlapping slot; touch the station to serialize concurrent slot operations.
    public Task<EnergySlot> CreateSlot(string stationId, SlotRequest input, string actor, CancellationToken ct) =>
        db.Transaction(async (session, token) =>
        {
            var node = await Touch(session, stationId, token);
            BusinessRules.Slot(input.Start.UtcDateTime, input.End.UtcDateTime, input.CapacityKwh,
                input.MaxBookings, node.BatterySlots, clock.GetUtcNow().UtcDateTime);
            await NoOverlap(session, stationId, "", input, token);
            var slot = new EnergySlot
            {
                StationId = stationId,
                Start = input.Start.UtcDateTime,
                End = input.End.UtcDateTime,
                CapacityKwh = input.CapacityKwh,
                MaxBookings = input.MaxBookings
            };
            await db.Slots.InsertOneAsync(session, slot, cancellationToken: token);
            await db.Log(session, actor, "Slot:Create", slot.Id, token);
            return slot;
        }, ct);

    // Edit only unreserved slots, so booking time and capacity contracts cannot silently change.
    public Task<EnergySlot> UpdateSlot(string id, SlotRequest input, string actor, CancellationToken ct) =>
        db.Transaction(async (session, token) =>
        {
            var slot = await db.Slots.Find(session, x => x.Id == id && x.Active).FirstOrDefaultAsync(token)
                ?? throw new DomainException(404, "Slot not found.");
            var node = await Touch(session, slot.StationId, token);
            if (slot.ReservedCount > 0) throw new DomainException(409, "Reserved slots cannot be edited.");
            BusinessRules.Slot(input.Start.UtcDateTime, input.End.UtcDateTime, input.CapacityKwh,
                input.MaxBookings, node.BatterySlots, clock.GetUtcNow().UtcDateTime);
            await NoOverlap(session, slot.StationId, id, input, token);
            slot.Start = input.Start.UtcDateTime; slot.End = input.End.UtcDateTime;
            slot.CapacityKwh = input.CapacityKwh; slot.MaxBookings = input.MaxBookings;
            await db.Slots.ReplaceOneAsync(session, x => x.Id == id, slot, cancellationToken: token);
            await db.Log(session, actor, "Slot:Update", id, token);
            return slot;
        }, ct);

    // Archive unreserved slots while retaining references needed by booking history.
    public Task<bool> DeleteSlot(string id, string actor, CancellationToken ct) =>
        db.Transaction(async (session, token) =>
        {
            var slot = await db.Slots.Find(session, x => x.Id == id).FirstOrDefaultAsync(token)
                ?? throw new DomainException(404, "Slot not found.");
            await Touch(session, slot.StationId, token);
            if (slot.ReservedCount > 0) throw new DomainException(409, "Reserved slots cannot be deleted.");
            await db.Slots.UpdateOneAsync(session, x => x.Id == id,
                Builders<EnergySlot>.Update.Set(x => x.Active, false), cancellationToken: token);
            await db.Log(session, actor, "Slot:Archive", id, token);
            return true;
        }, ct);

    // Increment the node revision in a transaction to prevent deactivation and scheduling races.
    public async Task<Station> Touch(IClientSessionHandle session, string id, CancellationToken ct) =>
        await db.Stations.FindOneAndUpdateAsync<Station>(session, x => x.Id == id && x.Active,
            Builders<Station>.Update.Inc(x => x.Revision, 1),
            new FindOneAndUpdateOptions<Station> { ReturnDocument = ReturnDocument.After }, ct)
        ?? throw new DomainException(409, "Node is inactive or unavailable.");

    // Reject overlapping published time windows for the same node.
    private async Task NoOverlap(IClientSessionHandle session, string stationId, string exceptId,
        SlotRequest input, CancellationToken ct)
    {
        if (await db.Slots.Find(session, x => x.StationId == stationId && x.Active && x.Id != exceptId
            && x.Start < input.End.UtcDateTime && x.End > input.Start.UtcDateTime).AnyAsync(ct))
            throw new DomainException(409, "A published slot already overlaps this time window.");
    }

    // Explicitly reject NaN and infinity, which range annotations alone may not exclude.
    private static void Validate(StationRequest input)
    {
        if (!double.IsFinite(input.Latitude) || !double.IsFinite(input.Longitude) ||
            !double.IsFinite(input.CapacityKw)) throw new DomainException(400, "Node measurements must be finite.");
    }
}
