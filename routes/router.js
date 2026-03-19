import express from "express";

import requireAuth from "../middleware/auth-config.js";
import { authRateLimit } from "../middleware/rate-limit.js";

import { authController } from "../controllers/auth-controller.js";
import { displayMain, display404, display500 } from "../controllers/display-controller.js";

const router = express.Router();

router.post("/auth-route", authController);

router.get("/", requireAuth, displayMain);

router.use(display404);

router.use(display500);

export default router;
