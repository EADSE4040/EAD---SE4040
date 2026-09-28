/* SE4040 Smart Solar Microgrid Trading System.
 * Resolve elapsed reservations so abandoned requests cannot retain battery capacity forever.
 */
using MongoDB.Driver;
using SolarTrading.Api.Repositories;
using SolarTrading.Api.Models;

namespace SolarTrading.Api.Services;

public sealed class ReservationExpiryService(MongoStore db, TimeProvider clock,
    ILogger<ReservationExpiryService> logger) : BackgroundService
{
    // Release expired active bookings transactionally, preserving their audit/history records.
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromMinutes(1));
        do
        {
            try
            {
                var now = clock.GetUtcNow().UtcDateTime;
                var ids = await db.Reservations.Find(x => x.End < now &&
                    (x.Status == "Pending" || x.Status == "Approved")).Project(x => x.Id).Limit(500).ToListAsync(stoppingToken);
                foreach (var id in ids)
                    await db.Transaction(async (session, ct) =>
                    {
                        // Recheck current state because a transfer may have completed after the first scan.
                        var r = await db.Reservations.Find(session, x => x.Id == id && x.End < now &&
                            (x.Status == "Pending" || x.Status == "Approved")).FirstOrDefaultAsync(ct);
                        if (r is null) return false;
                        await db.Slots.UpdateOneAsync(session, x => x.Id == r.SlotId,
                            Builders<EnergySlot>.Update.Inc(x => x.ReservedCount, -1).Inc(x => x.ReservedKwh, -r.EnergyKwh), cancellationToken: ct);
                        await db.Reservations.UpdateOneAsync(session, x => x.Id == id,
                            Builders<Reservation>.Update.Set(x => x.Status, "Expired").Set(x => x.QrNonce, "")
                                .Set(x => x.UpdatedAt, now).Inc(x => x.Revision, 1), cancellationToken: ct);
                        await db.Log(session, "system", "Reservation:Expire", id, ct);
                        return true;
                    }, stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { break; }
            catch (Exception e) { logger.LogError(e, "Reservation expiry pass failed; will retry."); }
        } while (await timer.WaitForNextTickAsync(stoppingToken));
    }
}
