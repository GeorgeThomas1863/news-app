import path from "path";

const requireAuth = (req, res, next) => {
  if (req.session.authenticated) {
    next();
  } else {
    res.sendFile(path.join(process.cwd(), "html", "auth.html"));
  }
};

export default requireAuth;
