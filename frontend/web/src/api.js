export const API_URL = (
  import.meta.env.VITE_API_URL || "http://localhost:5080/api"
).replace(/\/$/, "");
export async function request(
  path,
  { method = "GET", body, token, signal } = {},
) {
  const response = await fetch(`${API_URL}${path}`, {
    method,
    signal,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const errors = data?.errors && Object.values(data.errors).flat().join(" ");
    const error = new Error(
      errors ||
        data?.title ||
        (response.status === 401
          ? "Your session expired. Please sign in again."
          : response.status === 429
            ? "Too many attempts. Please wait a minute."
            : "Unable to complete the request."),
    );
    error.status = response.status;
    throw error;
  }
  return data;
}
export const date = (value) =>
  new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
export const localInput = (value) => {
  const d = new Date(value);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
};
