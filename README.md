# Django Collaborative Project Platform with IDE and Docker Integration

 This Django-based app combines an Integrated Development Environment (IDE) with social and collaborative features. It enables users to connect, collaborate on projects, manage tasks, and even run project code in a Docker terminal. 

## Key Features

### Social and Messaging:
- **Direct Messaging:** Send direct messages to users you follow and who follow you.
- **User Connections:** Follow other users and see who follows you to build a collaborative network.
- **Project Browsing:** View and explore other users' public projects.

### Collaboration and Task Management:
- **Project Collaboration:** Collaborate with other users on shared projects.
- **Task Management:** Assign and manage tasks for collaborators within projects.
- **Docker Integration:** Run project code directly in a Docker-based terminal environment.

### IDE Functionality:
- **Project Management:** Create, edit, rename, and organize files and folders within the project tree.
- **Download Project:** Download the entire project for offline access or sharing.
- **Auto Syntax Highlighting:** Syntax highlighting for various programming languages for improved readability.
- **Themes:** Personalize your coding environment with multiple available themes.

## Screenshots

| Overview                                              | 
|-------------------------------------------------------|
| <img src="./screenshots/overview.png" width="100%">   |

## Requirements

- Django
- CodeMirror API
- Bootstrap API
- Docker

## Installation


### 1. Clone this repository.
```bash
   git clone https://github.com/your-repo/project-platform.git
   cd project-platform
```

### 2. Install the required dependencies using pip:
```bash
pip install -r requirements.txt
```
### 3 Run migrations to create necessary database tables:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Build the Docker image for running project code:
```bash
sudo docker build -t terminal_session .
```
- To remove the Docker image: 
```bash
sudo docker rmi -f terminal_session
```

### 5. Start your Django development server:
```bash
python manage.py runserver
```

### 6. For WebSocket functionality, run the ASGI server:
```bash
daphne -p 8000 core.asgi:application
```

### 7. Navigate to the IDE app's URL in your browser to access the IDE.
   `http:127.0.0.1:8000`

## Functionality
- Messaging and Networking: Build a network of collaborators and communicate seamlessly.
- Project Collaboration: Work with team members on shared projects, assign tasks, and track progress.
- IDE with Docker Support: Write, manage, and run project code with the integrated IDE and Docker terminal.