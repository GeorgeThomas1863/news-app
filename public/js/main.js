const displayElement = document.getElementById("display-element");

export const buildMainDisplay = async () => {
  if (!displayElement) return null;

  const data = await buildMainForm();

  displayElement.append(data);

  return true;
};

buildMainDisplay();
