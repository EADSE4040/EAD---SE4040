/* SE4040 Smart Solar Microgrid Trading System.
 * Central time and state rules. UTC instants prevent client timezone bypasses.
 */
namespace SolarTrading.Api.Services;

public sealed class DomainException(int status, string message) : Exception(message)
{
    public int Status { get; } = status;
}

public static class BusinessRules
{
    // Validate the inclusive seven-day scheduling window using server time.
    public static void BookingWindow(DateTime start, DateTime now)
    {
        if (start <= now || start > now.AddDays(7))
            throw new DomainException(400, "Reservations must start in the future within seven days.");
    }

    // Require at least twelve hours' notice before any modification or cancellation.
    public static void Notice(DateTime start, DateTime now)
    {
        if (start < now.AddHours(12))
            throw new DomainException(409, "Changes and cancellations require at least twelve hours' notice.");
    }

    // Prevent changes to terminal reservations.
    public static void Editable(string status)
    {
        if (status is not ("Pending" or "Approved"))
            throw new DomainException(409, "Only pending or approved reservations can be changed.");
    }

    // Enforce finite positive energy to avoid invalid capacity arithmetic.
    public static void Energy(double energy)
    {
        if (!double.IsFinite(energy) || energy <= 0 || energy > 1000000)
            throw new DomainException(400, "Energy must be a positive finite number within the allowed range.");
    }

    // Validate slot intervals and node storage limits.
    public static void Slot(DateTime start, DateTime end, double capacity, int maxBookings,
        int batterySlots, DateTime now)
    {
        Energy(capacity);
        if (start <= now || end <= start || maxBookings < 1 || maxBookings > batterySlots)
            throw new DomainException(400, "Slots need future start/end times and a booking limit within node battery capacity.");
    }
}
