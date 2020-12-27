import os

from functions import score_generator, create_user, insert_reviews
from classes import User
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


gen_number = 107
#users = user_generator(gen_number)
scores = score_generator(gen_number, 4.82)
#print(scores)
i = 0
book_id = 73
# it could check first if some previous generated users alrady reviwed this particular book
max_user_id = db.execute("SELECT MAX(user_id) FROM users").fetchone()
# test if there is come user on the database
if max_user_id[0] != None:
    next_user = 1 + max_user_id[0]
else:
    next_user = 1

print(f"generated :{gen_number} and created users from: {next_user}")
for score in scores:
    # call the class method to generate users
    user = User.from_generate(next_user)
    # create user retrieve 0 if everything runs ok
    if create_user(user.user_name, user.pass_hash, user.pass_hash, user.email) != 0:
        print(f'oops, user could not be inserted in database, check error number: {create_user}')
    if insert_reviews(int(next_user), int(round(score, 4)), int(book_id)) != 0:
        print("could not insert review")
    #print(f'review: {review['user_id'], review['book_id']} inserted with score: {review['score']}')
    
    next_user += 1

print(f"till: {next_user}")
