const signUpButton = document.getElementById('signUp');
const signInButton = document.getElementById('signIn');
const container = document.querySelector('.container');

signUpButton.addEventListener('click', () => {
    console.log("Sign Up button clicked"); // Debugging
    container.classList.add('right-panel-active');
});

signInButton.addEventListener('click', () => {
    console.log("Sign In button clicked"); // Debugging
    container.classList.remove('right-panel-active');
});
