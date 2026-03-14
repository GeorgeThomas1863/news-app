import express from "express";

import requireAuth from "../middleware/auth-config.js";
import { authRateLimit } from "../middleware/rate-limit.js";

import { displayMain, display404, display500 } from "../controllers/display-controller.js";

const router = express.Router();

router.get("/", displayMain);

router.use(display404);

router.use(display500);

export default router;
