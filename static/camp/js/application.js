const form = document.querySelector("[data-application-form]");

if (form) {
  const modelContainer = document.querySelector("[data-model-form]");
  const categoryInputs = document.querySelectorAll('input[name="category"]');
  const talentNotice = document.querySelector("[data-talent-notice]");
  const updateCategory = () => {
    const selected = document.querySelector('input[name="category"]:checked');
    if (modelContainer) modelContainer.hidden = selected?.value !== "model";
    if (talentNotice) talentNotice.hidden = selected?.value !== "talent";
  };
  categoryInputs.forEach((input) => input.addEventListener("change", updateCategory));
  if (modelContainer) updateCategory();

  const genderInput = form.querySelector('select[name="gender"]');
  const updateSizes = (preserveErrors = false) => {
    form.querySelectorAll("[data-female-size]").forEach((container) => {
      const visible = genderInput?.value === "female" || (preserveErrors && container.classList.contains("has-error"));
      container.hidden = !visible;
      const input = container.querySelector("input");
      if (input) {
        input.required = visible;
        if (!visible) input.value = "";
      }
    });
  };
  genderInput?.addEventListener("change", () => updateSizes());
  updateSizes(true);
  const photoInputs = [...form.querySelectorAll('input[type="file"]')];
  const ageCategoryInput = form.querySelector('select[name="age_category"]');
  const kidsApplicationNotice = document.querySelector(
    "#kids-application-notice",
  );
  const modellingExperienceInput = form.querySelector(
    'select[name="has_modelling_experience"]',
  );
  const modellingExperienceDetails = form.querySelector(
    "[data-modelling-experience-details]",
  );

  const updateKidsApplicationNotice = () => {
    if (ageCategoryInput && kidsApplicationNotice) {
      kidsApplicationNotice.hidden = ageCategoryInput.value !== "kids";
    }
  };

  ageCategoryInput?.addEventListener("change", updateKidsApplicationNotice);
  updateKidsApplicationNotice();

  const updateModellingExperienceDetails = (preserveErrors = false) => {
    if (modellingExperienceDetails && modellingExperienceInput) {
      modellingExperienceDetails.hidden =
        modellingExperienceInput.value !== "yes" && !(preserveErrors && modellingExperienceDetails.classList.contains("has-error"));
    }
  };

  modellingExperienceInput?.addEventListener(
    "change",
    () => updateModellingExperienceDetails(),
  );
  updateModellingExperienceDetails(true);

  const validatePhotoInputs = () => {
    photoInputs.forEach((input) => {
      const file = input.files?.[0];
      let error = "";
      if (file && !["image/jpeg", "image/png"].includes(file.type)) {
        error = "Choose a JPG, JPEG or PNG image.";
      }
      input.setCustomValidity(error);
    });
  };

  photoInputs.forEach((photoInput) => {
    const photoPreview = photoInput
      .closest(".photo-upload-field")
      ?.querySelector("[data-photo-preview]");
    if (!photoPreview) return;

    photoInput.addEventListener("change", () => {
      photoPreview.replaceChildren();
      validatePhotoInputs(photoInput);

      const file = photoInput.files?.[0];
      if (!file) return;

      if (photoInput.validationMessage) {
        photoInput.reportValidity();
        return;
      }

      const image = document.createElement("img");
      image.alt = `Preview: ${file.name}`;
      image.src = URL.createObjectURL(file);
      image.onload = () => URL.revokeObjectURL(image.src);

      const removeButton = document.createElement("button");
      removeButton.type = "button";
      removeButton.className = "photo-remove";
      removeButton.textContent = "Remove photo";
      removeButton.setAttribute("aria-label", `Remove ${file.name}`);
      removeButton.addEventListener("click", () => {
        photoInput.value = "";
        validatePhotoInputs();
        photoPreview.replaceChildren();
      });
      photoPreview.append(image, removeButton);
    });
  });

  form.addEventListener("submit", (event) => {
    const submitButton = form.querySelector(".submit-application");
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = "Submitting…";
    }
  });
}
