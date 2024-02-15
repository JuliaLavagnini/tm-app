import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

if os.path.exists("env.py"):
    import env

app = Flask(__name__)  # Create Flask app instance

# Configure MongoDB database
app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)  # Initialize PyMongo with Flask app

# Route for displaying tasks
@app.route("/")
@app.route("/show_tasks")
def show_tasks():
    tasks = list(mongo.db.tasks.find())  # Fetch tasks from MongoDB
    done_tasks = list(mongo.db.completed_tasks.find())  # Fetch completed tasks from MongoDB
    return render_template("home.html", tasks=tasks, done_tasks=done_tasks)  # Render template with tasks data

# Route for searching tasks
@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        query = request.form.get("query")
        if query:
            tasks = list(mongo.db.tasks.find({"$or": [
                {"task_name": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"team_name": {"$regex": query, "$options": "i"}},
                {"created_by": {"$regex": query, "$options": "i"}},
                {"priority": {"$regex": query, "$options": "i"}}
            ]}))
            return render_template("home.html", tasks=tasks)
        else:
            flash("Please enter a valid search query.", "error")
            return redirect(url_for("show_tasks"))
    else:
        return redirect(url_for("show_tasks"))

# Route for user registration
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Get form data
        username = request.form.get("username").title()
        team_name = request.form.get("team_name").title()
        team_position = request.form.get("team_position").title()
        email = request.form.get("email")
        password = request.form.get("password")

        # Check if username already exists
        existing_user = mongo.db.users.find_one({"username": username})
        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        # Check if team name already exists
        team = mongo.db.teams.find_one({"name": team_name})
        if team is None:
            # Create a new team
            team = {"name": team_name}
            team_id = mongo.db.teams.insert_one(team).inserted_id
        else:
            team_id = team["_id"]

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Insert new user data into the database
        new_user = {
            "username": username,
            "password": hashed_password,
            "team_id": team_id,
            "team_position": team_position,
            "email": email
        }
        mongo.db.users.insert_one(new_user)

        # Store the new user in session
        session["user"] = username
        return redirect(url_for("profile", username=session["user"]))

    return render_template("register.html")

# Route for user sign-in
@app.route("/sign_in", methods=["GET", "POST"])
def sign_in():
    if request.method == "POST":
        username = request.form.get("username").title()
        password = request.form.get("password")
        existing_user = mongo.db.users.find_one({"username": username})
        if existing_user and check_password_hash(existing_user["password"], password):
            session["user"] = username
            return redirect(url_for("profile", username=session["user"]))
        else:
            flash("Incorrect Username and/or Password")
            return redirect(url_for("sign_in"))
    return render_template("sign_in.html")

# Route for user profile
@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    if session.get("user"):
        user_tasks = mongo.db.tasks.find({"created_by": username})  # Fetch user tasks
        user_done_tasks = mongo.db.completed_tasks.find({"created_by": username})  # Fetch user completed tasks
        user_data = mongo.db.users.find_one({"username": username})  # Fetch user data
        if user_data:
            team_name = user_data.get("team_name", "")
            team_data = mongo.db.teams.find_one({"_id": ObjectId(user_data["team_id"])})  # Fetch team data
            if team_data:
                team_name = team_data["name"]
            team_members = mongo.db.users.find({"team_id": user_data["team_id"], "username": {"$ne": username}})
            return render_template("profile.html", username=username,
                                   user_tasks=user_tasks,
                                   user_done_tasks=user_done_tasks,
                                   team_members=team_members,
                                   team=team_name,
                                   user_data=user_data)
        else:
            return "User data not found", 404
    return redirect(url_for("sign_in"))

# Route for user sign-out
@app.route("/sign_out")
def sign_out():
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("sign_in"))

# Route for adding a task
@app.route("/add_task", methods=["GET", "POST"])
def add_task():
    if request.method == "POST":
        task = {
            "task_name": request.form.get("task_name"),
            "description": request.form.get("description"),
            "due": request.form.get("due"),
            "priority": request.form.get("priority_degree"),
            "team_name": request.form.get("team_name"),
            "created_by": session["user"]
        }
        mongo.db.tasks.insert_one(task)
        return redirect(url_for("profile", username=session["user"]))

    priorities = mongo.db.priorities.find().sort("priority_degree", 1)
    teams = mongo.db.teams.find().sort("name", 1)
    return render_template("add_task.html", priorities=priorities, teams=teams)

# Route for editing a task
@app.route("/edit_task/<task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    if request.method == "POST":
        submit = {
            "task_name": request.form.get("task_name"),
            "description": request.form.get("description"),
            "due": request.form.get("due"),
            "priority": request.form.get("priority_degree"),
            "team_name": request.form.get("team_name"),
            "created_by": session["user"]
        }
        filters = {"_id": ObjectId(task_id)}
        mongo.db.tasks.update_one(filters, {"$set": submit})
        return redirect(url_for("profile", username=session["user"]))

    priorities = mongo.db.priorities.find().sort("priority_degree", 1)
    teams = mongo.db.teams.find().sort("name", 1)
    task = mongo.db.tasks.find_one({"_id": ObjectId(task_id)})
    return render_template("edit_task.html", task=task, priorities=priorities, teams=teams)

# Route for marking a task as done
@app.route("/mark_done/<task_id>")
def mark_done(task_id):
    task = mongo.db.tasks.find_one({'_id': ObjectId(task_id)})
    if task:
        mongo.db.completed_tasks.insert_one(task)
        mongo.db.tasks.delete_one({'_id': ObjectId(task_id)})
        return redirect(url_for('profile', username=session['user']))
    else:
        return 'Task not found', 404

if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)  # Run the Flask app
