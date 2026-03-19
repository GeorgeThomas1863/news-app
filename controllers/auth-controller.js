import { recordFailedAttempt, clearAttempts } from "../middleware/rate-limit.js";

export const authController = (req, res) => {
  if (!req.body || !req.body.pw) {
    recordFailedAttempt(req.ip);
    res.json({ success: false, redirect: "/401" });
    return;
  }

  //pw check
  if (req.body.pw !== process.env.ADMIN_PW) {
    recordFailedAttempt(req.ip);
    res.json({ success: false, redirect: "/401" });
    return;
  }

  // auth pw
  clearAttempts(req.ip);
  req.session.authenticated = true;
  res.json({ success: true, redirect: "/admin" });
};
