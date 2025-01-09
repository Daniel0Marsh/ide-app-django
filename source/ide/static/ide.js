// Store the collapse state in an object
let collapseState = {};

// Function to update the project tree
function updateProjectTree() {
    // Before updating the tree, store the current state of collapse elements
    document.querySelectorAll('.collapse').forEach(collapseElement => {
        const id = collapseElement.id;
        collapseState[id] = collapseElement.classList.contains('show');
    });

    // Save the scroll position of the filesSidebar to avoid shifting
    const filesSidebar = document.querySelector('#filesSidebar');
    const scrollPosition = filesSidebar.scrollTop;

    fetch(window.location.href, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',  // This tells Django it's an AJAX request
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.project_tree) {
            const treeContainer = document.querySelector('#filesSidebar ul');
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
            filesSidebar.scrollTop = scrollPosition;
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

document.addEventListener("DOMContentLoaded", () => {
    const sidebarCollapse = document.getElementById("sidebarCollapse");
    const taskSidebarCollapse = document.getElementById("taskSidebarCollapse");
    const filesSidebar = document.getElementById("filesSidebar");
    const tasksSidebar = document.getElementById("tasksSidebar");
    const body = document.body; // Used for applying layout classes

    sidebarCollapse.addEventListener("click", () => {
        filesSidebar.classList.toggle("active");
        tasksSidebar.classList.remove("active"); // Close the other sidebar

        // Update body class for layout adjustments
        updateLayoutClasses();
    });

    taskSidebarCollapse.addEventListener("click", () => {
        tasksSidebar.classList.toggle("active");
        filesSidebar.classList.remove("active"); // Close the other sidebar

        // Update body class for layout adjustments
        updateLayoutClasses();
    });

    function updateLayoutClasses() {
        const isFilesSidebarActive = filesSidebar.classList.contains("active");
        const isTasksSidebarActive = tasksSidebar.classList.contains("active");

        // Remove all sidebar-related classes
        body.classList.remove("files-sidebar-active", "tasks-sidebar-active", "both-sidebars-active");

        // Apply appropriate class based on active sidebars
        if (isFilesSidebarActive && isTasksSidebarActive) {
            body.classList.add("both-sidebars-active");
        } else if (isFilesSidebarActive) {
            body.classList.add("files-sidebar-active");
        } else if (isTasksSidebarActive) {
            body.classList.add("tasks-sidebar-active");
        }
    }
});

// JavaScript to Populate Modal
document.addEventListener('DOMContentLoaded', () => {
    const updateTaskModal = document.getElementById('updateTaskModal');
    updateTaskModal.addEventListener('show.bs.modal', (event) => {
        const button = event.relatedTarget;
        const taskId = button.getAttribute('data-task-id');
        const taskTitle = button.getAttribute('data-task-title');
        const taskDescription = button.getAttribute('data-task-description');
        const taskStatus = button.getAttribute('data-task-status');

        // Populate the modal fields
        document.getElementById('task_id').value = taskId;
        document.getElementById('task_title').value = taskTitle;
        document.getElementById('task_description').value = taskDescription;
        document.getElementById('task_status').value = taskStatus;
    });
});

// Update the project tree every 3 seconds
setInterval(updateProjectTree, 3000);

var editor;

function changeTheme(theme) {
    editor.setOption("theme", theme);
    document.getElementById('currentTheme').textContent = theme.charAt(0).toUpperCase() + theme.slice(1);
    document.getElementById('selectedTheme').value = theme;
}

function changeSyntax(mode) {
    editor.setOption("mode", mode);
    document.getElementById('currentSyntax').textContent = mode.charAt(0).toUpperCase() + mode.slice(1);
    document.getElementById('selectedSyntax').value = mode;
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


// AJAX used to send and receive the terminal prompts and responses
function sendPrompt() {
    const promptValue = document.querySelector('.terminal-input').value.trim();
    if (!promptValue) return;

    // Add the command to history and reset index
    commandHistory.push(promptValue);
    historyIndex = commandHistory.length;

    const formData = new FormData();
    formData.append('prompt', promptValue);

    const terminalDiv = document.getElementById('terminal');
    const projectName = "{{ current_project.project_name }}";

    // Append the user's command in terminal-like format
    terminalDiv.innerHTML += `<div>
        <span class="username">user@Ubuntu</span>:<span class="path">~/UserProjects/${projectName}</span>$ ${promptValue}
    </div>`;

    if (promptValue.toLowerCase() === 'clear') {
        terminalDiv.innerHTML = ''; // Clear the terminal
        document.querySelector('.terminal-input').value = ''; // Clear the input field
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
        console.log(data); // Log response to console for debugging

        if (data.input_prompt) {
            // If the backend has sent an 'input_prompt', display it for user input
            const inputDiv = document.createElement('div');
            inputDiv.innerHTML = `<span class="output">${data.input_prompt}</span>`;
            terminalDiv.appendChild(inputDiv);

            // Focus on the input field to allow the user to respond
            document.querySelector('.terminal-input').focus();
        } else {
            // Format response with new lines for better terminal output style
            const formattedResponse = data.response
                .split('\n') // Split response by newlines
                .map(line => `<div><span class="output">${line}</span></div>`) // Wrap each line in a div
                .join('');

            // Append the formatted response to the terminal UI
            terminalDiv.innerHTML += formattedResponse;

            // Scroll to the bottom of the terminal
            terminalDiv.scrollTop = terminalDiv.scrollHeight;

            // Clear the input field after processing
            document.querySelector('.terminal-input').value = '';
        }
    })
    .catch(error => console.error('Error:', error));
}

let commandHistory = [];
let historyIndex = -1;

// Handle command history navigation
document.querySelector('.terminal-input').addEventListener('keydown', (e) => {
    if (e.key === 'ArrowUp') {
        // Navigate up the history
        if (historyIndex > 0) historyIndex--;
        e.target.value = commandHistory[historyIndex] || '';
        e.preventDefault(); // Prevent default cursor movement
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
