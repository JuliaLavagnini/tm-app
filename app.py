import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from pymongo import MongoClient
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


@app.route("/")
@app.route("/get_tasks")
def get_tasks():
    tasks = mongo.db.tasks.find()
    return render_template("my-tasks.html", tasks=tasks)


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)

uri = "mongodb+srv://julialavagninimaia:nOMlYqDw7ubfR9sX@cluster0.iprbu29.mongodb.net/task_manager?retryWrites=true&w=majority"

try:
    # Attempt to connect to MongoDB
    client = MongoClient(uri)
    db = client.get_database()
    print("Connected to MongoDB successfully!")

    # Perform MongoDB operations here

except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
