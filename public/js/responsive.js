import { runPwToggle, runAuthSubmit } from "./run.js";

const authElement = document.getElementById("auth-element");
const displayElement = document.getElementById("display-element");

export const clickHandler = async (e) => {
  // e.preventDefault();

  const clickElement = e.target;
  const clickId = clickElement.id;
  const clickType = clickElement.getAttribute("data-label");

  console.log("CLICK ID");
  console.log(clickId);
  console.log("CLICK TYPE");
  console.log(clickType);

  if (clickType === "pwToggle") await runPwToggle();
  if (clickType === "auth-submit") await runAuthSubmit();
};

export const keyHandler = async (e) => {
  if (e.key !== "Enter") return null;
  e.preventDefault();

  const keyElement = e.target;
  const keyId = keyElement.id;

  console.log("KEY HANDLER");
  console.log(keyId);

  if (keyId === "auth-pw-input") await runAuthSubmit();

  return true;
};

if (authElement) {
  authElement.addEventListener("click", clickHandler);
  authElement.addEventListener("keydown", keyHandler);
}

if (displayElement) {
  displayElement.addEventListener("click", clickHandler);
  // displayElement.addEventListener("change", changeHandler);
  // displayElement.addEventListener("keydown", keyHandler);
}
