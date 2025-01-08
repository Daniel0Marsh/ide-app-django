
const roomName = "{{ room_name }}";
const chatSocket = new WebSocket(
    `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/chat/${roomName}/`
);

chatSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    const chatLog = document.querySelector('#chat-log');

    // Create a new message container
    const messageItem = document.createElement('div');
    messageItem.classList.add('message-item');

    // Add sender and timestamp if available
    if (data.sender) {
        const senderElem = document.createElement('strong');
        senderElem.textContent = `${data.sender}: `;
        messageItem.appendChild(senderElem);
    }

    // Add the message text
    const messageText = document.createElement('span');
    messageText.textContent = data.message;
    messageItem.appendChild(messageText);

    // Add timestamp if available
    if (data.timestamp) {
        const timestampElem = document.createElement('span');
        timestampElem.classList.add('timestamp');
        timestampElem.textContent = ` (${data.timestamp})`;
        messageItem.appendChild(timestampElem);
    }

    // Append the message to the chat log
    chatLog.appendChild(messageItem);

    // Auto-scroll to the latest message
    chatLog.scrollTop = chatLog.scrollHeight;
};

chatSocket.onclose = function(e) {
    console.error('Chat socket closed unexpectedly');
};

chatSocket.onerror = function(e) {
    console.error('WebSocket encountered an error:', e);
    alert('An error occurred with the chat connection. Please try again.');
};

document.querySelector('#chat-message-submit').onclick = function(e) {
    const messageInputDom = document.querySelector('#chat-message-input');
    const message = messageInputDom.value;

    chatSocket.send(JSON.stringify({
        'message': message,
        'sender': "{{ user.username }}",  // Include sender's username if available
    }));

    messageInputDom.value = ''; // Clear input after sending
};
