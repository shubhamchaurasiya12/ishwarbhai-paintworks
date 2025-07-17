console.log("JS loaded successfully.");

// static/js/script.js
setTimeout(() => {
  const toast = document.getElementById("flash-toast");
  if (toast) {
    toast.remove();
  }
}, 4000);
