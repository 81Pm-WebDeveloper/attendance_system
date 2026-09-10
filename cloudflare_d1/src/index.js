const MAX_EVENTS = 1000;

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true, service: "attendance-d1-backup" });
    }
    if (request.method !== "POST" || url.pathname !== "/raw-attendance-events") {
      return json({ error: "Not found" }, 404);
    }
    if (!env.BACKUP_TOKEN || request.headers.get("authorization") !== `Bearer ${env.BACKUP_TOKEN}`) {
      return json({ error: "Unauthorized" }, 401);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "Request body must be valid JSON" }, 400);
    }
    if (!Array.isArray(body.events) || body.events.length === 0 || body.events.length > MAX_EVENTS) {
      return json({ error: `events must contain 1-${MAX_EVENTS} items` }, 400);
    }

    // The collector reports its connector for diagnostics.  Dedicated OC and
    // CEBU Worker URLs each have their own DB binding, so this Worker always
    // writes to its own DB binding.
    const connector = String(body.connector || "primary").toLowerCase();

    const statements = [];
    for (const event of body.events) {
      if (!event || typeof event !== "object" || !event.source_hash || !event.employee_id ||
          !event.device_id || !event.event_timestamp || !event.raw_json ||
          !Number.isInteger(event.biometric_uid) || event.biometric_uid < 0) {
        return json({ error: "Each raw event requires source_hash, device_id, biometric_uid, employee_id, event_timestamp, and raw_json; biometric_uid must be a non-negative integer" }, 400);
      }
      statements.push(env.DB.prepare(`
        INSERT OR IGNORE INTO attendance_raw_events
          (source_hash, device_id, biometric_uid, employee_id, event_timestamp, punch, status, verify_type, workcode, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).bind(
        String(event.source_hash), String(event.device_id), event.biometric_uid, String(event.employee_id), String(event.event_timestamp),
        event.punch ?? null, event.status ?? null, event.verify_type ?? null, event.workcode ?? null,
        String(event.raw_json),
      ));
    }

    try {
      const results = await env.DB.batch(statements);
      const inserted = results.reduce((count, result) => count + (result.meta?.changes || 0), 0);
      return json({ ok: true, connector, received: body.events.length, inserted });
    } catch (error) {
      console.error("D1 backup insert failed", error);
      return json({ error: "D1 insert failed" }, 500);
    }
  },
};
