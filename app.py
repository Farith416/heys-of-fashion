from flask import Flask, render_template, request, redirect, session, flash
import os
from werkzeug.utils import secure_filename
from supabase import create_client, Client
 
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret")
 
# =========================
# ADMIN LOGIN
# =========================
 
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
 
 
# =========================
# SUPABASE
# =========================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL:
    raise Exception("SUPABASE_URL environment variable not found")

if not SUPABASE_KEY:
    raise Exception("SUPABASE_KEY environment variable not found")

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)
 
BUCKET_NAME = "product-images"
 
 
# =========================
# HOME
# =========================
 
@app.route("/")
def home():
 
    products = (
        supabase
        .table("products")
        .select("*")
        .order("id", desc=True)
        .execute()
        .data
    )
 
    product_data = []
 
    for product in products:
 
        images = (
            supabase
            .table("product_images")
            .select("image")
            .eq("product_id", product["id"])
            .execute()
            .data
        )
 
        image_urls = []
 
        for img in images:
 
            image_path = img["image"]
 
            image_url = (
                f"{SUPABASE_URL}/storage/v1/object/public/"
                f"{BUCKET_NAME}/{image_path}"
            )
 
            image_urls.append(image_url)
 
        product_data.append({
            "product": product,
            "images": image_urls
        })
 
    return render_template(
        "index.html",
        products=product_data
    )
 
 
# =========================
# LOGIN
# =========================
 
@app.route("/login", methods=["GET", "POST"])
def login():
 
    if request.method == "POST":
 
        username = request.form["username"]
        password = request.form["password"]
 
        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):
 
            session["admin"] = True
 
            flash(
                "✅ Logged in successfully!",
                "success"
            )
 
            return redirect("/admin")
 
        flash(
            "❌ Invalid username or password",
            "danger"
        )
 
    return render_template("login.html")
 
 
# =========================
# CHECK
# =========================
 
@app.route("/check")
def check():
    return str(session.get("admin"))
 
 
# =========================
# LOGOUT
# =========================
 
@app.route("/logout")
def logout():
 
    session.clear()
 
    flash(
        "👋 Successfully returned to home and logged out!",
        "info"
    )
 
    return redirect("/")
 
 
# =========================
# ADMIN
# =========================
 
@app.route("/admin", methods=["GET", "POST"])
def admin():
 
    if not session.get("admin"):
        return redirect("/login")
 
    if request.method == "POST":
 
        images = request.files.getlist("images")
 
        # -------------------------
        # ADD PRODUCT
        # -------------------------
 
        product_response = (
            supabase
            .table("products")
            .insert({
                "name": request.form["name"],
                "category": request.form["category"],
                "price": request.form["price"],
                "stock": request.form["stock"],
                "sizes": request.form["sizes"],
                "pack": request.form["pack"],
                "description": request.form["description"]
            })
            .execute()
        )
 
        product = product_response.data[0]
        product_id = product["id"]
 
        # -------------------------
        # UPLOAD IMAGES
        # -------------------------
 
        for image in images:
 
            if image and image.filename:
 
                filename = secure_filename(
                    image.filename
                )
 
                # Prevent same filenames from overwriting
                # existing images
                filename = (
                    f"{product_id}_{filename}"
                )
 
                image_bytes = image.read()
 
                supabase.storage.from_(
                    BUCKET_NAME
                ).upload(
                    filename,
                    image_bytes,
                    {
                        "content-type": image.content_type
                    }
                )
 
                # Save image path in database
                supabase.table(
                    "product_images"
                ).insert({
                    "product_id": product_id,
                    "image": filename
                }).execute()
 
        flash(
            "✅ Product added successfully!",
            "success"
        )
 
        return redirect("/")
 
    return render_template("admin.html")
 
 
# =========================
# DELETE PRODUCT
# =========================
 
@app.route("/delete/<int:id>")
def delete_product(id):
 
    if not session.get("admin"):
        return redirect("/login")
 
    # Get images first
    images = (
        supabase
        .table("product_images")
        .select("image")
        .eq("product_id", id)
        .execute()
        .data
    )
 
    # Delete images from storage
    for img in images:
 
        try:
            supabase.storage.from_(
                BUCKET_NAME
            ).remove([
                img["image"]
            ])
        except Exception:
            pass
 
    # Delete image records
    supabase.table(
        "product_images"
    ).delete().eq(
        "product_id", id
    ).execute()
 
    # Delete product
    supabase.table(
        "products"
    ).delete().eq(
        "id", id
    ).execute()
 
    flash(
        "🗑 Product deleted successfully!",
        "success"
    )
 
    return redirect("/")
 
 
# =========================
# EDIT PRODUCT
# =========================
 
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_product(id):
 
    if not session.get("admin"):
        return redirect("/login")
 
    if request.method == "POST":
 
        (
            supabase
            .table("products")
            .update({
                "name": request.form["name"],
                "category": request.form["category"],
                "price": request.form["price"],
                "stock": request.form["stock"],
                "sizes": request.form["sizes"],
                "pack": request.form["pack"],
                "description": request.form["description"]
            })
            .eq("id", id)
            .execute()
        )
 
        flash(
            "✅ Product updated successfully!",
            "success"
        )
 
        return redirect("/")
 
    product = (
        supabase
        .table("products")
        .select("*")
        .eq("id", id)
        .single()
        .execute()
        .data
    )
 
    return render_template(
        "edit_product.html",
        product=product
    )
 
 
# =========================
# RUN
# =========================
 
if __name__ == "__main__":
    app.run(debug=True)
 