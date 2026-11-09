const trainingShop = document.querySelector("[data-training-shop]");

if (trainingShop) {
  const training = trainingShop.querySelector('[name="training"]');
  const hours = trainingShop.querySelector("[data-training-hours]");
  const hoursInput = trainingShop.querySelector('[name="hours"]');
  const page = trainingShop.closest("[data-training-shop-page]");

  const updateTraining = () => {
    const individual = training.value === "individual";
    page.querySelectorAll("[data-training-details]").forEach((element) => {
      const type = element.dataset.trainingDetails;
      element.hidden = type !== training.value;
    });
    hours.hidden = !individual;
    hoursInput.disabled = !individual;
    hoursInput.required = individual;
  };

  training.addEventListener("change", updateTraining);
  updateTraining();
}
