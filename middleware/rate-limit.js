const attempts = new Map();
const MAX_ATTEMPTS = 10;
const WINDOW_MS = 15 * 60 * 1000; // 15 minutes

function pruneExpired() {
  const now = Date.now();
  for (const [ip, record] of attempts) {
    if (now - record.windowStart > WINDOW_MS) attempts.delete(ip);
  }
}

export const authRateLimit = (req, res, next) => {
  pruneExpired();
  const ip = req.ip;
  const record = attempts.get(ip);
  if (record && record.count >= MAX_ATTEMPTS) {
    return res.status(429).json({ success: false, message: "Too many attempts. Try again later." });
  }
  next();
};

export const recordFailedAttempt = (ip) => {
  const now = Date.now();
  const record = attempts.get(ip);
  if (!record || now - record.windowStart > WINDOW_MS) {
    attempts.set(ip, { count: 1, windowStart: now });
  } else {
    record.count += 1;
  }
};

export const clearAttempts = (ip) => attempts.delete(ip);
