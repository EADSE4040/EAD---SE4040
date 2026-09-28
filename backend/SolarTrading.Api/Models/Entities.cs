/* SE4040 Smart Solar Microgrid Trading System.
 * MongoDB persistence entities; business decisions belong to application services.
 */
using MongoDB.Bson.Serialization.Attributes;

namespace SolarTrading.Api.Models;

public static class Roles
{
    public const string Backoffice = "Backoffice";
    public const string Operator = "GridOperator";
    public const string Prosumer = "Prosumer";
    public const string Staff = Backoffice + "," + Operator;
}

public sealed class User
{
    [BsonId] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string? Nic { get; set; }
    public string Name { get; set; } = "";
    public string Email { get; set; } = "";
    public string Phone { get; set; } = "";
    public string Address { get; set; } = "";
    public string PasswordHash { get; set; } = "";
    public string Role { get; set; } = Roles.Prosumer;
    public string Status { get; set; } = "Pending";
    public int TokenVersion { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}

public sealed class Station
{
    [BsonId] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string Name { get; set; } = "";
    public string Address { get; set; } = "";
    public double Latitude { get; set; }
    public double Longitude { get; set; }
    public double CapacityKw { get; set; }
    public int BatterySlots { get; set; }
    public string Schedule { get; set; } = "";
    public bool Active { get; set; } = true;
    public int Revision { get; set; }
}

public sealed class EnergySlot
{
    [BsonId] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string StationId { get; set; } = "";
    public DateTime Start { get; set; }
    public DateTime End { get; set; }
    public double CapacityKwh { get; set; }
    public int MaxBookings { get; set; }
    public double ReservedKwh { get; set; }
    public int ReservedCount { get; set; }
    public bool Active { get; set; } = true;
}

public sealed class Reservation
{
    [BsonId] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string ProsumerId { get; set; } = "";
    public string StationId { get; set; } = "";
    public string SlotId { get; set; } = "";
    public DateTime Start { get; set; }
    public DateTime End { get; set; }
    public double EnergyKwh { get; set; }
    public string Direction { get; set; } = "DropOff";
    public string Status { get; set; } = "Pending";
    public string QrNonce { get; set; } = "";
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
    public string? CompletedBy { get; set; }
    public DateTime? CompletedAt { get; set; }
    public double? TransferredKwh { get; set; }
    public int Revision { get; set; }
}

public sealed class AuditEntry
{
    [BsonId] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string ActorId { get; set; } = "";
    public string Action { get; set; } = "";
    public string EntityId { get; set; } = "";
    public DateTime At { get; set; } = DateTime.UtcNow;
}
