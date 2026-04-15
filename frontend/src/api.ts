function authHeader(): HeadersInit {
  const t = localStorage.getItem("skypipe_token");
  const h: Record<string, string> = { Accept: "application/json" };
  if (t) h.Authorization = `Bearer ${t}`;
  return h;
}

export async function login(username: string, password: string) {
  const r = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) throw new Error((await r.json()).detail || "Login failed");
  const data = await r.json();
  localStorage.setItem("skypipe_token", data.access_token);
  return data;
}

export async function me() {
  const r = await fetch("/auth/me", { headers: authHeader() });
  if (!r.ok) throw new Error("Session expired");
  return r.json();
}

export async function architecture() {
  const r = await fetch("/v1/architecture", { headers: authHeader() });
  if (!r.ok) throw new Error("Failed to load architecture");
  return r.json();
}

export async function capabilities() {
  const r = await fetch("/v1/capabilities", { headers: authHeader() });
  if (!r.ok) throw new Error("Failed to load capabilities");
  return r.json();
}

export async function createJob(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const t = localStorage.getItem("skypipe_token");
  const r = await fetch("/v1/jobs", {
    method: "POST",
    headers: t ? { Authorization: `Bearer ${t}` } : {},
    body: fd,
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<{ job_id: string; status: string }>;
}

export async function getJob(jobId: string) {
  const r = await fetch(`/v1/jobs/${jobId}`, { headers: authHeader() });
  if (!r.ok) throw new Error("Job not found");
  return r.json();
}

export async function getStory(jobId: string) {
  const r = await fetch(`/v1/jobs/${jobId}/story`, { headers: authHeader() });
  if (!r.ok) throw new Error("Story not found");
  return r.json();
}

export async function getResults(jobId: string) {
  const r = await fetch(`/v1/jobs/${jobId}/results`, { headers: authHeader() });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export function logout() {
  localStorage.removeItem("skypipe_token");
}
