function toHex(buffer) {
  return Array.from(new Uint8Array(buffer))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function sha256(message) {
  const bytes = new TextEncoder().encode(message);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return toHex(digest);
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function fingerprintCanvas() {
  const canvas = document.createElement("canvas");
  canvas.width = 280;
  canvas.height = 60;
  const ctx = canvas.getContext("2d");
  if (!ctx) return "canvas-na";

  ctx.textBaseline = "top";
  ctx.font = "16px Arial";
  ctx.fillStyle = "#f60";
  ctx.fillRect(0, 0, 280, 60);
  ctx.fillStyle = "#069";
  ctx.fillText("DriveGo ACInt", 10, 18);
  ctx.fillStyle = "rgba(102, 204, 0, 0.7)";
  ctx.fillText(navigator.userAgent, 10, 34);
  return canvas.toDataURL();
}

function fingerprintWebGL() {
  try {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
    if (!gl) return "webgl-na";

    const debugInfo = gl.getExtension("WEBGL_debug_renderer_info");
    const vendor = debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR);
    const renderer = debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
    return `${vendor || "unknown"}::${renderer || "unknown"}`;
  } catch {
    return "webgl-error";
  }
}

function buildFingerprint() {
  return {
    hc: navigator.hardwareConcurrency || 1,
    mem: navigator.deviceMemory || 0,
    lang: navigator.language || "unknown",
    tz: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
    sw: screen.width || 0,
    sh: screen.height || 0,
    cd: screen.colorDepth || 0,
    touch: navigator.maxTouchPoints || 0,
    canvas: fingerprintCanvas(),
    webgl: fingerprintWebGL(),
  };
}

let cachedAcInt = null;
let cachedAcIntAt = 0;

export async function getAcInt(force = false) {
  const now = Date.now();
  if (cachedAcInt && !force && now - cachedAcIntAt < 120000) return cachedAcInt;

  const t0 = Date.now();
  const t1 = crypto.getRandomValues(new Uint32Array(1))[0];
  const t2 = randomInt(31, 60);
  const fingerprint = buildFingerprint();
  const timeHash = await sha256(`${t0}:${t1}:${t2}`);

  cachedAcInt = [timeHash, [t0, t1, t2, [fingerprint]]];
  cachedAcIntAt = now;
  return cachedAcInt;
}

function normalizeBody(body) {
  if (body == null) return undefined;
  if (typeof body === "string") return body;
  return JSON.stringify(body);
}

function getCookie(name) {
  const prefix = `${name}=`;
  const cookie = document.cookie.split(";").map((item) => item.trim()).find((item) => item.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : "";
}

async function parseJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.message || data.detail || "İşlem başarısız.");
  }
  return data;
}

export async function secureFetch(url, options = {}) {
  const {
    method = "GET",
    body = undefined,
    headers = {},
    includeAcIntHeader = true,
    includeAcIntBody = false,
  } = options;

  const finalHeaders = { ...headers };
  let finalBody = normalizeBody(body);

  if (includeAcIntHeader || includeAcIntBody) {
    const acInt = await getAcInt();
    if (includeAcIntHeader) {
      finalHeaders["X-ACINT"] = JSON.stringify(acInt);
    }
    if (includeAcIntBody) {
      const parsed = finalBody ? JSON.parse(finalBody) : {};
      parsed.ACInt = acInt;
      finalBody = JSON.stringify(parsed);
    }
  }

  if (finalBody !== undefined) {
    finalHeaders["Content-Type"] = "application/json";
  }

  if (method !== "GET") {
    const csrfToken = getCookie("csrf_token");
    if (csrfToken) finalHeaders["X-CSRF-Token"] = csrfToken;
  }

  const response = await fetch(url, {
    method,
    credentials: "include",
    headers: finalHeaders,
    body: method === "GET" ? undefined : finalBody,
  });

  return parseJson(response);
}
