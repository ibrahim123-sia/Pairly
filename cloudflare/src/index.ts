/**
 * Pairly on Cloudflare.
 *
 * - Static assets: the React build (frontend/dist) is served directly by
 *   Cloudflare; unknown paths fall back to index.html (wrangler.jsonc).
 * - /api/*, /docs, /openapi.json: run this Worker, which forwards the request
 *   to the FastAPI container (backend/Dockerfile). One named instance is used,
 *   so in-memory caches stay warm while it is awake.
 * - Cron Trigger: asks the API to run scheduled store jobs that are due.
 */
import { Container, getContainer } from "@cloudflare/containers";

export interface Env {
  PAIRLY_API: DurableObjectNamespace<PairlyApi>;

  // Plain settings (wrangler.jsonc "vars")
  APP_ENV: string;
  APP_DEBUG: string;
  SCHEDULER_MODE: string;
  SEED_DEMO: string;
  MAIL_SUPPRESS_SEND: string;
  AI_DAILY_REQUEST_LIMIT: string;
  R2_BUCKET: string;
  FRONTEND_URL: string;

  // Secrets (wrangler secret put, or the GitHub deploy workflow)
  DATABASE_URL: string;
  SECRET_KEY: string;
  JWT_SECRET_KEY: string;
  SUPER_ADMIN_EMAIL: string;
  SUPER_ADMIN_PASSWORD: string;
  R2_ACCOUNT_ID: string;
  R2_ACCESS_KEY_ID: string;
  R2_SECRET_ACCESS_KEY: string;
  CRON_SECRET: string;
  GROQ_API_KEY?: string;
  GEMINI_API_KEY?: string;
  // Optional: real email sending (also set MAIL_SUPPRESS_SEND to "false")
  MAIL_SERVER?: string;
  MAIL_PORT?: string;
  MAIL_USERNAME?: string;
  MAIL_PASSWORD?: string;
  MAIL_DEFAULT_SENDER?: string;
}

/** Settings passed to the FastAPI container as environment variables. */
const CONTAINER_ENV: (keyof Env)[] = [
  "APP_ENV",
  "APP_DEBUG",
  "SCHEDULER_MODE",
  "SEED_DEMO",
  "MAIL_SUPPRESS_SEND",
  "AI_DAILY_REQUEST_LIMIT",
  "R2_BUCKET",
  "FRONTEND_URL",
  "DATABASE_URL",
  "SECRET_KEY",
  "JWT_SECRET_KEY",
  "SUPER_ADMIN_EMAIL",
  "SUPER_ADMIN_PASSWORD",
  "R2_ACCOUNT_ID",
  "R2_ACCESS_KEY_ID",
  "R2_SECRET_ACCESS_KEY",
  "CRON_SECRET",
  "GROQ_API_KEY",
  "GEMINI_API_KEY",
  "MAIL_SERVER",
  "MAIL_PORT",
  "MAIL_USERNAME",
  "MAIL_PASSWORD",
  "MAIL_DEFAULT_SENDER",
];

const API_PORT = 5000;
const INSTANCE_NAME = "pairly-api";
// A cold start runs database migrations and imports pandas before the port
// opens; the library's 20 s default is too short for that.
const COLD_START_TIMEOUT_MS = 120_000;

export class PairlyApi extends Container<Env> {
  defaultPort = API_PORT;
  sleepAfter = "10m";

  constructor(ctx: DurableObjectState<{}>, env: Env) {
    super(ctx, env);
    const vars: Record<string, string> = {};
    for (const key of CONTAINER_ENV) {
      const value = env[key];
      if (typeof value === "string" && value !== "") vars[key] = value;
    }
    this.envVars = vars;
  }

  override onError(error: unknown) {
    console.error("Pairly API container error:", error);
    throw error;
  }
}

async function api(env: Env) {
  const stub = getContainer(env.PAIRLY_API, INSTANCE_NAME);
  await stub.startAndWaitForPorts({
    ports: API_PORT,
    cancellationOptions: { portReadyTimeoutMS: COLD_START_TIMEOUT_MS },
  });
  return stub;
}

export default {
  // Only API paths reach the Worker (assets.run_worker_first); everything
  // else is a static file or the single-page app.
  async fetch(request, env): Promise<Response> {
    try {
      return await (await api(env)).fetch(request);
    } catch (error) {
      console.error("Could not reach the Pairly API:", error);
      return Response.json(
        { detail: "The Pairly API is starting or unavailable. Please try again in a minute." },
        { status: 503, headers: { "Retry-After": "30" } },
      );
    }
  },

  async scheduled(_controller, env, ctx): Promise<void> {
    if (!env.CRON_SECRET) return;
    ctx.waitUntil(
      (async () => {
        const res = await (await api(env)).fetch(
          new Request("http://pairly-api/api/internal/scheduled-jobs/run", {
            method: "POST",
            headers: { "X-Cron-Secret": env.CRON_SECRET },
          }),
        );
        console.log("Scheduled jobs check:", res.status, await res.text());
      })(),
    );
  },
} satisfies ExportedHandler<Env>;
