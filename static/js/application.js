const form = document.querySelector("[data-application-form]");

if (form) {
  const photoInputs = [...form.querySelectorAll('input[type="file"]')];
  const maximumBytes = Number(form.dataset.maxPhotoBytes);
  const maximumPhotoMegabytes = form.dataset.maxPhotoMb;
  const dobInput = form.querySelector('input[name="date_of_birth"]');
  const ageOutput = document.querySelector("#calculated-age");
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

  const updateAge = () => {
    if (!dobInput?.value || !ageOutput) return;
    const [year, month, day] = dobInput.value.split("-").map(Number);
    const today = new Date();
    let age = today.getFullYear() - year;
    if (
      today.getMonth() + 1 < month ||
      (today.getMonth() + 1 === month && today.getDate() < day)
    ) {
      age -= 1;
    }
    ageOutput.textContent =
      age >= 0 ? `${age} ${age === 1 ? "year" : "years"}` : "Enter a valid date";
  };

  dobInput?.addEventListener("input", updateAge);
  updateAge();

  const updateKidsApplicationNotice = () => {
    if (ageCategoryInput && kidsApplicationNotice) {
      kidsApplicationNotice.hidden = ageCategoryInput.value !== "kids";
    }
  };

  ageCategoryInput?.addEventListener("change", updateKidsApplicationNotice);
  updateKidsApplicationNotice();

  const updateModellingExperienceDetails = () => {
    if (modellingExperienceDetails && modellingExperienceInput) {
      modellingExperienceDetails.hidden =
        modellingExperienceInput.value !== "yes";
    }
  };

  modellingExperienceInput?.addEventListener(
    "change",
    updateModellingExperienceDetails,
  );
  updateModellingExperienceDetails();

  const validatePhotoInputs = () => {
    photoInputs.forEach((input) => {
      const file = input.files?.[0];
      let error = "";
      if (file && !["image/jpeg", "image/png"].includes(file.type)) {
        error = "Choose a JPG, JPEG or PNG image.";
      } else if (file && file.size > maximumBytes) {
        error = `This photo must be ${maximumPhotoMegabytes} MB or smaller.`;
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
