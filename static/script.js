var socket = io.connect("http://" + document.domain + ":" + location.port);

socket.on("message", (data) => {
    let messagesDiv = document.getElementById("messages");
    let messageElement = document.createElement("p");
    messageElement.innerHTML = `<strong>${data.username}:</strong> ${data.message}`;
    messagesDiv.appendChild(messageElement);
});

function sendMessage() {
    let input = document.getElementById("messageInput");
    socket.send({ "message": input.value });
    input.value = "";
}

function typing() {
    socket.emit("typing", {});
}

socket.on("user_typing", (data) => {
    console.log(`${data.username} is typing...`);
});

function startCall() {
    socket.emit("call", {});
}

socket.on("incoming_call", (data) => {
    alert(`${data.caller} is calling you!`);
});

document.getElementById("sendMessage").addEventListener("click", function() {
    var message = document.getElementById("messageInput").value;
    if (message.trim() !== "") {
        socket.emit("message", {room: room, message: message});
        document.getElementById("messageInput").value = "";
    }
});

socket.on("message", function(data) {
    var messageDiv = document.createElement("p");
    messageDiv.innerHTML = "<strong>" + data.username + ":</strong> " + data.message;
    document.getElementById("messages").appendChild(messageDiv);
});

socket.emit("join", {room: room});

document.getElementById("leaveRoom").addEventListener("click", function() {
    socket.emit("leave", {room: room});
    window.location.href = "/chat";
});

// File Upload
document.getElementById("fileInput").addEventListener("change", function() {
    var file = this.files[0];
    var formData = new FormData();
    formData.append("file", file);
    formData.append("room", room);

    fetch("/upload", {
        method: "POST",
        body: formData
    }).then(response => response.text())
    .then(data => {
        socket.emit("message", {room: room, message: "📂 File Uploaded: " + data});
    });
});

// Video Calling
document.getElementById("callButton").addEventListener("click", function() {
    window.open("/video_call/" + room, "_blank");
});

