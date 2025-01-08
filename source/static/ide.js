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
    const promptValue = document.querySelector('.terminal-input').value.trim();
    if (!promptValue) return;

    // Add the command to history and reset index
    commandHistory.push(promptValue);
    historyIndex = commandHistory.length;

var formData = new FormData();
formData.append('prompt', promptValue);

var terminalDiv = document.getElementById('terminal');
var project_name = "{{ current_project.project_name }}";
terminalDiv.innerHTML += '<div><span class="username">user@Ubuntu</span>:<span class="path">~/UserProjects/' + project_name + '</span>$ ' + promptValue + '</div>';



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
    terminalDiv.innerHTML += '<div><span class="prompt"></span> ' + data.response + '</div>';
    // Clear the input field after sending the prompt
    document.querySelector('.terminal-input').value = '';
})
.catch(error => console.error('Error:', error));
}


let commandHistory = [];
let historyIndex = -1;

document.querySelector('.terminal-input').addEventListener('keydown', (e) => {
    if (e.key === 'ArrowUp') {
        // Navigate up the history
        if (historyIndex > 0) historyIndex--;
        e.target.value = commandHistory[historyIndex] || '';
        e.preventDefault(); // Prevent the default cursor movement
    } else if (e.key === 'ArrowDown') {
        // Navigate down the history
        if (historyIndex < commandHistory.length - 1) historyIndex++;
        e.target.value = commandHistory[historyIndex] || '';
        e.preventDefault();
    }
});





function toggleOffcanvasHeight() {
    const offcanvasElement = document.getElementById('offcanvasBottom');
    if (offcanvasElement.classList.contains('h-50')) {
        offcanvasElement.classList.remove('h-50');
        offcanvasElement.classList.add('h-100');
    } else {
        offcanvasElement.classList.remove('h-100');
        offcanvasElement.classList.add('h-50');
    }
}


    // Store the collapse state in an object
    let collapseState = {};

    // Function to update the project tree
    function updateProjectTree() {
        // Before updating the tree, store the current state of collapse elements
        document.querySelectorAll('.collapse').forEach(collapseElement => {
            const id = collapseElement.id;
            collapseState[id] = collapseElement.classList.contains('show');
        });

        // Save the scroll position of the sidebar to avoid shifting
        const sidebar = document.querySelector('#sidebar');
        const scrollPosition = sidebar.scrollTop;

        fetch(window.location.href, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',  // This tells Django it's an AJAX request
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.project_tree) {
                const treeContainer = document.querySelector('#sidebar ul');
                treeContainer.innerHTML = ''; // Clear the existing tree

                // Generate new tree HTML
                const treeHTML = generateTreeHTML(data.project_tree);
                treeContainer.innerHTML = treeHTML;

                // Reapply the saved collapse state
                document.querySelectorAll('.collapse').forEach(collapseElement => {
                    const id = collapseElement.id;
                    if (collapseState[id]) {
                        // If the state was 'expanded', reapply the 'show' class
                        collapseElement.classList.add('show');
                    } else {
                        // Otherwise, collapse it
                        collapseElement.classList.remove('show');
                    }
                });

                // Reinitialize collapse buttons
                document.querySelectorAll('.btn.folder-btn').forEach(button => {
                    const targetCollapse = document.querySelector(button.getAttribute('data-bs-target'));
                    if (targetCollapse && targetCollapse.classList.contains('show')) {
                        button.setAttribute('aria-expanded', 'true');
                    } else {
                        button.setAttribute('aria-expanded', 'false');
                    }
                });

                // Reapply the scroll position to prevent visual movement
                sidebar.scrollTop = scrollPosition;
            }
        })
        .catch(error => console.error('Error fetching project tree:', error));
    }

    // Function to generate tree HTML from the project tree structure
    function generateTreeHTML(nodes) {
        let html = '';
        nodes.forEach(node => {
            if (node.type === 'directory') {
                html += `<li>
                            <button class="btn btn-sm folder-btn" type="button" data-bs-toggle="collapse"
                                    data-bs-target="#${slugify(node.name)}" aria-expanded="false">
                                <i class="bi bi-folder-plus"></i><i class="bi bi-folder-minus d-none"></i> ${node.name}
                            </button>
                            <ul class="collapse" id="${slugify(node.name)}">
                                ${generateTreeHTML(node.children)}  <!-- Recursive call -->
                            </ul>
                          </li>`;
            } else if (node.type === 'file') {
                html += `<li>
                            <button class="btn btn-sm file-item" name="open_file" value="${node.path}" type="submit">
                                <i class="bi bi-file-earmark-code"></i> ${node.name}
                            </button>
                          </li>`;
            }
        });
        return html;
    }

    // Function to safely create slugs for the element IDs
    function slugify(text) {
        return text.toLowerCase().replace(/\s+/g, '-').replace(/[^\w\-]+/g, '');
    }

    // Update the project tree every 5 seconds
    setInterval(updateProjectTree, 3000);