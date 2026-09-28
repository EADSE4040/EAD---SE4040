/* SE4040 Smart Solar Microgrid Trading System.
 * Account lifecycle, password hashing and server-side role enforcement.
 */
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.AspNetCore.Identity;
using Microsoft.IdentityModel.Tokens;
using MongoDB.Driver;
using SolarTrading.Api.DTOs;
using SolarTrading.Api.Models;
using SolarTrading.Api.Repositories;

namespace SolarTrading.Api.Services;

public sealed class AccountService(MongoStore db, IConfiguration config)
{
    private readonly PasswordHasher<User> hasher = new();

    // Authenticate active accounts and issue a signed short-lived role token.
    public async Task<object> Login(LoginRequest input, CancellationToken ct)
    {
        var email = input.Email.Trim().ToLowerInvariant();
        var user = await db.Users.Find(x => x.Email == email).FirstOrDefaultAsync(ct);
        if (user is null || hasher.VerifyHashedPassword(user, user.PasswordHash, input.Password)
            == PasswordVerificationResult.Failed)
            throw new DomainException(401, "Email or password is incorrect.");
        if (user.Status != "Active")
            throw new DomainException(403, "Your account is pending activation or has been deactivated. Contact Backoffice.");
        var expiry = DateTime.UtcNow.AddMinutes(config.GetValue("Jwt:ExpiryMinutes", 120));
        var token = new JwtSecurityToken(config["Jwt:Issuer"], config["Jwt:Audience"],
            [new Claim(ClaimTypes.NameIdentifier, user.Id), new Claim(ClaimTypes.Role, user.Role),
             new Claim("version", user.TokenVersion.ToString())], expires: expiry,
            signingCredentials: new SigningCredentials(new SymmetricSecurityKey(
                Encoding.UTF8.GetBytes(config["Jwt:Key"]!)), SecurityAlgorithms.HmacSha256));
        return new
        {
            token = new JwtSecurityTokenHandler().WriteToken(token),
            expiresAt = expiry,
            user = UserView.From(user)
        };
    }

    // Register a pending prosumer with a normalized NIC as the Mongo primary key.
    public async Task<UserView> Register(RegisterRequest input, bool active, CancellationToken ct)
    {
        var user = new User
        {
            Id = input.Nic.Trim().ToUpperInvariant(),
            Nic = input.Nic.Trim().ToUpperInvariant(),
            Name = input.Name.Trim(),
            Email = input.Email.Trim().ToLowerInvariant(),
            Phone = input.Phone.Trim(),
            Address = input.Address.Trim(),
            Status = active ? "Active" : "Pending"
        };
        user.PasswordHash = hasher.HashPassword(user, input.Password);
        try { await db.Users.InsertOneAsync(user, cancellationToken: ct); }
        catch (MongoWriteException e) when (e.WriteError.Category == ServerErrorCategory.DuplicateKey)
        { throw new DomainException(409, "This NIC or email is already registered."); }
        return UserView.From(user);
    }

    // Create a staff account; caller authorization is enforced by the controller.
    public async Task<UserView> CreateStaff(StaffRequest input, CancellationToken ct)
    {
        var user = new User
        {
            Name = input.Name.Trim(),
            Email = input.Email.Trim().ToLowerInvariant(),
            Role = input.Role,
            Status = "Active"
        };
        user.PasswordHash = hasher.HashPassword(user, input.Password);
        try { await db.Users.InsertOneAsync(user, cancellationToken: ct); }
        catch (MongoWriteException e) when (e.WriteError.Category == ServerErrorCategory.DuplicateKey)
        { throw new DomainException(409, "This email is already registered."); }
        return UserView.From(user);
    }

    // Load an account or return a consistent not-found error.
    public async Task<User> Get(string id, CancellationToken ct) =>
        await db.Users.Find(x => x.Id == id).FirstOrDefaultAsync(ct)
        ?? throw new DomainException(404, "Account not found.");

    // Return safe filtered accounts for administration and operational selection.
    public async Task<List<UserView>> List(string? role, string? status, CancellationToken ct)
    {
        var f = Builders<User>.Filter.Empty;
        if (!string.IsNullOrEmpty(role)) f &= Builders<User>.Filter.Eq(x => x.Role, role);
        if (!string.IsNullOrEmpty(status)) f &= Builders<User>.Filter.Eq(x => x.Status, status);
        return (await db.Users.Find(f).SortBy(x => x.Name).Limit(500).ToListAsync(ct))
            .Select(UserView.From).ToList();
    }

    // Update mutable profile data without allowing NIC, role, email or status escalation.
    public async Task<UserView> Profile(string id, ProfileRequest input, CancellationToken ct)
    {
        var user = await db.Users.FindOneAndUpdateAsync<User>(x => x.Id == id,
            Builders<User>.Update.Set(x => x.Name, input.Name.Trim()).Set(x => x.Phone, input.Phone.Trim())
                .Set(x => x.Address, input.Address.Trim()),
            new FindOneAndUpdateOptions<User> { ReturnDocument = ReturnDocument.After }, ct);
        return UserView.From(user ?? throw new DomainException(404, "Account not found."));
    }

    // Activate or deactivate accounts atomically and invalidate every old access token.
    public async Task<UserView> SetStatus(string id, string status, string actor, CancellationToken ct)
    {
        if (id == actor) throw new DomainException(409, "Administrators cannot deactivate their own account here.");
        return await db.Transaction(async (session, token) =>
        {
            var user = await db.Users.FindOneAndUpdateAsync<User>(session, x => x.Id == id,
                Builders<User>.Update.Set(x => x.Status, status).Inc(x => x.TokenVersion, 1),
                new FindOneAndUpdateOptions<User> { ReturnDocument = ReturnDocument.After }, token)
                ?? throw new DomainException(404, "Account not found.");
            await db.Log(session, actor, "Account:" + status, id, token);
            return UserView.From(user);
        }, ct);
    }

    // Allow a prosumer to deactivate their own account and revoke existing sessions.
    public async Task DeactivateSelf(string id, CancellationToken ct)
    {
        await db.Users.UpdateOneAsync(x => x.Id == id && x.Role == Roles.Prosumer,
            Builders<User>.Update.Set(x => x.Status, "Deactivated").Inc(x => x.TokenVersion, 1),
            cancellationToken: ct);
    }
}
