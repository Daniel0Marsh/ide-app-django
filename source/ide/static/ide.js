
var editor;

function changeTheme(theme) {
    editor.setOption("theme", theme);
    document.getElementById('currentTheme').textContent = theme.charAt(0).toUpperCase() + theme.slice(1);
    document.getElementById('selectedThemeInput').value = theme;
}

function changeSyntax(mode) {
    editor.setOption("mode", mode);
    document.getElementById('currentSyntax').textContent = mode.charAt(0).toUpperCase() + mode.slice(1);
    document.getElementById('selectedSyntaxInput').value = mode;
}

document.addEventListener("DOMContentLoaded", function () {
    editor = CodeMirror.fromTextArea(document.getElementById("myTextarea"), {
        lineNumbers: true,
        mode: "autodetect",
        theme: "default",
        autoCloseBrackets: true,
        matchBrackets: true
    });
    editor.setSize(null, "100%");

    var initialTheme = "{{ current_project.selected_theme }}";
    var initialSyntax = "{{ current_project.selected_syntax }}";

    if (initialTheme !== "default") {
        changeTheme(initialTheme);
    }
    if (initialSyntax !== "auto") {
        changeSyntax(initialSyntax);
    }
});

document.getElementById("sidebarCollapse").addEventListener("click", function () {
    document.getElementById("sidebar").classList.toggle("active");
});

document.querySelectorAll('.collapse').forEach(function(collapse) {
    collapse.addEventListener('show.bs.collapse', function() {
        this.previousElementSibling.querySelector('.bi-folder-plus').classList.add('d-none');
        this.previousElementSibling.querySelector('.bi-folder-minus').classList.remove('d-none');
    });

    collapse.addEventListener('hide.bs.collapse', function() {
        this.previousElementSibling.querySelector('.bi-folder-plus').classList.remove('d-none');
        this.previousElementSibling.querySelector('.bi-folder-minus').classList.add('d-none');
    });
});



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

// open the change project model if current_project === 'none'
window.onload = function() {
var current_project = "{{ current_project }}";

if (current_project === "none") {
  var myModal = new bootstrap.Modal(document.getElementById('openingProjectModal'));
  myModal.show();
}
};




