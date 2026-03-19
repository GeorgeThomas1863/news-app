// import { EYE_CLOSED_SVG } from "../util/define-things.js";

// const displayElement = document.getElementById("display-element");

// export const unhideAdminAuthModal = async () => {
//   let modal = document.getElementById("admin-auth-modal-overlay");

//   if (!modal) {
//     modal = await buildAdminAuthModal();
//     displayElement.append(modal);
//   }

//   modal.classList.add("active");

//   // Focus the input
//   const input = document.getElementById("admin-auth-modal-input");
//   if (input) input.focus();

//   return true;
// };

// export const hideAdminAuthModal = async () => {
//   const modal = document.getElementById("admin-auth-modal-overlay");
//   if (!modal) return;

//   modal.classList.remove("active");

//   // Clear input
//   const input = document.getElementById("admin-auth-modal-input");
//   if (input) input.value = "";

//   return true;
// };

// // modal.js
// export const buildAdminAuthModal = async () => {
//   const modalOverlay = document.createElement("div");
//   modalOverlay.id = "admin-auth-modal-overlay";
//   modalOverlay.className = "modal-overlay";

//   const modalContent = document.createElement("div");
//   modalContent.className = "modal-content";

//   const modalTitle = document.createElement("h2");
//   modalTitle.textContent = "⚠️ Authorization Required to Nuke Ohio ⚠️";
//   modalTitle.className = "modal-title";

//   const pwWrapper = document.createElement("div");
//   pwWrapper.className = "password-input-wrapper";

//   const pwInput = document.createElement("input");
//   pwInput.type = "password";
//   pwInput.id = "admin-auth-modal-input";
//   pwInput.className = "password-input";
//   pwInput.placeholder = "Enter admin password";

//   const toggleButton = document.createElement("button");
//   toggleButton.type = "button";
//   toggleButton.className = "password-toggle-btn";
//   toggleButton.setAttribute("data-label", "pwToggle");
//   toggleButton.innerHTML = EYE_CLOSED_SVG;

//   pwWrapper.append(pwInput, toggleButton);

//   const buttonWrapper = document.createElement("div");
//   buttonWrapper.className = "modal-button-wrapper";

//   const submitButton = document.createElement("button");
//   submitButton.id = "admin-auth-modal-submit";
//   submitButton.className = "btn-submit";
//   submitButton.textContent = "AUTHORIZE";
//   submitButton.setAttribute("data-label", "admin-auth-modal-submit");

//   const cancelButton = document.createElement("button");
//   cancelButton.id = "admin-auth-modal-cancel";
//   cancelButton.className = "btn-cancel";
//   cancelButton.textContent = "CANCEL";
//   cancelButton.setAttribute("data-label", "admin-auth-modal-cancel");

//   buttonWrapper.append(cancelButton, submitButton);

//   modalContent.append(modalTitle, pwWrapper, buttonWrapper);
//   modalOverlay.append(modalContent);

//   return modalOverlay;
// };
