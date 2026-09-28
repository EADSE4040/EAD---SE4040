/* SE4040 Smart Solar Microgrid Trading System.
 * Database indexes and optional first-admin bootstrap from environment configuration.
 */
using Microsoft.AspNetCore.Identity;
using MongoDB.Driver;
using SolarTrading.Api.Models;
using SolarTrading.Api.Repositories;

namespace SolarTrading.Api.Services;

public sealed class DatabaseInitializer(MongoStore db, IConfiguration config, ILogger<DatabaseInitializer> logger) : IHostedService
{
    // Initialize uniqueness/query indexes and create the initial Backoffice account only when configured.
    public async Task StartAsync(CancellationToken ct)
    {
        await db.Users.Indexes.CreateOneAsync(new CreateIndexModel<User>(
            Builders<User>.IndexKeys.Ascending(x => x.Email), new CreateIndexOptions { Unique = true }), cancellationToken: ct);
        await db.Slots.Indexes.CreateOneAsync(new CreateIndexModel<EnergySlot>(
            Builders<EnergySlot>.IndexKeys.Ascending(x => x.StationId).Ascending(x => x.Start)), cancellationToken: ct);
        await db.Reservations.Indexes.CreateOneAsync(new CreateIndexModel<Reservation>(
            Builders<Reservation>.IndexKeys.Ascending(x => x.ProsumerId).Ascending(x => x.Status).Ascending(x => x.Start)), cancellationToken: ct);
        await db.Reservations.Indexes.CreateOneAsync(new CreateIndexModel<Reservation>(
            Builders<Reservation>.IndexKeys.Ascending(x => x.StationId).Ascending(x => x.Status)), cancellationToken: ct);
        var email = config["Bootstrap:Email"]?.Trim().ToLowerInvariant();
        var password = config["Bootstrap:Password"];
        if (string.IsNullOrWhiteSpace(email) || string.IsNullOrWhiteSpace(password)) return;
        if (password.Length < 12) throw new InvalidOperationException("Bootstrap password must have at least twelve characters.");
        if (await db.Users.Find(x => x.Role == Roles.Backoffice).AnyAsync(ct)) return;
        var admin = new User { Name = "System Administrator", Email = email, Role = Roles.Backoffice, Status = "Active" };
        admin.PasswordHash = new PasswordHasher<User>().HashPassword(admin, password);
        await db.Users.InsertOneAsync(admin, cancellationToken: ct);
        logger.LogInformation("Initial Backoffice account created. Remove bootstrap credentials from the deployment configuration.");
    }

    // MongoClient owns connection pooling and needs no per-hosted-service shutdown action.
    public Task StopAsync(CancellationToken ct) => Task.CompletedTask;
}
