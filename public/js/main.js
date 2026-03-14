import { buildMainForm } from "./forms/main-form.js";
import { SAMPLE_DATA } from "./util/sample.js";

const displayElement = document.getElementById("display-element");

export const buildMainDisplay = async () => {
  if (!displayElement) return null;

  //GET DATA HERE

  const form = await buildMainForm(SAMPLE_DATA);

  displayElement.append(form);

  return true;
};

buildMainDisplay();

