function toggleOptions() {
    const options = document.getElementById("options");
    options.style.display = options.style.display === "none" ? "block" : "none";
  }

  function showLoader() {
    const loader = document.getElementById("loader");
    loader.style.display = "block";
  }
  
function showNivelForm() {
const temaForm = document.getElementById("temaForm");
const nivelForm = document.getElementById("nivelForm");
const tematica = document.getElementById("tematica").value;
const hidden_tematica = document.getElementById("hidden_tematica");
if (tematica) {
  temaForm.style.display = "none";
  nivelForm.style.display = "block";
  hidden_tematica.value = tematica;
} else {
  alert("Por favor, ingresa un tema.");
}
}