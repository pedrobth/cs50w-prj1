import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))

db = scoped_session(sessionmaker(bind=engine))

def main():
    try:
        file = open("books.csv")
        reader = csv.reader(file)
        #skip the header
        next(reader, None)

        # iterate into columns
        for isbn, title, author, year in reader:
            
            # insert data into session
            db.execute("INSERT INTO books (isbn, author, title, year) VALUES (:isbn, :author, :title, :year)", {"isbn": str(isbn), "author": author, "title": title, "year": year})
        # commit data to database
        db.commit()
    except:
        print("Error opening csv file check if it is in the same folder and if it's name is correct")
    

if __name__ == "__main__":
    main()