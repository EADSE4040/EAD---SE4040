/* SE4040 Smart Solar Microgrid Trading System.
 * Application composition, validated JWT authentication, error responses and API routing.
 */
using System.Security.Claims;
using System.Text;
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.IdentityModel.Tokens;
using MongoDB.Driver;
using SolarTrading.Api.Repositories;
using SolarTrading.Api.Services;

var builder = WebApplication.CreateBuilder(args);
builder.Configuration.AddJsonFile("appsettings.Local.json", optional: true).AddEnvironmentVariables();
foreach (var key in new[] { "Jwt:Key", "Qr:Key" })
    if (Encoding.UTF8.GetByteCount(builder.Configuration[key] ?? "") < 32)
        throw new InvalidOperationException($"Configure {key} with an independent random secret of at least 32 bytes.");
builder.Services.AddControllers();
builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddSingleton<MongoStore>();
builder.Services.AddScoped<AccountService>();
builder.Services.AddScoped<GridService>();
builder.Services.AddScoped<ReservationService>();
builder.Services.AddHostedService<DatabaseInitializer>();
builder.Services.AddHostedService<ReservationExpiryService>();
builder.Services.AddCors(options => options.AddDefaultPolicy(policy => policy
    .WithOrigins(builder.Configuration.GetSection("Cors:Origins").Get<string[]>() ?? [])
    .AllowAnyHeader().AllowAnyMethod()));
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme).AddJwtBearer(options =>
{
    // Validate issuer, audience, signature, expiry and current account state for every authenticated request.
    options.TokenValidationParameters = new TokenValidationParameters
    {
        ValidateIssuer = true, ValidateAudience = true, ValidateIssuerSigningKey = true,
        ValidateLifetime = true, ValidIssuer = builder.Configuration["Jwt:Issuer"],
        ValidAudience = builder.Configuration["Jwt:Audience"], ClockSkew = TimeSpan.FromSeconds(15),
        IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(builder.Configuration["Jwt:Key"]!))
    };
    options.Events = new JwtBearerEvents { OnTokenValidated = async context =>
    {
        // Re-check activation and token version so deactivation immediately invalidates old sessions.
        var id = context.Principal?.FindFirstValue(ClaimTypes.NameIdentifier);
        var version = context.Principal?.FindFirstValue("version");
        var db = context.HttpContext.RequestServices.GetRequiredService<MongoStore>();
        var user = await db.Users.Find(x => x.Id == id).FirstOrDefaultAsync(context.HttpContext.RequestAborted);
        if (user is null || user.Status != "Active" || user.TokenVersion.ToString() != version)
            context.Fail("Account is inactive or this session has been revoked.");
    } };
});
builder.Services.AddAuthorization();
builder.Services.AddRateLimiter(options =>
{
    // Partition login limits by the connecting client; do not trust unconfigured forwarded headers.
    options.RejectionStatusCode = 429;
    options.AddPolicy("auth", context => RateLimitPartition.GetFixedWindowLimiter(
        context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
        _ => new FixedWindowRateLimiterOptions { PermitLimit = 20, Window = TimeSpan.FromMinutes(1), QueueLimit = 0 }));
});
var app = builder.Build();
app.Use(async (context, next) =>
{
    // Return consistent safe Problem Details instead of exposing database or stack-trace information.
    try { await next(context); }
    catch (DomainException e)
    { await Results.Problem(statusCode: e.Status, title: e.Message).ExecuteAsync(context); }
    catch (MongoException e)
    {
        app.Logger.LogError(e, "MongoDB operation failed");
        await Results.Problem(statusCode: 503, title: "The data service is unavailable. Please try again.").ExecuteAsync(context);
    }
    catch (Exception e) when (e is not OperationCanceledException)
    {
        app.Logger.LogError(e, "Unhandled request failure");
        await Results.Problem(statusCode: 500, title: "An unexpected error occurred.").ExecuteAsync(context);
    }
});
app.Use(async (context, next) =>
{
    // Apply baseline browser security headers to API responses.
    context.Response.Headers.XContentTypeOptions = "nosniff";
    context.Response.Headers["Referrer-Policy"] = "no-referrer";
    await next(context);
});
app.UseCors();
app.UseAuthentication();
app.UseAuthorization();
app.UseRateLimiter();
app.MapControllers();
app.MapGet("/api/health", async (MongoStore db, CancellationToken ct) =>
{
    // Verify actual database reachability rather than reporting a static healthy flag.
    await db.Database.RunCommandAsync<MongoDB.Bson.BsonDocument>(new MongoDB.Bson.BsonDocument("ping", 1), cancellationToken: ct);
    return Results.Ok(new { status = "healthy", database = "connected", utc = DateTime.UtcNow });
});
app.Run();
