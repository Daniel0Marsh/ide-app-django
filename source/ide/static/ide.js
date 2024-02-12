    var editor;

    function changeTheme(theme) {
        editor.setOption("theme", theme);
        // Update the button text to display the current theme
        document.getElementById('currentTheme').textContent = theme.charAt(0).toUpperCase() + theme.slice(1);
        // Update the hidden input field to store the selected theme
        document.getElementById('selectedThemeInput').value = theme;
    }

    function changeSyntax(mode) {
        editor.setOption("mode", mode);
        // Update the button text to display the current syntax
        document.getElementById('currentSyntax').textContent = mode.charAt(0).toUpperCase() + mode.slice(1);
        // Update the hidden input field to store the selected syntax
        document.getElementById('selectedSyntaxInput').value = mode;
    }

    document.addEventListener("DOMContentLoaded", function () {
        editor = CodeMirror.fromTextArea(document.getElementById("myTextarea"), {
            lineNumbers: true,
            mode: "auto", // Default mode
            theme: "default", // Default theme
            autoCloseBrackets: true, // Optional, enables bracket matching
            matchBrackets: true // Optional, enables bracket matching
        });
        editor.setSize(null, "100%");

        // Get the initial theme value from the model
        var initialTheme = "{{ project.selected_theme }}";
        // Get the initial syntax value from the model
        var initialSyntax = "{{ project.selected_syntax }}";

        // Update the theme if it's not the default theme
        if (initialTheme !== "default") {
            changeTheme(initialTheme);
        }
        // Update the syntax if it's not the default syntax
        if (initialSyntax !== "auto") {
            changeSyntax(initialSyntax);
        }
    });

    // Toggle sidebar
    document.getElementById("sidebarCollapse").addEventListener("click", function () {
        document.getElementById("sidebar").classList.toggle("active");
    });

    // Add event listeners to toggle folder icons
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

