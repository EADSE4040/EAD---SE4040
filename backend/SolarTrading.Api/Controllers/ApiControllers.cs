/* SE4040 Smart Solar Microgrid Trading System.
 * Thin REST controllers delegate business decisions to the central services.
 */
using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using SolarTrading.Api.DTOs;
using SolarTrading.Api.Models;
using SolarTrading.Api.Services;

namespace SolarTrading.Api.Controllers;

[ApiController]
public abstract class ApiController : ControllerBase
{
    protected string Actor => User.FindFirstValue(ClaimTypes.NameIdentifier)!;
    protected string Role => User.FindFirstValue(ClaimTypes.Role)!;
}

[Route("api/auth")]
public sealed class AuthController(AccountService service) : ApiController
{
    // Authenticate active users under a per-client rate limit.
    [HttpPost("login"), EnableRateLimiting("auth")]
    public Task<object> Login(LoginRequest input, CancellationToken ct) => service.Login(input, ct);

    // Register a new pending account; activation requires Backoffice review.
    [HttpPost("register"), EnableRateLimiting("auth")]
    public Task<UserView> Register(RegisterRequest input, CancellationToken ct) => service.Register(input, false, ct);

    // Refresh the client's safe account view from server data.
    [HttpGet("me"), Authorize]
    public async Task<UserView> Me(CancellationToken ct) => UserView.From(await service.Get(Actor, ct));

    // Edit the authenticated user's mutable profile fields.
    [HttpPut("me"), Authorize]
    public Task<UserView> Profile(ProfileRequest input, CancellationToken ct) => service.Profile(Actor, input, ct);

    // Deactivate the authenticated prosumer and invalidate their sessions.
    [HttpPost("me/deactivate"), Authorize(Roles = Roles.Prosumer)]
    public async Task<IActionResult> Deactivate(CancellationToken ct)
    { await service.DeactivateSelf(Actor, ct); return NoContent(); }
}

[Route("api/users"), Authorize(Roles = Roles.Staff)]
public sealed class UsersController(AccountService service) : ApiController
{
    // List users, restricting operational callers to prosumer records.
    [HttpGet]
    public Task<List<UserView>> List(string? role, string? status, CancellationToken ct) =>
        service.List(Role == Roles.Operator ? Roles.Prosumer : role, status, ct);

    // Create a web staff account as Backoffice.
    [HttpPost("staff"), Authorize(Roles = Roles.Backoffice)]
    public Task<UserView> Staff(StaffRequest input, CancellationToken ct) => service.CreateStaff(input, ct);

    // Create an active prosumer from Backoffice administration.
    [HttpPost("prosumers"), Authorize(Roles = Roles.Backoffice)]
    public Task<UserView> Prosumer(RegisterRequest input, CancellationToken ct) => service.Register(input, true, ct);

    // Update a prosumer profile as Backoffice.
    [HttpPut("{id}"), Authorize(Roles = Roles.Backoffice)]
    public async Task<UserView> Profile(string id, ProfileRequest input, CancellationToken ct)
    {
        if ((await service.Get(id, ct)).Role != Roles.Prosumer)
            throw new DomainException(400, "Use self-service profile editing for staff accounts.");
        return await service.Profile(id, input, ct);
    }

    // Activate pending accounts or reactivate deactivated accounts as Backoffice only.
    [HttpPost("{id}/activate"), Authorize(Roles = Roles.Backoffice)]
    public Task<UserView> Activate(string id, CancellationToken ct) => service.SetStatus(id, "Active", Actor, ct);

    // Deactivate an account and revoke its existing JWT sessions.
    [HttpPost("{id}/deactivate"), Authorize(Roles = Roles.Backoffice)]
    public Task<UserView> Deactivate(string id, CancellationToken ct) => service.SetStatus(id, "Deactivated", Actor, ct);
}

[Route("api/stations"), Authorize]
public sealed class StationsController(GridService service) : ApiController
{
    // Serve persisted station coordinates and specifications to every authenticated role.
    [HttpGet]
    public Task<List<Station>> List(bool includeInactive, CancellationToken ct) =>
        service.Stations(includeInactive && Role != Roles.Prosumer, ct);

    // Restrict new node registration to system administrators.
    [HttpPost, Authorize(Roles = Roles.Backoffice)]
    public Task<Station> Create(StationRequest input, CancellationToken ct) => service.Create(input, ct);

    // Allow staff to update node information and operational schedules.
    [HttpPut("{id}"), Authorize(Roles = Roles.Staff)]
    public Task<Station> Update(string id, StationRequest input, CancellationToken ct) => service.Update(id, input, Actor, ct);

    // Deactivate a node only when it has no active reservations.
    [HttpPost("{id}/deactivate"), Authorize(Roles = Roles.Backoffice)]
    public Task<bool> Deactivate(string id, CancellationToken ct) => service.Active(id, false, Actor, ct);

    // Reactivate an archived node without changing its reservation history.
    [HttpPost("{id}/activate"), Authorize(Roles = Roles.Backoffice)]
    public Task<bool> Activate(string id, CancellationToken ct) => service.Active(id, true, Actor, ct);

    // Publish a battery/energy trading slot on an active station.
    [HttpPost("{id}/slots"), Authorize(Roles = Roles.Staff)]
    public Task<EnergySlot> Slot(string id, SlotRequest input, CancellationToken ct) => service.CreateSlot(id, input, Actor, ct);
}

[Route("api/slots"), Authorize]
public sealed class SlotsController(GridService service) : ApiController
{
    // List future operational slots, with optional station filtering.
    [HttpGet]
    public Task<List<EnergySlot>> List(string? stationId, bool includePast, CancellationToken ct) =>
        service.Slots(stationId, includePast && Role != Roles.Prosumer, ct);

    // Update a published slot before any capacity is reserved.
    [HttpPut("{id}"), Authorize(Roles = Roles.Staff)]
    public Task<EnergySlot> Update(string id, SlotRequest input, CancellationToken ct) => service.UpdateSlot(id, input, Actor, ct);

    // Archive an unreserved slot; preserve history references.
    [HttpDelete("{id}"), Authorize(Roles = Roles.Staff)]
    public Task<bool> Delete(string id, CancellationToken ct) => service.DeleteSlot(id, Actor, ct);
}

[Route("api/reservations"), Authorize]
public sealed class ReservationsController(ReservationService service) : ApiController
{
    // Return filtered server data and enforce prosumer ownership in the service.
    [HttpGet]
    public Task<object> List(string? status, string? search, DateTimeOffset? from, DateTimeOffset? to,
        int page = 1, int pageSize = 25, CancellationToken ct = default) =>
        service.List(Actor, Role, status, search, from, to, page, pageSize, ct);

    // Return live operational counts from the central service.
    [HttpGet("dashboard")]
    public Task<object> Dashboard(CancellationToken ct) => service.Dashboard(Actor, Role, ct);

    // Create a booking for self or a selected active prosumer.
    [HttpPost]
    public Task<BookingView> Create(ReservationRequest input, CancellationToken ct) => service.Create(input, Actor, Role, ct);

    // Modify a booking through the service's notice and capacity rules.
    [HttpPut("{id}")]
    public Task<BookingView> Update(string id, ReservationRequest input, CancellationToken ct) => service.Update(id, input, Actor, Role, ct);

    // Cancel a booking with the minimum notice enforced server-side.
    [HttpPost("{id}/cancel")]
    public Task<BookingView> Cancel(string id, CancellationToken ct) => service.Cancel(id, Actor, Role, ct);

    // Approve a pending energy request as an operational staff member.
    [HttpPost("{id}/approve"), Authorize(Roles = Roles.Staff)]
    public Task<BookingView> Approve(string id, CancellationToken ct) => service.Decide(id, true, Actor, ct);

    // Reject a pending energy request and release reserved capacity.
    [HttpPost("{id}/reject"), Authorize(Roles = Roles.Staff)]
    public Task<BookingView> Reject(string id, CancellationToken ct) => service.Decide(id, false, Actor, ct);

    // Retrieve the signed QR dispatch payload for an approved owned booking.
    [HttpGet("{id}/qr")]
    public Task<object> Qr(string id, CancellationToken ct) => service.Qr(id, Actor, Role, ct);

    // Verify a camera scan against live server records.
    [HttpPost("verify"), Authorize(Roles = Roles.Staff)]
    public Task<BookingView> Verify(QrRequest input, CancellationToken ct) => service.Verify(input.QrCode, ct);

    // Finalize the verified energy transfer once, during its scheduled slot.
    [HttpPost("complete"), Authorize(Roles = Roles.Staff)]
    public Task<BookingView> Complete(CompleteRequest input, CancellationToken ct) => service.Complete(input, Actor, ct);
}
