import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


@app.route("/")
@app.route("/show_tasks")
def show_tasks():
    tasks = list(mongo.db.tasks.find())
    done_tasks = list(mongo.db.completed_tasks.find())
    return render_template("home.html", tasks=tasks, done_tasks=done_tasks)


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    tasks = list(mongo.db.tasks.find({"$text": {"$search": query}}))
    return render_template("home.html", tasks=tasks)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Get form data directly from the request object
        username = request.form.get("username").title()
        team_name = request.form.get("team_name").title()
        team_position = request.form.get("team_position").title()
        email = request.form.get("email")
        password = request.form.get("password")

        # check if username already exists in db
        existing_user = mongo.db.users.find_one({"username": username})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        # Check if team name already exists in db
        team = mongo.db.teams.find_one({"name": team_name})

        if team is None:
            # Create a new team document
            team = {"name": team_name}
            # Insert the new team into the 'teams' collection
            team_id = mongo.db.teams.insert_one(team).inserted_id
        else:
            # Use the existing team id as the team id for the user
            team_id = team["_id"]

        register = {
            "username": username,
            "password": generate_password_hash(password),
            "team_id": team_id,
            "team_position": team_position,
            "email": email
        }
        # Insert the new user into the 'users' collection
        mongo.db.users.insert_one(register)

        # Set the new user into the 'session' cookie
        session["user"] = username
        return redirect(url_for("profile", username=session["user"]))

    return render_template("register.html")


# user sign-in function
@app.route("/sign_in", methods=["GET", "POST"])
def sign_in():
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").title()})
        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                session["user"] = request.form.get("username").title()
                return redirect(
                    url_for("profile", username=session["user"]))
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("sign_in"))
        else:
            # username doesn't exist
            flash("Username not found, please register")
            return redirect(url_for("sign_in"))
    return render_template("sign_in.html")


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    if session.get("user"):
        # Fetch tasks for the specified user from the database
        user_tasks = mongo.db.tasks.find({"created_by": username})

        # Fetch done tasks for the specified user from the database
        user_done_tasks = mongo.db.completed_tasks.find(
            {"created_by": username})

        # Fetch team name for the current user
        user_data = mongo.db.users.find_one({"username": username})
        # Ensure that user_data is not None before trying to access its fields
        if user_data is not None:
            team_name = user_data.get("team_name", "")

            # Fetch team document using team_id
            team_data = mongo.db.teams.find_one(
                {"_id": ObjectId(user_data["team_id"])})

            # Ensure that team_data is not None before trying to access its fields
            if team_data is not None:
                team_name = team_data["name"]

            # Fetch all team members with the same team_id, excluding the current user
            team_members = mongo.db.users.find(
                {"team_id": user_data["team_id"], "username": {"$ne": username}})

            return render_template("profile.html", username=username,
                                   user_tasks=user_tasks,
                                   user_done_tasks=user_done_tasks,
                                   team_members=team_members,
                                   team=team_name,
                                   user_data=user_data)

        else:
            # User data not found, handle error
            return "User data not found", 404

    return redirect(url_for("sign_in"))


@app.route("/sign_out")
def sign_out():
    # remove user from session cookie
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("sign_in"))


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


@app.route('/mark_done', methods=['POST'])
def mark_done():
    task_id = request.form['task_id']
    task = mongo.db.tasks.find_one({'_id': ObjectId(task_id)})

    if task:
        mongo.db.completed_tasks.insert_one(task)
        mongo.db.tasks.delete_one({'_id': ObjectId(task_id)})
    return redirect(url_for('profile', username=session['user']))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
