import os

from flask import Flask, session, render_template, redirect, request, url_for, jsonify, make_response
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.wrappers import Response
from functions import *

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

"""# configure Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))"""

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/", methods=["POST", "GET"])
@login_required
def index():
    if request.method == "POST":
        # retrieve search choice from user
        search_option = request.form.get("inlineRadioOptions")
        book_info = {}
        # test for isbn search chosen
        if not search_option:
            return feedback(" Search type is mandatory", 412)
        if search_option == "isbn":
            book_info = search_isbn(request.form.get("search_input"))
        # test for author search chosen
        if search_option == "author":
            book_info = search_author(request.form.get("search_input"))
        # test for title search chosen
        if search_option == "title":
            book_info = search_title(request.form.get("search_input"))
        # the book is not on the database
        if not book_info:
            return feedback(" item not found", 404)

        # remember search list
        session["books"] = book_info
        return redirect("books")
    return render_template("search.html")

@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        user_name = request.form.get("user_name")
        password = request.form.get("password")
        pass_confirm = request.form.get("pass_confirm")
        email = request.form.get("email").lower()
        result = create_user(user_name, password, pass_confirm, email)
        
        # all good
        if result == 0:
            # redirect to login
            return redirect("/login")

        # missing field(s)
        if result == 1:
            return feedback(" all fields are mandatory, also consider to active javaScript for a better expirience", 404)
        
        # existing account
        if result == 2:
            return feedback(" There is an existing account for that email address. If you don't remember your password try to reset it.", 404)

        # username taken
        if result == 3:
            return feedback(" This user name is taken, try another one", 404)
        
        # weak password
        if result == 4:
            return feedback(" your password must contain from 8 to 30 characters with letters, numbers and special characteres", 404)
        
        # password doesn't match with password confirmation
        if result == 5:
            return feedback(" Password and password confirmation must match", 404)
        
        # user registration failed
        if result == 6:
            return feedback(" Could not register", 404)
        
        return feedback(" Something went wrong, consider reporting us with that error message - error 827")
        
    return render_template("register.html")

@app.route("/books")
@login_required
def books():
    if not session["books"]:
        redirect("/")
    # prepare session to book_detail
    session["books"]
    session['book'] = {}
    session['good_reads_result'] = {}
    session['user_score'] = 5
    session['text_review'] = "n"
    return render_template("books.html", books_list=session['books'])

@app.route("/detail/<string:isbn>", methods=["GET", "POST"])
@login_required
def book_view(isbn):
    # clear any previous book info on the session
    del session['book']
    del session['good_reads_result']
    del session['user_score']
    del session['text_review']

    # select the specific book into session['books'] list
    book_index = next((index for (index, b) in enumerate(session["books"]) if b['isbn'] == isbn), -1)
    
    # remember book complete info
    session["book"] = int(book_index)

    # declare a dictionary to organize data
    book_info = {'book_dict': {}, 'good_reads_result': {}}
    # get goodreads information
    good_reads_raw = import_review(isbn)
    # organize goodreads relevant information
    book_info['good_reads_result'] = {
        'work_ratings_count': good_reads_raw["books"][0]["work_ratings_count"], 
        'average_rating': good_reads_raw["books"][0]["average_rating"]
    }
    # get reviews from database, it will return book_dict["review_count"] = 0 and book_dict["avrg_score"] = "-" in case there are none and all the book_info (author, isbn, title, year)
    book_info['book_dict'] = get_reviews(isbn)

    # query database for user review and assign it to dictionary
    user_review = select_user_review(
        session['user_id'], 
        session['books'][book_index]['book_id']
        )
    
    # calculate rating arithmetic mean and total reviews
    balanced_ratings = balance_ratings(
        reads_rate_count=book_info['good_reads_result']['work_ratings_count'], 
        reads_avrg_rating=book_info['good_reads_result']['average_rating'], 
        db_avrg_score=book_info['book_dict']['avrg_score'], db_review_count=book_info['book_dict']['review_count']
    )
    # organize data in a dictionary
    book_info['book_dict']['total_reviews'] = balanced_ratings['book_dict']['total_reviews']
    book_info['book_dict']['balanced_score'] = balanced_ratings['book_dict']['balanced_score']

    # the book_info could be more concise, without all data that is already inside session books (author, isbn, title, year). Although this solution may use less computer resources it the code gets more confusing. Prioritising clean and comprehensible code the information is centralised in one dict key.
    session['book_dict'] = book_info['book_dict']
    session['good_reads_result'] = book_info['good_reads_result']
    session['user_score'] = user_review['score']
    session['text_review'] = user_review['text_review']
    # check if user can review that book
    if session['user_score'] == "-":
                
        # wait for user review
        if request.method == "POST":
            # delete previous data on session
            try:
                del session['user_score']
                session['user_score'] = int(request.form.get("book_rate"))
                if request.form.get("text_review"):
                    session['text_review'] = str(request.form.get("text_review"))
                # insert user review
                reviewed = insert_reviews(
                    user=session['user_id'], 
                    gen_review=int(session['user_score']), 
                    book_id=book_info['book_dict']["book_id"],
                    text_review=session['text_review']
                )
                if reviewed != 0:
                    return feedback(" Could not submit your review, check if it has more than 250 characters", 412)
                return feedback(
                f" you reviewed {session['book_dict']['title']} with a {str(session['user_score'])}.0 score ", 200
                )
            except ValueError:
                return feedback(" Could not complete your request", 400)
           
            return feedback(
                f" you reviewed {session['book_dict']['title']} with a {str(session['user_score'])}.0 score ", 200
            )
        return render_template("detail.html", 
            good_reads_result=session['good_reads_result'], 
            user_score=session['user_score'],
            text_review=session['text_review'], 
            book_dict=session['book_dict'], 
            title=book_info["book_dict"]["title"]
        )
    # logged user already reviwed that book
    else:
        # round average score
        try:
            book_info['book_dict']['avrg_score'] = round(book_info['book_dict']['avrg_score'], 2)
        except:
            pass # average_score was not a number
        # test if user wrote a review
        if not session['text_review']:
            if request.method == "POST":
                session['text_review'] = str(request.form.get("text_review"))
                    
                update_review(
                        user_id=session['user_id'], 
                        score=str(session['user_score']), 
                        book_id=book_info['book_dict']["book_id"],
                        text_review=session['text_review']
                    )
                return render_template("detail.html", 
                            good_reads_result=(session['good_reads_result']), 
                            user_score=str(session['user_score']), 
                            text_review=session['text_review'], 
                            book_dict=(session['book_dict']), 
                            title=book_info["book_dict"]["title"]
                        )
        
    # 
    return render_template("detail.html", 
            good_reads_result=(session['good_reads_result']), 
            user_score=str(session['user_score']), 
            text_review=session['text_review'], 
            book_dict=(session['book_dict']), 
            title=book_info["book_dict"]["title"]
        )
    
@app.route("/login", methods=["GET", "POST"])
def login():
    # wait for user action
    if request.method == "POST":
        user_name = request.form.get("user_name")
        password = request.form.get("password")
        # ensure to have all info 
        if not user_name or not password:
            # notify user if any field is missing
            return feedback(" User name and password are mandatory", 412)
        # run all the checkup (database info selection and )
        user = log(user_name, password)
        if not user:
            return feedback(" User not found or password does not match", 404)
        # remember user_id
        session["user_id"] = user
        return redirect("/")
    # load the page to login
    return render_template("login.html")

@app.route("/api/<isbn>", methods=["GET"])
def api_isbn(isbn):
    book_api = get_reviews(isbn)
    if not book_api:
        return make_response(jsonify("404, could not find your request"), 404)
    return(jsonify(book_api))


@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect("/")
    
# allow to keep track of changes when debug=true
if __name__ == '__main__':
    app.run(debug=False)