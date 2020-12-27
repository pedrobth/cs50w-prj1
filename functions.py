import os
import re
import numpy as np
import math
import itertools

from functools import wraps
from flask import Flask, g, request, redirect, url_for, session, render_template, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
from classes import User, Review

try:
    # Set up database
    engine = create_engine(os.getenv("DATABASE_URL"), pool_size=15, max_overflow=5)
    db = scoped_session(sessionmaker(bind=engine))
except:
    print(" Could not set database ")

def login_required(f):
    """check logged user, if not redirect to login page https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def log(user_name, password):
    # set a dictionary
    user_dict = {'pass_hash': 'nouser'}

    # iterates into user table info
    for row in db.execute("SELECT * FROM users WHERE (user_name= :user_name)", {"user_name": user_name}).fetchall():
        # test if user exists and if password match
        if row == None:
            return(None)
        # set info into the dictionary
        user_dict = {head: value for head, value in row.items()}

    # check if password match
    if check_password_hash(user_dict["pass_hash"], password) == False:
        return(None)

    # all good
    else:
        # return user_id
        return(user_dict['user_id'])

def feedback(msg, code=400):
    """return feebback for errors or bad usage"""
    return render_template("feedback.html", msg=msg, code=code), code

def create_user(user_name, password, pass_confirm, email):

    # check if all fields exists
    if not user_name or not password or not pass_confirm or not email:
        return(1)

    # check if email is taken
    if db.execute("SELECT email FROM users WHERE email = :mail", {"mail": email}).fetchone() != None:
        return(2)

    # check if username is taken
    if db.execute("SELECT user_name FROM users WHERE user_name = :user_nm", {"user_nm": user_name}).fetchone() != None:
        return(3)

    # check password strength
    ''' https://www.codespeedy.com/check-the-password-strength-in-python/'''
    if (bool(re.match('((?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!"#$%&()*+,-./:;<=>?@[\]^_`{|}~´¨çÇ]).{8,30})', password)) == False):
        return(4)

    # check if password match with password confirmation
    if password != pass_confirm:
        return (5)

    # hash password
    pass_hashed = generate_password_hash(password)

    # insert all info in database
    try:
        db.execute("INSERT INTO users (user_name, pass_hash, email) VALUES (:user_nm, :hash_pass, :mail)", {'user_nm': user_name, 'hash_pass': pass_hashed, 'mail': email})
        db.commit()
        return(0)
    except:
        return(6)

def get_reviews(isbn):
    """ query database for reviews via ISBN, if there are no reviews, it will ser review_count to int(0) and the reviews count to '-'  and query the database for the rest of the book info it will return a dict with the info"""

    book_dict = {}
    # iterate into database information for the given book id
    for row in db.execute("SELECT * FROM books_scores WHERE (isbn = :isbn) LIMIT(15)", {"isbn": isbn}).fetchall():
        # put the results into a dicti
        book_dict = {head: value for head, value in row.items()}

    # Test if book has reviews on database
    if not book_dict:
        # query database for book info
        try:
            book_dict = search_isbn(isbn)[0]
            # set info that does not exist in database
            book_dict["review_count"] = "0"
            book_dict["avrg_score"] = "-"
            return(book_dict)
        except:
            return(None)
    else:
        book_dict['avrg_score'] = round(book_dict['avrg_score'], 2)
    return(book_dict)

def balance_ratings(reads_rate_count, reads_avrg_rating, db_avrg_score, db_review_count):
    """ this function will recieve the good reads and database review and balance the results using a arithmetic mean. It will return:
    book_info{
        "book_dict":{
            'total_reviews':    ,
            'balanced_score':   
        }
    }
    """
    book_info = {'book_dict':{}}

    # scores/reviews exists in database
    if db_avrg_score != "-":
        # prepare goodreads data
        gr_score_times_rate_count = (reads_rate_count * float(reads_avrg_rating))

        # prepare database data
        db_score_times_rate_count = int(db_review_count) * float(db_avrg_score)

        # calculate balanced score and put it into the dictionary
        book_info['book_dict']['balanced_score'] = round((gr_score_times_rate_count + db_score_times_rate_count) / (reads_rate_count + int(db_review_count)), 2)
    # no reviews for that book in database
    else:
        # the average rating, in that case, is = imported from good reads
        book_info['book_dict']['balanced_score'] = reads_avrg_rating

    # organize all in a dict would be easier to use a classes
    book_info["book_dict"]['total_reviews'] = str(reads_rate_count + int(db_review_count))

    return(book_info)

def select_user_review(user_id, book_id):
    """
    Given user id, and book this method search if that user already reviewed that book and return a dict with reviewed score. If the user did not reviwed that book it will return:
    score: '-'
    """
    review = db.execute("SELECT * FROM reviews WHERE (book_id = :book_id AND user_id = :user_id)", {'user_id': user_id, 'book_id': book_id}).fetchall()
    # check user book review existence
    if not review:
        # set '-' as a score
        user_review = {'score': '-', 'text_review': None}
        return(user_review)
    # organize data before passing it
    user_review = {
        'score': review[0][2],
        'text_review': review[0][3]
        }
    return(user_review)

def update_review(user_id, book_id, score, text_review):
    if len(text_review) > 250:
        return feedback("Text review are 250 characters limited", 412)
    try:
        db.execute("UPDATE reviews SET(user_id, book_id, score, text_review) VALUES(:user_id, :book_id, :score, text_review) WHERE (book_id=:book_id  AND user_id=:user_id '2436')", {'user_id': user_id, 'book_id': book_id, 'score': score, 'text_review': text_review})
        db.commit()
        return(0)
    except:
        return(1)

def score_generator(reviews_qty, avrg):

    """ returns a list of scores from 0 to 1000 normal distributed with a given average and standard deviation. Supported by empirical rule there is 1 chance in 390,682,215,445 to get a result out of the max score with 7 standard deviation from the mean. Even with the odds in our side the max score was decreased by one unit and added one to the min value, also it was used 8 standard deviation intervals apart from the mean, this will give more stability to the code but consider to add a test for numbers out of range, if it breaks the logic (precision is 2 decimal)"""

    # test for a 5 star review
    if avrg == 5.00:
        # return a list with (eviews_qty) 5 star scores
        return([5] * reviews_qty)
    # test for a 0 star review
    elif avrg == 1.00:
        # return a list with (eviews_qty) 0 star scores
        return([0] * reviews_qty)
    # ensure the decimals used in average
    avrg = round(avrg, 2)
    # set variables to populate the samples
    max_score = int(5)
    min_score = int(2)
    std_dev_intervals = 8

    # calculate the standard deviation
    if avrg > 2.5:
        std_deviation = (max_score - avrg) / std_dev_intervals
    else:
        std_deviation = (avrg - min_score) / std_dev_intervals

    # return generated list
    return(np.random.normal(avrg, std_deviation, reviews_qty))

def import_review(isbn):
    """
    API code for good reads platform returns s json with all book information
    """
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "wu9Ik89SrqNlAmfleeHw", "isbns": isbn})
    print(res)
    return(res.json())

def insert_reviews(user, gen_review, book_id, text_review=None):

    """
    insert reviews will accept variables (user, gen_review, book_id, text_review=None) and insert it in the database. return 0 if succeded and 1 if not.
    Raw sql e.g.:
    INSERT INTO "reviews" ("user_id", "book_id", "score") VALUES ('369', '365', '100');
    """
    gen_review = round(gen_review, 3)
    try:
        if len(text_review) > 250:
            return (412)
    except:
        pass
    try:
        db.execute("INSERT INTO reviews (user_id, book_id, score, text_review) VALUES (:user_id, :book_id, :score, :text_review)", {'user_id': user, 'book_id': book_id, 'score': gen_review, 'text_review': text_review})
        db.commit()
        return(0)
    except:
        return(1)

def search_isbn(isbn):
    """
    search for book by isbn, partial number is allowed return 0 if succeded and 1 if not.
    raw sql e.g.:
    SELECT * FROM "books" WHERE "isbn" LIKE '%0380%' LIMIT 15;
    """
    book_list = []
    book_dict = {}
    try:
        # iterate into each of possible results
        for row in db.execute("SELECT * FROM books WHERE (books.isbn LIKE :isbn) LIMIT(15)", {"isbn": '%' + isbn + '%'}).fetchall():
            # organize the result into a dict
            book_dict = {head: value for head, value in row.items()}
            # add (append) that result to the list
            book_list.append(book_dict)
        # return data
        return(book_list)
    except:
        return(0)

def search_author(author):
    """
    search for book by author, capitalization is ignored and partial name is allowed return 0 if succeded and 1 if not.
    raw sql e.g.:
    SELECT * FROM "books" WHERE "author" ILIKE '%john%' LIMIT 15;
    """
    book_list = []
    book_dict = {}
    try:
        # iterate into each of possible results limited of 10 results to avoid data extraction
        for row in db.execute("SELECT * FROM books WHERE (books.author ILIKE :author) LIMIT(15)", {"author": '%' + author + '%'}).fetchall():
            # organize each result into a dict
            book_dict = {head: value for head, value in row.items()}
            # add (append) that result to the list
            book_list.append(book_dict)
        # return data
        return(book_list)
    except:
        return(0)

def search_title(title):
    """
    search for book title, capitalization is ignored and partial title is allowed return 0 if succeded and 1 if not.
    raw sql e.g.:
    SELECT * FROM "books" WHERE "title" ILIKE '%The Thief%' LIMIT 15;
    """

    book_list = []
    book_dict = {}
    try:
        # iterate into each of possible results
        for row in db.execute("SELECT * FROM books WHERE (books.title ILIKE :title) LIMIT(15)", {"title": '%' + title + '%'}).fetchall():
            # organize one result into a dict
            book_dict = {head: value for head, value in row.items()}
            # add (append) that result to the list
            book_list.append(book_dict)
        # return data
        return(book_list)
    except:
        return(0)
