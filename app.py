from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from datetime import datetime
import smtplib 
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bson.objectid import ObjectId
from pymongo import DESCENDING
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
    if request.method == "POST" and "name" in request.form and "phone" in request.form:
        # Extract form data
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        address = request.form.get("address")

        # Save to MongoDB
        contact_collection.insert_one({
            "name": name,
            "email": email,
            "phone": phone,
            "address": address,
            "submitted_at": datetime.now()
        })

        # Send Email
        sender_email = os.getenv("EMAIL_USER")       # your gmail
        sender_password = os.getenv("EMAIL_PASS") # app password
        receiver_email = os.getenv("REC_EMAIL")      # your admin email

        try:
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = receiver_email
            msg["Subject"] = "📩 New Contact Form Submission"

            body = f"""
            Someone submitted the contact form:

            Name: {name}
            Email: {email}
            Phone: {phone}
            Address: {address}
            """

            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)

            print("✅ Email sent successfully")
        except Exception as e:
            print("❌ Error sending email:", e)


        # Show success message to user
        flash("✅ Thank you! We will call you back soon.")
        return redirect(url_for("home"))

    # Load reviews for homepage
    reviews = list(reviews_collection.find().sort("date", -1).limit(6))

    # Calculate overall rating
    all_reviews = list(reviews_collection.find())
    total_reviews = len(all_reviews)
    if total_reviews > 0:
        overall_rating = round(sum(r.get('rating', 0) for r in all_reviews) / total_reviews, 1)
    else:
        overall_rating = 0

    return render_template("home.html",
                           reviews=reviews,
                           overall_rating=overall_rating,
                           total_reviews=total_reviews)


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

        quotation_collection.insert_one({
            "name": name,
            "email": email,
            "phone": phone,
            "date": datetime.now()
        })

        flash("Form submitted. Download your quotation below.")
        return render_template("quotation.html", show_download=True)

    return render_template("quotation.html", show_download=False)



if __name__ == "__main__":
    app.run(debug=True, port=3000)
