import { sendToBack } from "./util/api-front.js";
import { EYE_OPEN_SVG, EYE_CLOSED_SVG } from "./util/define-things.js";

export const runAuthSubmit = async () => {
  const authPwInput = document.getElementById("auth-pw-input");

  const params = {
    route: "/auth-route",
    pw: authPwInput.value || authPwInput.placeholder,
  };

  try {
    const authData = await sendToBack(params);
    if (!authData || !authData.redirect) return null;

    window.location.href = authData.redirect;
    return authData;
  } catch (e) {
    // console.log("ERROR: " + e.message + "; FUNCTION: " + e.function);
    return null;
  }
};

export const runPwToggle = async () => {
  const pwButton = document.querySelector(".password-toggle-btn");
  const pwInput = document.querySelector(".password-input");

  // console.log(pwButton);
  // console.log(pwInput);
  const currentSvgId = pwButton.querySelector("svg").id;

  if (currentSvgId === "eye-closed-icon") {
    pwButton.innerHTML = EYE_OPEN_SVG;
    pwInput.type = "text";
    return true;
  }

  pwButton.innerHTML = EYE_CLOSED_SVG;
  pwInput.type = "password";
  return true;
};
