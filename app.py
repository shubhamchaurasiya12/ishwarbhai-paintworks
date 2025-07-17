from flask import Flask, render_template, request, redirect, flash
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session

app = Flask(__name__)
app.secret_key = "secret123"  # Needed for flash messages


# MongoDB setup
client = MongoClient("mongodb://localhost:27017")
db = client['ishwarbhai_paintworks']

# Define all collections here:
contact_collection = db['contact']
reviews_collection = db['reviews']
users_collection = db['users']

# Set up Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# User model
class User(UserMixin):
    def __init__(self, user_doc):
        self.id = str(user_doc['_id'])
        self.name = user_doc['name']
        self.email = user_doc['email']

@login_manager.user_loader
def load_user(user_id):
    user_doc = users_collection.find_one({"_id": ObjectId(user_id)})
    return User(user_doc) if user_doc else None


@app.route("/", methods=["GET", "POST"])
def home():
    # Contact form handling (from Phase 3)
    if request.method == "POST" and "name" in request.form and "message" in request.form:
        # This POST is for contact form
        contact_data = {
            "name": request.form.get("name"),
            "email": request.form.get("email"),
            "phone": request.form.get("phone"),
            "address": request.form.get("address"),
            "message": request.form.get("message"),
            "submitted_at": datetime.now()
        }

        db.contact.insert_one(contact_data)
        flash("Thank you! We have received your message.")
        return redirect("/")
    # Get reviews from DB
    reviews = list(reviews_collection.find().sort("date", -1))

    return render_template("home.html")

@app.route("/submit_review", methods=["POST"])
@login_required
def submit_review():
    name = current_user.name  # Assuming `current_user.name` is stored on login
    rating = float(request.form.get("rating"))
    comment = request.form.get("comment")

    review = {
        "name": name,
        "rating": rating,
        "comment": comment,
        "date": datetime.now()
    }

    reviews_collection.insert_one(review)
    flash("Review submitted successfully!")
    return redirect("/")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if users_collection.find_one({"email": email}):
            flash("Email already registered.")
            return redirect("/signup")

        hashed_pw = generate_password_hash(password)
        user_doc = {
            "name": name,
            "email": email,
            "password": hashed_pw
        }
        user_id = users_collection.insert_one(user_doc).inserted_id
        flash("Signup successful. You can now log in.")
        return redirect("/login")

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user_doc = users_collection.find_one({"email": email})
        if user_doc and check_password_hash(user_doc["password"], password):
            login_user(User(user_doc))
            flash("Logged in successfully.")
            return redirect("/")
        else:
            flash("Invalid email or password.")
            return redirect("/login")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You’ve been logged out.")
    return redirect("/")

@app.route("/force_logout")
def force_logout():
    from flask_login import logout_user
    logout_user()
    flash("Force logout successful. Please log in again.")
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
