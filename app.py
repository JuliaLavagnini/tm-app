import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)

login_manager = LoginManager(app)


class User(UserMixin):
    def __init__(self, user_id, username, password, team_name):
        self.id = user_id
        self.username = username
        self.password = password
        self.team_name = team_name

    @staticmethod
    def get(user_id):
        # Implement this method to retrieve a user by ID
        pass


@login_manager.user_loader
def load_user(user_id):
    # Implement this function to load a user by ID
    return User.get(user_id)


@app.route("/")
@app.route("/get_tasks")
def get_tasks():
    tasks = list(mongo.db.tasks.find())
    return render_template("tasks.html", tasks=tasks)


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    tasks = list(mongo.db.tasks.find({"$text": {"$search": query}}))
    return render_template("tasks.html", tasks=tasks)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Get form data directly from the request object
        username = request.form.get("username").title()
        team_name = request.form.get("team_name")
        password = request.form.get("password")

        # check if username already exists in db
        existing_user = mongo.db.users.find_one({"username": username})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        # Create a new user document
        register = {
            "username": username,
            "password": generate_password_hash(password),
            "team_name": team_name
        }
        # Insert the new user into the 'users' collection
        mongo.db.users.insert_one(register)

        # Set the new user into the 'session' cookie
        session["user"] = username
        return redirect(url_for("profile", username=session["user"]))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Check username and password (replace with your authentication logic)
        user = User.get(request.form.get("username"))
        if user and check_password(request.form.get("password"), user.password):
            login_user(user)
            flash("Logged in successfully.")
            return redirect(url_for("profile", username=user.username))

        flash("Invalid username or password.")

    return render_template("login.html")


@app.route("/profile/<username>", methods=["GET", "POST"])
@login_required
def profile(username):
    if session.get("user"):
        # Fetch tasks for the specified user from the database
        user_tasks = mongo.db.tasks.find({"created_by": username})

        # Fetch team name for the current user
        user_data = mongo.db.users.find_one({"username": username})
        # Ensure that team_name is in your user data structure
        team_name = user_data.get("team_name", "")

        # Fetch team members with the same team_name excluding the current user
        team_members = mongo.db.users.find(
            {"team_name": team_name, "username": {"$ne": username}})

        return render_template("profile.html", username=username,
                               user_tasks=user_tasks,
                               team_members=team_members, team=team_name)

    return redirect(url_for("login"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for("get_tasks"))


@app.route("/add_task", methods=["GET", "POST"])
def add_task():
    if request.method == "POST":
        task = {
            "task_name": request.form.get("task_name"),
            "description": request.form.get("description"),
            "due": request.form.get("due"),
            "team": request.form.get("team_name"),
            "priority": request.form.get("priority_degree"),
            "created_by": session["user"]
        }
        mongo.db.tasks.insert_one(task)
        flash("Task Successfully Added")
        return redirect(url_for("get_tasks"))

    priorities = mongo.db.priorities.find().sort("priority_degree", 1)
    teams = mongo.db.teams.find().sort("team_name", 1)
    return render_template("add_task.html", priorities=priorities, teams=teams)


@app.route("/edit_task/<task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    if request.method == "POST":
        is_urgent = "on" if request.form.get("is_urgent") else "off"
        submit = {
            "category_name": request.form.get("category_name"),
            "task_name": request.form.get("task_name"),
            "task_description": request.form.get("task_description"),
            "is_urgent": is_urgent,
            "due_date": request.form.get("due_date"),
            "created_by": session["user"]
        }
        mongo.db.tasks.update({"_id": ObjectId(task_id)}, submit)
        flash("Task Successfully Updated")

    task = mongo.db.tasks.find_one({"_id": ObjectId(task_id)})
    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template("edit_task.html", task=task, categories=categories)


@app.route("/delete_task/<task_id>")
def delete_task(task_id):
    mongo.db.tasks.remove({"_id": ObjectId(task_id)})
    flash("Task Successfully Deleted")
    return redirect(url_for("get_tasks"))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
