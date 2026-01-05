const startButton = document.getElementById('startButton');
const startMenu = document.getElementById('startMenu');
const clock = document.getElementById('clock');

function updateClock() {
  const now = new Date();
  const hours = now.getHours().toString().padStart(2, '0');
  const minutes = now.getMinutes().toString().padStart(2, '0');
  clock.textContent = `${hours}:${minutes}`;
}

function toggleStartMenu() {
  startMenu.classList.toggle('open');
}

function closeStartMenu(event) {
  if (!startMenu.contains(event.target) && !startButton.contains(event.target)) {
    startMenu.classList.remove('open');
  }
}

updateClock();
setInterval(updateClock, 30 * 1000);

startButton.addEventListener('click', toggleStartMenu);
document.addEventListener('click', closeStartMenu);

// Keep keyboard navigation intuitive
startButton.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    toggleStartMenu();
  }
});
