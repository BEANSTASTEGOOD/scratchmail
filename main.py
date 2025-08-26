from flask import Flask, render_template_string, request, session as flask_session, redirect, url_for, jsonify
from scratchclient import ScratchSession
import os

app = Flask(__name__)
app.secret_key = "supersecret"

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Scratch Messages Dashboard</title>
    <style>
        body {
            font-family: "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            background: #f5f5f5;
        }
        header {
            background: #8e44ad; /* purple instead of orange */
            color: white;
            padding: 15px;
            font-size: 22px;
            font-weight: bold;
        }
        main {
            padding: 20px;
            max-width: 800px;
            margin: auto;
        }
        .section-title {
            color: #e67e22; /* orange instead of purple */
            font-size: 18px;
            margin: 15px 0 10px;
        }
        .message {
            background: white;
            border: 2px solid #8e44ad;
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 10px;
        }
        .message.unread {
            border-color: #e67e22;
            background: #fff6f0;
        }
        .time {
            font-size: 0.85em;
            color: #666;
            margin-bottom: 6px;
        }
        button {
            background: #e67e22;
            border: none;
            color: white;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 5px;
        }
        button:hover {
            background: #ca5f0c;
        }
        form {
            margin-bottom: 20px;
            background: white;
            padding: 10px;
            border-radius: 6px;
            border: 1px solid #ccc;
        }
        input {
            margin: 5px;
            padding: 6px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <header>Scratch Messages (Purple/Orange Theme)</header>
    <main>
        <form method="POST" action="/login" onsubmit="saveLogin()">
            <input type="text" id="username" name="username" placeholder="Username" required>
            <input type="password" id="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>

        <div class="section-title">Unread Messages</div>
        <div id="unread"></div>

        <div class="section-title">Read Messages</div>
        <div id="read"></div>
    </main>

    <script>
        function saveLogin() {
            localStorage.setItem("username", document.getElementById("username").value);
            localStorage.setItem("password", document.getElementById("password").value);
        }

        let readMessages = JSON.parse(localStorage.getItem("readMessages") || "[]");
        let notifiedMessages = JSON.parse(localStorage.getItem("notifiedMessages") || "[]");

        function markAsRead(id) {
            if (!readMessages.includes(id)) {
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

                    if (!readMessages.includes(id)) {
                        div.classList.add("unread");
                        let btn = document.createElement("button");
                        btn.textContent = "Mark as Read";
                        btn.onclick = () => markAsRead(id);
                        div.appendChild(btn);
                        containerUnread.appendChild(div);

                        if (Notification.permission === "granted" && !notifiedMessages.includes(id)) {
                            new Notification("New Scratch Message", { body: msg.text });
                            notifiedMessages.push(id);
                            localStorage.setItem("notifiedMessages", JSON.stringify(notifiedMessages));
                        }
                    } else {
                        containerRead.appendChild(div);
                    }
                });
            });
        }

        window.onload = function() {
            if (localStorage.getItem("username")) document.getElementById("username").value = localStorage.getItem("username");
            if (localStorage.getItem("password")) document.getElementById("password").value = localStorage.getItem("password");

            if (Notification.permission !== "granted") Notification.requestPermission();

            if (localStorage.getItem("username") && localStorage.getItem("password")) {
                loadMessages();
                setInterval(loadMessages, 10000);
            }
        }
    </script>
</body>
</html>
"""

# --- backend stays same as before ---

def format_message(msg):
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
