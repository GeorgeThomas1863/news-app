import { buildAuthForm } from "./forms/auth-form.js";

const authElement = document.getElementById("auth-element");

export const buildAuthDisplay = async () => {
  if (!authElement) return null;

  try {
    const authForm = await buildAuthForm();
    if (!authForm) {
      const error = new Error("FAILED TO BUILD AUTH FORM");
      error.function = "buildAuthDisplay";
      throw error;
    }

    authElement.appendChild(authForm);
  } catch (e) {
    // console.log("ERROR: " + e.message + "; FUNCTION: " + e.function);
  }
};

buildAuthDisplay();