import os
import requests

from flask import Flask, session, render_template, request, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from functools import wraps

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

KEY = "lK0xcyf8s0f7yGRPw3TcHw"

################################################
#verifica si la sesion esta iniciada
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function
    
################################################

### Ingresa a la main page si la sesion esta habilitada 
@app.route("/", methods=["POST", "GET"])
@login_required 
def login():
    id_user = session.get("user_id")
    user = db.execute("SELECT * FROM usuarios WHERE id=:id_user",{"id_user":id_user}).fetchone()

    user_name= user[0]

    return render_template("main.html", name = user_name)

### Verifica si el usuario existe y los casos que se ingrese mal la clave o el usuario

# LOGIN REQUERIMENT
@app.route("/login", methods=['GET', 'POST'])
def login_page():
    if request.method == "POST":
        log_name = request.form.get("log_name")
        log_password = request.form.get("log_password")

        if log_name is "":
            return render_template("login.html", message1="Usuario Invalido")
  
        if log_password is "":
            return render_template("login.html", message2="Clave invalida")

        user = db.execute("SELECT * FROM usuarios WHERE nombre=:name AND password=:password",{"name":log_name, "password":log_password}).fetchone()
    
        db.commit()
        if user:
            session["user_name"] = user[0]
            session["user_id"] = user[2]
            return redirect("/")
        else:
            return render_template("login.html", message3="Usuario o clave invalida")
    else: 
        session.clear()
        return render_template("login.html", message3="")
        


### verifica si el usuario existe y si no, ingresa un nuevo usuario a la base de datos

#REGISTRATION REQUERIMENT 
@app.route("/registro", methods=['GET', 'POST'])
def registro():
    # Get form information.
    reg_name = request.form.get("reg_name")
    reg_password = request.form.get("reg_password")

    if reg_name is None and reg_password is None:
        return render_template("registro.html", message1="")
    
    if reg_name is "":
        return render_template("registro.html", message1="Usuario no valido")

    if reg_password is "":
        return render_template("registro.html", message2="Clave invalida")

    #nos aseguramos que el usuario no exista  
       
    if db.execute("SELECT nombre FROM usuarios WHERE nombre= :name",{"name":reg_name}).rowcount == 1:
        return render_template("registro.html", message1="Usuario ya existe")
    db.commit()

    if reg_name is not "" and reg_password is not "":
        db.execute("INSERT INTO usuarios ( nombre, password) VALUES ( :nombre, :password)",
            {"nombre": reg_name, "password": reg_password})
        db.commit()
    
        user = db.execute("SELECT id FROM usuarios WHERE nombre= :name",{"name":reg_name}).fetchone()
        session['user_id'] = user[0]

        return redirect("/")
        
    return render_template("registro.html", message1="Usuario invalido")


# SEARCH REQUERIMENT 
@app.route("/libros", methods=["GET", "POST"])
def libros():
    if request.method == "POST":
        search = request.form.get("search")
        if search != "":
            # list the posible matches
            result = db.execute("SELECT * FROM books WHERE LOWER(isbn) LIKE :book OR title LIKE :book OR author LIKE :book", {"book": '%'+search+'%'}).fetchall()
            if not result:
                message = "No se encontraron resultados para:"
                return render_template("main.html", message=message, search=search)

            for libro in result:
                isbn = libro[1]
                goodreadsapi(isbn)
                print(libro[1])
            return render_template("libros.html", libros=result, search=search)
    
        else:
            message="Ingrese una busqueda"
            return render_template("main.html", message= message)
    else:
        redirect("/")


### Cierra la sesion 

# LOGOUT REQUERIMENT
@app.route("/logout")
def logout_page():
    session.clear()
    return redirect("/")

#Appi access
@app.route("/api/<string:isbn>", methods=["GET"])
def goodreadsapi(isbn):
    if request.method == "GET":
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": KEY, "isbns": isbn})
        if res.status_code == 200:
            res = res.json()
            return res
        else:
            return jsonify({"error":"Invalid book isbn"})

# Book page and book submition 
@app.route("/libros/<string:isbn_book>", methods=["GET", "POST"])
def book_detail(isbn_book):
    if request.method == "GET":
        book = db.execute("SELECT isbn FROM books WHERE isbn = :isbn_book", {"isbn_book":isbn_book}).fetchone()
        if book:
            #goodread review data
            res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": KEY, "isbns":isbn_book})
            if res.status_code == 200:

                res = res.json()
                res_goodreads = res["books"][0]

                average_rating = res_goodreads["average_rating"]
                isbn13 = res_goodreads["isbn13"]
                reviews_count = res_goodreads["reviews_count"]

                db.execute("UPDATE books SET reviews_count = :reviews_count, isbn13 = :isbn13, average_rating = :average_rating WHERE isbn = :isbn", {"reviews_count":reviews_count, "isbn13":isbn13, "average_rating":average_rating, "isbn":isbn_book})
                db.commit()
            
            detail = db.execute("SELECT * FROM books WHERE isbn = :isbn_book", {"isbn_book":isbn_book}).fetchone()

            reviews = db.execute("SELECT reviews.*, usuarios.id, usuarios.nombre FROM reviews INNER JOIN usuarios ON reviews.user_id = usuarios.id WHERE isbn = :isbn", {"isbn":isbn_book}).fetchall()
            avg_book = {}
            if reviews:
                avg_book = {"avg1":[],"avg2":[],"avg3":[],"avg4":[],"avg5":[]}
                for review in reviews:
                    if review[3] == 1:
                        avg_book["avg1"].append(review[3])
                    elif review[3] == 2:
                        avg_book["avg1"].append(review[3])
                    elif review[3] == 3:
                        avg_book["avg1"].append(review[3])
                    elif review[3] == 4:
                        avg_book["avg1"].append(review[3])
                    elif review[3] == 5:
                        avg_book["avg1"].append(review[3])

            return render_template("libros.html", book_detail=detail, reviews=reviews)
        else:
            return redirect("error/404")
    
    #review submition 
    if request.method == "POST":
        review_isbn = request.form.get("book_id_review")
        book_id = request.form.get("book_id")

        book_review = request.form.get("book_review")
        book_rating = request.form.get("book_rating")
        
        if book_review or book_rating or review_isbn:
            result = db.execute("SELECT * FROM reviews WHERE isbn = :isbn AND user_id = :usuario", {"isbn":review_isbn, "usuario":session["user_id"]}).fetchone()
            if result:
                db.execute("UPDATE reviews SET rating = :rating, commentary = :commentary WHERE id = :id", {"rating":book_rating, "commentary":book_review, "id":result.id})
                db.commit()
            else:
                db.execute("INSERT INTO reviews (isbn, user_id, rating, commentary) VALUES (:isbn, :user_id, :rating, :commentary)", {"isbn":review_isbn, "user_id":session["user_id"], "rating":book_rating, "commentary":book_review})
                db.commit()
            return redirect("/libros/"+review_isbn)
    else:
        return redirect("error/404")
    
   

@app.route("/error/404")
def page404():
    return render_template("error_usuario.html")
