
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