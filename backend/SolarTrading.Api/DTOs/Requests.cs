/* SE4040 Smart Solar Microgrid Trading System.
 * Validated API request contracts. Password hashes and QR nonces are never public DTOs.
 */
using System.ComponentModel.DataAnnotations;
using SolarTrading.Api.Models;

namespace SolarTrading.Api.DTOs;

public record LoginRequest([Required, EmailAddress] string Email, [Required] string Password);
public record RegisterRequest(
    [Required, RegularExpression(@"^(?:\d{9}[VvXx]|\d{12})$")] string Nic,
    [Required, StringLength(100, MinimumLength = 2)] string Name,
    [Required, EmailAddress, StringLength(254)] string Email,
    [Required, StringLength(128, MinimumLength = 10)] string Password,
    [Required, StringLength(25)] string Phone,
    [Required, StringLength(300)] string Address);
public record ProfileRequest(
    [Required, StringLength(100, MinimumLength = 2)] string Name,
    [Required, StringLength(25)] string Phone,
    [Required, StringLength(300)] string Address);
public record StaffRequest(
    [Required, StringLength(100, MinimumLength = 2)] string Name,
    [Required, EmailAddress, StringLength(254)] string Email,
    [Required, StringLength(128, MinimumLength = 10)] string Password,
    [Required, RegularExpression("^(Backoffice|GridOperator)$")] string Role);
public record StationRequest(
    [Required, StringLength(100)] string Name,
    [Required, StringLength(300)] string Address,
    [Range(-90, 90)] double Latitude,
    [Range(-180, 180)] double Longitude,
    [Range(0.01, 1000000)] double CapacityKw,
    [Range(1, 10000)] int BatterySlots,
    [Required, StringLength(500)] string Schedule);
public record SlotRequest(DateTimeOffset Start, DateTimeOffset End,
    [Range(0.01, 1000000)] double CapacityKwh, [Range(1, 10000)] int MaxBookings);
public record ReservationRequest([Required] string SlotId,
    [Range(0.01, 1000000)] double EnergyKwh,
    [Required, RegularExpression("^(DropOff|Charging)$")] string Direction,
    string? ProsumerId = null);
public record QrRequest([Required, StringLength(300)] string QrCode);
public record CompleteRequest([Required, StringLength(300)] string QrCode,
    [Range(0.01, 1000000)] double TransferredKwh);
public record UserView(string Id, string? Nic, string Name, string Email, string Phone,
    string Address, string Role, string Status)
{
    // Return only safe account fields to clients.
    public static UserView From(User user) => new(user.Id, user.Nic, user.Name,
        user.Email, user.Phone, user.Address, user.Role, user.Status);
}
public record BookingView(string Id, string ProsumerId, string ProsumerName, string StationId,
    string StationName, string SlotId, DateTime Start, DateTime End, double EnergyKwh,
    string Direction, string Status, DateTime CreatedAt, DateTime? CompletedAt, double? TransferredKwh)
{
    // Join descriptive reference data without exposing verification secrets.
    public static BookingView From(Reservation r, string station, string prosumer) => new(
        r.Id, r.ProsumerId, prosumer, r.StationId, station, r.SlotId, r.Start, r.End,
        r.EnergyKwh, r.Direction, r.Status, r.CreatedAt, r.CompletedAt, r.TransferredKwh);
}
