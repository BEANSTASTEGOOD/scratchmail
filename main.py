from flask import Flask, render_template_string, request, session as flask_session, redirect, url_for, jsonify
from scratchclient import ScratchSession

app = Flask(__name__)
app.secret_key = "supersecret"

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Scratch Messages</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .message { border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 6px; }
        .time { font-size: 0.9em; color: gray; }
        form { margin-bottom: 20px; }
        input { margin: 5px; padding: 5px; }
        button { margin-top: 5px; }
    </style>
</head>
<body>
    <h1>Scratch Messages Dashboard</h1>

    <form method="POST" action="/login" onsubmit="saveLogin()">
        <input type="text" id="username" name="username" placeholder="Username" required>
        <input type="password" id="password" name="password" placeholder="Password" required>
        <button type="submit">Login</button>
    </form>

    <h2>Unread Messages</h2>
    <div id="unread"></div>

    <h2>Read Messages</h2>
    <div id="read"></div>

    <script>
        // Save login to localStorage
        function saveLogin() {
            localStorage.setItem("username", document.getElementById("username").value);
            localStorage.setItem("password", document.getElementById("password").value);
        }

        let readMessages = JSON.parse(localStorage.getItem("readMessages") || "[]");

        function markAsRead(id) {
            if(!readMessages.includes(id)) {
                readMessages.push(id);
                localStorage.setItem("readMessages", JSON.stringify(readMessages));
                loadMessages();
            }
        }

        function loadMessages() {
            fetch("/messages")
            .then(res => res.json())
            .then(data => {
                let containerUnread = document.getElementById("unread");
                let containerRead = document.getElementById("read");
                containerUnread.innerHTML = "";
                containerRead.innerHTML = "";

                data.forEach(msg => {
                    let id = msg.unique_id;
                    let div = document.createElement("div");
                    div.className = "message";
                    div.innerHTML = `<div class="time">[${msg.created_timestamp}]</div><div>${msg.text}</div>`;

                    if(!readMessages.includes(id)) {
                        let btn = document.createElement("button");
                        btn.textContent = "Mark as Read";
                        btn.onclick = () => markAsRead(id);
                        div.appendChild(btn);

                        // Notification for new message
                        if(Notification.permission === "granted") {
                            new Notification("New Scratch Message", { body: msg.text });
                        }

                        containerUnread.appendChild(div);
                    } else {
                        containerRead.appendChild(div);
                    }
                });
            });
        }

        window.onload = function() {
            if(localStorage.getItem("username")) document.getElementById("username").value = localStorage.getItem("username");
            if(localStorage.getItem("password")) document.getElementById("password").value = localStorage.getItem("password");

            // Ask for notification permission
            if(Notification.permission !== "granted") Notification.requestPermission();

            if(localStorage.getItem("username") && localStorage.getItem("password")) {
                loadMessages();
                setInterval(loadMessages, 10000);
            }
        }
    </script>
</body>
</html>
"""

def format_message(msg):
    """Return readable text for a message"""
    if msg.type == "followuser":
        return f"{msg.actor} followed you."
    elif msg.type == "loveproject":
        return f"{msg.actor} loved your project '{msg.title}' (ID: {msg.project_id})."
    elif msg.type == "favoriteproject":
        return f"{msg.actor} favorited your project '{msg.project_title}' (ID: {msg.project_id})."
    elif msg.type == "addcomment":
        base = f"{msg.actor} commented '{msg.comment_fragment}' on {msg.comment_obj_title}"
        if msg.commentee_username:
            base += f" (in reply to {msg.commentee_username})"
        return base
    elif msg.type == "curatorinvite":
        return f"{msg.actor} invited you to curate the studio '{msg.title}' (ID: {msg.gallery_id})."
    elif msg.type == "remixproject":
        return f"{msg.actor} remixed '{msg.parent_title}' into '{msg.title}'."
    elif msg.type == "studioactivity":
        return f"Activity in studio '{msg.title}' (ID: {msg.gallery_id})."
    elif msg.type == "forumpost":
        return f"{msg.actor} posted in forum topic '{msg.topic_title}' (ID: {msg.topic_id})."
    elif msg.type == "becomehoststudio":
        return f"You became the host of '{msg.gallery_title}' (ID: {msg.gallery_id})."
    elif msg.type == "becomeownerstudio":
        return f"You became the manager of '{msg.gallery_title}' (ID: {msg.gallery_id})."
    elif msg.type == "userjoin":
        return "Welcome to Scratch! 🎉"
    else:
        return f"Unknown message type: {msg.type}"

def unique_id(msg):
    """Return a string uniquely identifying a message"""
    # Use type + timestamp + actor + project/comment ID if available
    base = f"{msg.type}_{msg.created_timestamp}_{msg.actor}"
    if hasattr(msg, "comment_id") and msg.comment_id:
        base += f"_c{msg.comment_id}"
    if hasattr(msg, "project_id") and msg.project_id:
        base += f"_p{msg.project_id}"
    return base

@app.route("/", methods=["GET"])
def index():
    return render_template_string(TEMPLATE)

@app.route("/login", methods=["POST"])
def login():
    flask_session["username"] = request.form["username"]
    flask_session["password"] = request.form["password"]
    return redirect(url_for("index"))

@app.route("/messages", methods=["GET"])
def messages():
    if "username" not in flask_session or "password" not in flask_session:
        return jsonify([])

    try:
        s = ScratchSession(flask_session["username"], flask_session["password"])
        msgs = s.get_messages(limit=20)
        return jsonify([
            {
                "created_timestamp": m.created_timestamp,
                "text": format_message(m),
                "unique_id": unique_id(m)
            }
            for m in msgs
        ])
    except Exception as e:
        print("Error fetching messages:", e)
        return jsonify([])

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render provides the PORT environment variable
    app.run(host="0.0.0.0", port=port, debug=True)
