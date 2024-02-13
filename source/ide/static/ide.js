<script>
    // ajax used to send and receive the terminal prompts and responses

    function sendPrompt() {
    var promptValue = document.querySelector('.terminal-input').value;

    var formData = new FormData();
    formData.append('prompt', promptValue);

    var terminalDiv = document.getElementById('terminal');
    terminalDiv.innerHTML += '<div><span class="prompt">User$</span> ' + promptValue + '</div>'; // Append input text

    if (promptValue.toLowerCase() === 'clear') {
        terminalDiv.innerHTML = ''; // Clear the terminal
        // Clear the input field after sending the prompt
        document.querySelector('.terminal-input').value = '';
        return; // Exit the function
    }

    fetch('', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': '{{ csrf_token }}' // Include CSRF token for Django
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log(data); // Do something with the response
        // Append the response to the terminal UI
        terminalDiv.innerHTML += '<div><span class="prompt">User$</span> ' + data.response + '</div>';
        // Clear the input field after sending the prompt
        document.querySelector('.terminal-input').value = '';
    })
    .catch(error => console.error('Error:', error));
}
</script>



