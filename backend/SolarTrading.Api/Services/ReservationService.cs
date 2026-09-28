/* SE4040 Smart Solar Microgrid Trading System.
 * FAT-service reservation workflow, atomic capacity accounting and signed QR dispatch.
 */
using System.Security.Cryptography;
using System.Text;
using MongoDB.Driver;
using SolarTrading.Api.DTOs;
using SolarTrading.Api.Models;
using SolarTrading.Api.Repositories;

namespace SolarTrading.Api.Services;

public sealed class ReservationService(MongoStore db, GridService grid, TimeProvider clock,
    IConfiguration config)
{
    // Create a pending reservation and claim capacity in the same Mongo transaction.
    public async Task<BookingView> Create(ReservationRequest input, string actor, string role,
        CancellationToken ct)
    {
        var id = role == Roles.Prosumer ? actor : input.ProsumerId;
        if (string.IsNullOrWhiteSpace(id)) throw new DomainException(400, "Select a prosumer.");
        var booking = await db.Transaction(async (session, token) =>
        {
            await RequireProsumer(session, id, token);
            var slot = await Claim(session, input.SlotId, input.EnergyKwh, token);
            BusinessRules.BookingWindow(slot.Start, clock.GetUtcNow().UtcDateTime);
            var r = new Reservation { ProsumerId = id, SlotId = slot.Id, StationId = slot.StationId,
                Start = slot.Start, End = slot.End, EnergyKwh = input.EnergyKwh, Direction = input.Direction };
            await db.Reservations.InsertOneAsync(session, r, cancellationToken: token);
            await db.Log(session, actor, "Reservation:Create", r.Id, token);
            return r;
        }, ct);
        return await View(booking, ct);
    }

    // Change an owned editable booking, releasing and reclaiming capacity atomically.
    public async Task<BookingView> Update(string id, ReservationRequest input, string actor,
        string role, CancellationToken ct)
    {
        var booking = await db.Transaction(async (session, token) =>
        {
            var r = await Owned(session, id, actor, role, token);
            BusinessRules.Editable(r.Status);
            BusinessRules.Notice(r.Start, clock.GetUtcNow().UtcDateTime);
            await RequireProsumer(session, r.ProsumerId, token);
            await Release(session, r, token);
            var slot = await Claim(session, input.SlotId, input.EnergyKwh, token);
            BusinessRules.BookingWindow(slot.Start, clock.GetUtcNow().UtcDateTime);
            BusinessRules.Notice(slot.Start, clock.GetUtcNow().UtcDateTime);
            r.SlotId = slot.Id; r.StationId = slot.StationId; r.Start = slot.Start; r.End = slot.End;
            r.EnergyKwh = input.EnergyKwh; r.Direction = input.Direction; r.Status = "Pending";
            r.QrNonce = ""; r.UpdatedAt = clock.GetUtcNow().UtcDateTime; r.Revision++;
            await db.Reservations.ReplaceOneAsync(session, x => x.Id == id, r, cancellationToken: token);
            await db.Log(session, actor, "Reservation:Update", id, token);
            return r;
        }, ct);
        return await View(booking, ct);
    }

    // Cancel an owned booking with notice and release its held capacity.
    public async Task<BookingView> Cancel(string id, string actor, string role, CancellationToken ct)
    {
        var booking = await db.Transaction(async (session, token) =>
        {
            var r = await Owned(session, id, actor, role, token);
            BusinessRules.Editable(r.Status);
            BusinessRules.Notice(r.Start, clock.GetUtcNow().UtcDateTime);
            await Release(session, r, token);
            r.Status = "Cancelled"; r.QrNonce = ""; r.Revision++;
            r.UpdatedAt = clock.GetUtcNow().UtcDateTime;
            await db.Reservations.ReplaceOneAsync(session, x => x.Id == id, r, cancellationToken: token);
            await db.Log(session, actor, "Reservation:Cancel", id, token);
            return r;
        }, ct);
        return await View(booking, ct);
    }

    // Approve a pending booking or reject it and release capacity; issue a fresh nonce on approval.
    public async Task<BookingView> Decide(string id, bool approve, string actor, CancellationToken ct)
    {
        var booking = await db.Transaction(async (session, token) =>
        {
            var r = await Owned(session, id, actor, Roles.Operator, token);
            if (r.Status != "Pending") throw new DomainException(409, "Only pending reservations can be reviewed.");
            if (r.Start <= clock.GetUtcNow().UtcDateTime) throw new DomainException(409, "This reservation has already started.");
            if (approve) await RequireProsumer(session, r.ProsumerId, token);
            else await Release(session, r, token);
            r.Status = approve ? "Approved" : "Rejected";
            r.QrNonce = approve ? Convert.ToHexString(RandomNumberGenerator.GetBytes(16)) : "";
            r.UpdatedAt = clock.GetUtcNow().UtcDateTime; r.Revision++;
            await db.Reservations.ReplaceOneAsync(session, x => x.Id == id, r, cancellationToken: token);
            await db.Log(session, actor, "Reservation:" + r.Status, id, token);
            return r;
        }, ct);
        return await View(booking, ct);
    }

    // Return a signed QR payload only for an owned approved reservation.
    public async Task<object> Qr(string id, string actor, string role, CancellationToken ct)
    {
        var r = await GetOwned(id, actor, role, ct);
        if (r.Status != "Approved" || r.End < clock.GetUtcNow().UtcDateTime)
            throw new DomainException(409, "QR is only available for a valid approved reservation.");
        var payload = $"v1.{r.Id}.{r.QrNonce}";
        return new { qrCode = payload + "." + Sign(payload), reservationId = id, expiresAt = r.End };
    }

    // Verify QR authenticity and current server state before presenting transfer details.
    public async Task<BookingView> Verify(string code, CancellationToken ct)
    {
        var id = VerifySignature(code);
        var r = await db.Reservations.Find(x => x.Id == id).FirstOrDefaultAsync(ct)
            ?? throw new DomainException(404, "Reservation not found.");
        ValidateQr(r, code, false);
        return await View(r, ct);
    }

    // Finalize a transfer exactly once in its scheduled window and release held battery capacity.
    public async Task<BookingView> Complete(CompleteRequest input, string actor, CancellationToken ct)
    {
        var id = VerifySignature(input.QrCode);
        var r = await db.Transaction(async (session, token) =>
        {
            var booking = await Owned(session, id, actor, Roles.Operator, token);
            ValidateQr(booking, input.QrCode, true);
            BusinessRules.Energy(input.TransferredKwh);
            if (input.TransferredKwh > booking.EnergyKwh)
                throw new DomainException(400, "Actual transfer cannot exceed reserved energy.");
            await Release(session, booking, token);
            booking.Status = "Completed"; booking.CompletedBy = actor;
            booking.CompletedAt = clock.GetUtcNow().UtcDateTime; booking.UpdatedAt = booking.CompletedAt.Value;
            booking.TransferredKwh = input.TransferredKwh; booking.QrNonce = ""; booking.Revision++;
            await db.Reservations.ReplaceOneAsync(session, x => x.Id == id, booking, cancellationToken: token);
            await db.Log(session, actor, "Reservation:Complete", id, token);
            return booking;
        }, ct);
        return await View(r, ct);
    }

    // Read a filtered, paginated booking list; prosumers can never widen their ownership filter.
    public async Task<object> List(string actor, string role, string? status, string? search,
        DateTimeOffset? from, DateTimeOffset? to, int page, int pageSize, CancellationToken ct)
    {
        var f = role == Roles.Prosumer ? Builders<Reservation>.Filter.Eq(x => x.ProsumerId, actor)
            : Builders<Reservation>.Filter.Empty;
        if (!string.IsNullOrWhiteSpace(status)) f &= Builders<Reservation>.Filter.Eq(x => x.Status, status);
        if (from.HasValue) f &= Builders<Reservation>.Filter.Gte(x => x.Start, from.Value.UtcDateTime);
        if (to.HasValue) f &= Builders<Reservation>.Filter.Lte(x => x.Start, to.Value.UtcDateTime);
        if (!string.IsNullOrWhiteSpace(search))
        {
            var escaped = System.Text.RegularExpressions.Regex.Escape(search.Trim());
            var stationIds = await db.Stations.Find(Builders<Station>.Filter.Regex(x => x.Name,
                new MongoDB.Bson.BsonRegularExpression(escaped, "i"))).Project(x => x.Id).ToListAsync(ct);
            f &= Builders<Reservation>.Filter.Regex(x => x.Id, new MongoDB.Bson.BsonRegularExpression(escaped, "i"))
                | Builders<Reservation>.Filter.Regex(x => x.ProsumerId, new MongoDB.Bson.BsonRegularExpression(escaped, "i"))
                | Builders<Reservation>.Filter.In(x => x.StationId, stationIds);
        }
        page = Math.Max(1, page); pageSize = Math.Clamp(pageSize, 1, 100);
        var total = await db.Reservations.CountDocumentsAsync(f, cancellationToken: ct);
        var rows = await db.Reservations.Find(f).SortByDescending(x => x.CreatedAt)
            .Skip((page - 1) * pageSize).Limit(pageSize).ToListAsync(ct);
        var items = new List<BookingView>();
        foreach (var r in rows) items.Add(await View(r, ct));
        return new { items, total, page, pageSize };
    }

    // Calculate live counts server-side for the relevant role and user.
    public async Task<object> Dashboard(string actor, string role, CancellationToken ct)
    {
        var f = role == Roles.Prosumer ? Builders<Reservation>.Filter.Eq(x => x.ProsumerId, actor)
            : Builders<Reservation>.Filter.Empty;
        var now = clock.GetUtcNow().UtcDateTime;
        var pending = await db.Reservations.CountDocumentsAsync(f & Builders<Reservation>.Filter.Eq(x => x.Status, "Pending"), cancellationToken: ct);
        var approvedFuture = await db.Reservations.CountDocumentsAsync(f & Builders<Reservation>.Filter.Eq(x => x.Status, "Approved")
            & Builders<Reservation>.Filter.Gt(x => x.Start, now), cancellationToken: ct);
        var completed = await db.Reservations.CountDocumentsAsync(f & Builders<Reservation>.Filter.Eq(x => x.Status, "Completed"), cancellationToken: ct);
        var nodes = await db.Stations.CountDocumentsAsync(x => x.Active, cancellationToken: ct);
        return new { pending, approvedFuture, completed, activeNodes = nodes };
    }

    // Atomically reserve energy and battery capacity under the published slot limits.
    private async Task<EnergySlot> Claim(IClientSessionHandle session, string id, double energy, CancellationToken ct)
    {
        BusinessRules.Energy(energy);
        var slot = await db.Slots.Find(session, x => x.Id == id && x.Active).FirstOrDefaultAsync(ct)
            ?? throw new DomainException(404, "Slot not found.");
        await grid.Touch(session, slot.StationId, ct);
        var claimed = await db.Slots.FindOneAndUpdateAsync<EnergySlot>(session,
            x => x.Id == id && x.Active && x.ReservedCount < slot.MaxBookings &&
                x.ReservedKwh <= slot.CapacityKwh - energy,
            Builders<EnergySlot>.Update.Inc(x => x.ReservedCount, 1).Inc(x => x.ReservedKwh, energy),
            new FindOneAndUpdateOptions<EnergySlot> { ReturnDocument = ReturnDocument.After }, ct);
        return claimed ?? throw new DomainException(409, "This slot does not have enough energy or battery capacity.");
    }

    // Release only capacity belonging to an existing nonterminal booking.
    private Task<UpdateResult> Release(IClientSessionHandle session, Reservation r, CancellationToken ct) =>
        db.Slots.UpdateOneAsync(session, x => x.Id == r.SlotId,
            Builders<EnergySlot>.Update.Inc(x => x.ReservedCount, -1).Inc(x => x.ReservedKwh, -r.EnergyKwh), cancellationToken: ct);

    // Check target identity against the authoritative active prosumer account.
    private async Task RequireProsumer(IClientSessionHandle session, string id, CancellationToken ct)
    {
        if (!await db.Users.Find(session, x => x.Id == id && x.Role == Roles.Prosumer && x.Status == "Active").AnyAsync(ct))
            throw new DomainException(409, "Prosumer is not active or does not exist.");
    }

    // Load a transaction-scoped reservation and enforce ownership for prosumer callers.
    private async Task<Reservation> Owned(IClientSessionHandle session, string id, string actor,
        string role, CancellationToken ct)
    {
        var r = await db.Reservations.Find(session, x => x.Id == id).FirstOrDefaultAsync(ct)
            ?? throw new DomainException(404, "Reservation not found.");
        if (role == Roles.Prosumer && r.ProsumerId != actor) throw new DomainException(403, "This reservation belongs to another account.");
        return r;
    }

    // Enforce ownership on read paths as well as write paths.
    private async Task<Reservation> GetOwned(string id, string actor, string role, CancellationToken ct)
    {
        var r = await db.Reservations.Find(x => x.Id == id).FirstOrDefaultAsync(ct)
            ?? throw new DomainException(404, "Reservation not found.");
        if (role == Roles.Prosumer && r.ProsumerId != actor) throw new DomainException(403, "This reservation belongs to another account.");
        return r;
    }

    // Produce a safe joined response for summary and history screens.
    private async Task<BookingView> View(Reservation r, CancellationToken ct)
    {
        var node = await db.Stations.Find(x => x.Id == r.StationId).FirstOrDefaultAsync(ct);
        var user = await db.Users.Find(x => x.Id == r.ProsumerId).FirstOrDefaultAsync(ct);
        return BookingView.From(r, node?.Name ?? "Archived node", user?.Name ?? r.ProsumerId);
    }

    // Sign the versioned QR payload with a dedicated server-only HMAC key.
    private string Sign(string payload) => Convert.ToHexString(HMACSHA256.HashData(
        Encoding.UTF8.GetBytes(config["Qr:Key"]!), Encoding.UTF8.GetBytes(payload)));

    // Compare signatures in constant time before querying the reservation identified by a scan.
    private string VerifySignature(string code)
    {
        var parts = code.Split('.');
        if (parts.Length != 4 || parts[0] != "v1" || parts[1].Length != 32 || parts[2].Length != 32 || parts[3].Length != 64)
            throw new DomainException(400, "Invalid transaction QR code.");
        try
        {
            if (!CryptographicOperations.FixedTimeEquals(Convert.FromHexString(parts[3]),
                Convert.FromHexString(Sign(string.Join('.', parts.Take(3))))))
                throw new DomainException(400, "QR signature is invalid.");
        }
        catch (FormatException) { throw new DomainException(400, "QR signature is invalid."); }
        return parts[1];
    }

    // Require the current nonce and status, then enforce the scheduled transfer window.
    private void ValidateQr(Reservation r, string code, bool completing)
    {
        if (r.Status != "Approved" || r.QrNonce != code.Split('.')[2])
            throw new DomainException(409, "Reservation is cancelled, completed, unapproved, or this QR was replaced.");
        var now = clock.GetUtcNow().UtcDateTime;
        if (now > r.End || (completing && now < r.Start))
            throw new DomainException(409, "Energy transfer must be completed during its scheduled slot.");
    }
}
