document.addEventListener("DOMContentLoaded", function () {
    // Retrieve the logged-in user's information from the server-side template
    const loggedInUsername = "{{ request.user.username|escapejs }}"; // Username of the logged-in user
    const loggedInUserId = parseInt("{{ request.user.id }}", 10);  // ID of the logged-in user

    // Initialize the WebSocket connection for real-time chat
    const chatSocket = new WebSocket(`ws://${window.location.host}/ws/chat/`);

    // Select DOM elements for interactions
    const participantLinks = document.querySelectorAll('.participant-link'); // All participant links
    const backToChatsButton = document.getElementById('backToChatsButton'); // Back button to list chats
    const openChatCard = document.getElementById('openChatCard'); // Card displaying open chat
    const listChatCard = document.getElementById('ListChatCard'); // Card displaying list of chats
    const chatLog = document.querySelector('#chat-log'); // Log where messages will be displayed
    const messageInputDom = document.querySelector('#chat-message-input'); // Input field for new messages
    const messageSubmitButton = document.querySelector('#chat-message-submit'); // Button to submit a message

    // Variables for the current chat recipient and room
    let currentRecipientId = null;
    let currentRoomName = null;

    // Event listener for when a participant is selected to start a chat
    if (participantLinks.length > 0) {
        participantLinks.forEach(link => {
            link.addEventListener('click', function (e) {
                e.preventDefault();

                // Set the recipient's ID and other details from the data attributes of the clicked link
                currentRecipientId = parseInt(this.dataset.recipientId, 10);
                const recipientUsername = this.dataset.recipientUsername;
                const recipientProfileImage = this.dataset.recipientProfile;
                const recipientProfileUrl = `/profile/${recipientUsername}`;

                // Generate the chat room name based on the IDs (to ensure uniqueness)
                currentRoomName = `${Math.min(loggedInUserId, currentRecipientId)}-${Math.max(loggedInUserId, currentRecipientId)}`;

                // Update the UI with the selected recipient's details
                document.getElementById('recipient-username').textContent = recipientUsername;
                document.getElementById('recipient-username').href = recipientProfileUrl;
                document.getElementById('recipient-profile-img').src = recipientProfileImage;

                // Filter and display messages for the selected chat room
                filterMessagesByRoom(currentRoomName);

                // Join the WebSocket room for the selected recipient
                chatSocket.send(JSON.stringify({
                    'action': 'join',
                    'recipient_id': currentRecipientId,
                    'roomName': currentRoomName
                }));

                // Show the chat interface
                toggleChatVisibility(true);
            });
        });
    }

    // Event listener for the "back to chats" button to return to the chat list
    if (backToChatsButton) {
        backToChatsButton.addEventListener('click', function() {
            toggleChatVisibility(false);
        });
    }

    // Function to filter and display messages for the selected chat room
    function filterMessagesByRoom(roomName) {
        // Get all message items
        const allMessages = Array.from(document.querySelectorAll('.message-item'));

        console.log(`Filtering messages for room: ${roomName}`);

        // Loop through all messages and display only those belonging to the selected room
        allMessages.forEach(message => {
            if (message.dataset.roomname === roomName) {
                message.style.display = '';  // Show the message
            } else {
                message.style.display = 'none';  // Hide the message
            }
        });

        // Auto-scroll to the latest visible message
        const visibleMessages = document.querySelectorAll('.message-item[style="display: inline;"]');
        if (visibleMessages.length > 0) {
            chatLog.scrollTop = chatLog.scrollHeight; // Scroll to the bottom of the chat log
        }
    }

    // WebSocket onmessage handler to display incoming messages
    chatSocket.onmessage = function (e) {
        const data = JSON.parse(e.data);

        // Check if the message was sent by the current logged-in user
        const isSender = data.sender === loggedInUsername;

        // Create a message element for the incoming message
        const messageItem = createMessageElement(data, isSender);

        // Append the message element to the chat log
        chatLog.appendChild(messageItem);

        // Auto-scroll to the latest message
        chatLog.scrollTop = chatLog.scrollHeight;
    };

    // Function to create a new message element and return it
    function createMessageElement(data, isSender) {
        const messageItem = document.createElement('div');
        messageItem.classList.add('message-item', isSender ? 'sender' : 'receiver');
        messageItem.dataset.roomname = data.roomName; // Add room name for filtering

        // Create the profile image for the sender
        const profileImg = document.createElement('img');
        profileImg.classList.add('profile-img');
        profileImg.src = data.profile_image_url;

        // Create the container for the message content (including username and timestamp)
        const messageContent = document.createElement('div');
        messageContent.classList.add('message-content');

        // Username and timestamp container
        const usernameContainer = document.createElement('div');

        const userName = document.createElement('span');
        userName.classList.add('user-name');
        userName.textContent = data.sender;

        const timestamp = document.createElement('span');
        timestamp.classList.add('timestamp');
        timestamp.textContent = data.timestamp;

        // Append username and timestamp to the container
        usernameContainer.appendChild(userName);
        usernameContainer.appendChild(timestamp);

        // Message bubble container
        const messageBubble = document.createElement('div');
        messageBubble.classList.add('message-bubble');
        messageBubble.textContent = data.message;

        // Append username, timestamp, and message bubble to the message content
        messageContent.appendChild(usernameContainer);
        messageContent.appendChild(messageBubble);

        // Append profile image and message content to the message item
        messageItem.appendChild(profileImg);
        messageItem.appendChild(messageContent);

        return messageItem;
    }

    // WebSocket onclose handler for unexpected disconnections
    chatSocket.onclose = function(e) {
        console.error('Chat socket closed unexpectedly');
    };

    // Helper function to toggle chat visibility (show or hide the open chat interface)
    function toggleChatVisibility(showChat) {
        if (showChat) {
            listChatCard.style.display = 'none'; // Hide chat list
            openChatCard.style.display = 'block'; // Show open chat interface
            openChatCard.classList.add('fade-in'); // Apply fade-in effect
        } else {
            openChatCard.style.display = 'none'; // Hide open chat
            listChatCard.style.display = 'block'; // Show chat list
        }
    }

    // Function to send a message to the WebSocket server
    function sendMessage() {
        const message = messageInputDom.value; // Get the message from the input field
        chatSocket.send(JSON.stringify({
            'action': 'message',
            'message': message,
            'sender': loggedInUsername,
            'recipient_id': currentRecipientId,
        }));
        messageInputDom.value = '';  // Clear the input field after sending the message
    }

    // Send message when the submit button is clicked
    messageSubmitButton.onclick = function(e) {
        sendMessage();
    };

    // Send message when Enter key is pressed (without Shift for new lines)
    messageInputDom.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});