export const buildCollapseContainer = async (inputObj) => {
  if (!inputObj || !inputObj.titleElement || !inputObj.contentElement) return null;
  const { titleElement, contentElement, isExpanded = false, className = "", dataAttribute = "" } = inputObj;

  // Create container
  const collapseContainer = document.createElement("div");
  collapseContainer.className = `collapse-container ${className}`;

  // Create header with arrow and title
  const collapseHeader = document.createElement("div");
  collapseHeader.setAttribute("data-update", dataAttribute);
  collapseHeader.className = "collapse-header";

  const arrow = document.createElement("div");
  arrow.id = "collapse-arrow";
  arrow.className = isExpanded ? "collapse-arrow expanded" : "collapse-arrow";
  arrow.setAttribute("data-update", dataAttribute);

  const existingTitleClasses = titleElement.className || "";
  titleElement.className = existingTitleClasses ? `${existingTitleClasses} collapse-title` : "collapse-title";
  titleElement.setAttribute("data-update", dataAttribute);

  //add arrow / title to header
  collapseHeader.append(arrow, titleElement);

  //below preserves existing classes on content
  const existingClasses = contentElement.className || "";
  const collapseClasses = isExpanded ? "collapse-content" : "collapse-content hidden";
  contentElement.className = existingClasses ? `${existingClasses} ${collapseClasses}` : collapseClasses;

  //add collapse element at end
  collapseContainer.append(collapseHeader, contentElement);

  // CLICK LISTENER HERE
  collapseHeader.addEventListener("click", () => {
    arrow.classList.toggle("expanded");
    contentElement.classList.toggle("hidden");
  });

  return collapseContainer;
};

export const defineCollapseItems = async (inputArray) => {
  if (!inputArray || !inputArray.length) return null;

  for (let i = 0; i < inputArray.length; i++) {
    const collapseElement = inputArray[i];
    const header = collapseElement.querySelector(".collapse-header");
    if (!header) continue;

    header.addEventListener("click", () => {
      // collapse shit
      for (let j = 0; j < inputArray.length; j++) {
        if (i !== j) {
          const otherCollapse = inputArray[j];
          const otherContent = otherCollapse.querySelector(".collapse-content");
          const otherArrow = otherCollapse.querySelector(".collapse-arrow");

          otherContent.classList.add("hidden");
          otherArrow.classList.remove("expanded");
        }
      }
    });
  }
};

export const hideArray = async (inputs) => {
  for (const input of inputs) {
    if (!input) continue;
    input.classList.add("hidden");
  }
};

export const unhideArray = async (inputs) => {
  for (const input of inputs) {
    if (!input) continue;
    input.classList.remove("hidden");
  }
};
