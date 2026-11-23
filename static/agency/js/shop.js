const trainingShop = document.querySelector("[data-training-shop]");

if (trainingShop) {
  const training = trainingShop.querySelector('[name="training"]');
  const page = trainingShop.closest("[data-training-shop-page]");

  const updateTraining = () => {
    page.querySelectorAll("[data-training-details]").forEach((element) => {
      const type = element.dataset.trainingDetails;
      element.hidden = type !== training.value;
    });
  };

  training.addEventListener("change", updateTraining);
  updateTraining();
}
