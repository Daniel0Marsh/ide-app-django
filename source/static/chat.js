// Pass the logged-in user's username from Django to JavaScript
const loggedInUsername = "{{ request.user.username|escapejs }}";
const roomName = "{{ room_name|escapejs }}";
const chatSocket = new WebSocket(
    `ws://${window.location.host}/ws/chat/${roomName}/`
);

chatSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    const chatLog = document.querySelector('#chat-log');

    // Create message item container
    const messageItem = document.createElement('div');
    messageItem.classList.add('message-item');

    // Add the appropriate CSS class based on sender
    if (data.sender === loggedInUsername) {
        messageItem.classList.add('sender');
    } else {
        messageItem.classList.add('receiver');
    }

    // User's profile picture
    const profileImg = document.createElement('img');
    profileImg.classList.add('profile-img');
    profileImg.src = data.profile_image_url;

    // Message content container
    const messageContent = document.createElement('div');
    messageContent.classList.add('message-content');

    // User's name bubble
    const userName = document.createElement('span');
    userName.classList.add('user-name');
    userName.textContent = data.sender;

    // Timestamp bubble
    const timestamp = document.createElement('span');
    timestamp.classList.add('timestamp');
    timestamp.textContent = data.timestamp;  // Display timestamp

    // Message bubble
    const messageBubble = document.createElement('div');
    messageBubble.classList.add('message-bubble');
    messageBubble.textContent = data.message;

    // Append username and timestamp to message content
    const usernameContainer = document.createElement('div');
    usernameContainer.appendChild(userName);
    usernameContainer.appendChild(timestamp);

    messageContent.appendChild(usernameContainer);
    messageContent.appendChild(messageBubble);

    // Append profile image and message content to message item
    messageItem.appendChild(profileImg);
    messageItem.appendChild(messageContent);

    chatLog.appendChild(messageItem);

    // Auto-scroll to the latest message
    chatLog.scrollTop = chatLog.scrollHeight;
};

chatSocket.onclose = function(e) {
    console.error('Chat socket closed unexpectedly');
};

// Function to send the message
function sendMessage() {
    const messageInputDom = document.querySelector('#chat-message-input');
    const message = messageInputDom.value;
    chatSocket.send(JSON.stringify({
        'message': message,
        'sender': loggedInUsername, // Include sender info
    }));
    messageInputDom.value = ''; // Clear input after sending
}

// Send message on button click
document.querySelector('#chat-message-submit').onclick = function(e) {
    sendMessage();
};

// Send message on Enter key press
document.querySelector('#chat-message-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) { // Check if Enter is pressed (without Shift key for multi-line input)
        e.preventDefault(); // Prevent the default behavior (line break)
        sendMessage();
    }
});