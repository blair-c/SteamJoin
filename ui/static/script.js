function inputToSteam(input) {
  steam = input;
  steam = steam.replace('https://', '')
  steam = steam.replace('steamcommunity.com/', '')
  steam = steam.replace('id/', '')
  steam = steam.replace('profiles/', '')
  steam = steam.replace(/[^a-zA-Z0-9_-]/g, '')
  return steam;
}

function formSubmit(event) {
  event.preventDefault();
  input = document.getElementById("profile-input").value;
  input = input.replace(/\s/g, '') // remove whitespace
  if (input) {
    steam = inputToSteam(input);
    window.location.href = '/' + steam + '?noredirect';
  }
  return false;
}
const form = document.getElementById("form");
form.addEventListener("submit", formSubmit)

async function copyJoinLink(input) {
  steam = inputToSteam(input);
  navigator.clipboard.writeText('https://steamjoin.com/' + steam);
  // Show success
  let tooltip = document.getElementById('copy-link');
  console.log(tooltip.textContent);
  if (tooltip.textContent == 'Copy Link') {
    tooltip.textContent = 'Copied!';
    await new Promise(r => setTimeout(r, 2000));
    tooltip.textContent = 'Copy Link';
  }
}
