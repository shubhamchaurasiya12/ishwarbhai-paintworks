from flask import Flask, render_template, request, redirect, flash
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
import os
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
  # Needed for flash messages


# MongoDB setup
client = MongoClient(os.environ.get("MONGO_URI"))
db = client["ishwarpaintworks"]

SECRET_KEY = os.environ.get("SECRET_KEY")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")


# Define all collections here:
contact_collection = db['contact']
reviews_collection = db['reviews']
users_collection = db['users']
gallery_collection = db['gallery']
quotation_collection = db["quotations"]


# Set up Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Admin Email
ADMIN_EMAIL = "admin@paintworks.com"

# Admin check helper
def is_admin():
    return current_user.is_authenticated and current_user.email == ADMIN_EMAIL


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
    reviews = list(reviews_collection.find().sort("date", -1))  # sort newest first (optional)
    return render_template("home.html", reviews=reviews)

@app.route("/submit_review", methods=["POST"])
@login_required
def submit_review():
    rating = float(request.form["rating"])
    comment = request.form["comment"]
    reviews_collection.insert_one({
        "name": current_user.name,
        "rating": rating,
        "comment": comment,
        "date": datetime.now()
    })
    flash("Review submitted!")
    return redirect("/")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        if users_collection.find_one({"email": email}):
            flash("Email already registered")
            return redirect("/signup")
        users_collection.insert_one({
            "name": name,
            "email": email,
            "password": password
        })
        flash("Signup successful. Please login.")
        return redirect("/login")
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user_doc = users_collection.find_one({"email": email})
        if user_doc and check_password_hash(user_doc["password"], password):
            user = User(user_doc)
            login_user(user)
            flash("Login successful.")
            return redirect("/")
        else:
            flash("Invalid credentials")
            return redirect("/login")
    return render_template("login.html")



@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("logged out successfully.")
    return redirect("/")

@app.route("/gallery")
def gallery_list():
    sites = gallery_collection.find({}, {"site_name": 1})
    return render_template("gallery_list.html", sites=sites)

@app.route("/gallery/<site_name>")
def gallery_site(site_name):
    site = gallery_collection.find_one({"site_name": site_name})
    return render_template("gallery_detail.html", site=site)


@app.route("/add_sample_gallery")
def add_sample_gallery():
    gallery_collection.insert_one({
        "site_name": "Hotel Raj",
        "images": [
            {
                "image_url": "/static/images/image1.png",
                "title": "Main Hall",
                "description": "Acrylic + Texture"
            },
            {
                "image_url": "/static/images/image2.png",
                "title": "Lobby",
                "description": "Duco Finish"
            }
        ]
    })
    return "Sample gallery added!"

@app.route("/admin")
@login_required
def admin_panel():
    if not is_admin():
        flash("Access denied")
        return redirect("/")

    contacts = contact_collection.find()
    reviews = reviews_collection.find()
    quotations = quotation_collection.find() if 'quotation_collection' in globals() else []
    gallery_sites = gallery_collection.find()

    return render_template("admin_panel.html", 
        contacts=contacts, 
        reviews=reviews, 
        quotations=quotations, 
        gallery_sites=gallery_sites)

@app.route("/admin/delete_review/<id>")
@login_required
def delete_review(id):
    if not is_admin():
        return redirect("/")
    reviews_collection.delete_one({"_id": ObjectId(id)})
    flash("Review deleted.")
    return redirect("/admin")


@app.route("/quotation", methods=["GET", "POST"])
def quotation():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        project = request.form["project"]

        quotation_collection.insert_one({
            "name": name,
            "email": email,
            "phone": phone,
            "project": project,
            "date": datetime.now()
        })

        flash("Form submitted. Download your quotation below.")
        return render_template("quotation.html", show_download=True)

    return render_template("quotation.html", show_download=False)



if __name__ == "__main__":
    app.run(debug=False)
