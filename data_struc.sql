/* The isbn 10 digit schema has the last digit calculated. The possible values for a check digit calculated by the procedure, called modulus 11, is from zero to ten. In order to show a check digit of ten as one character, the convention is adopted of using the letter "X" to stand for a ten, like a Roman ten. https://isbn-information.com/the-10-digit-isbn.html

The 13 digit schema has the same possibility - the letter "X" representing the digit

So the isbn and isbn13 cannot be an integer type, unless we separate the digit, in addition some isbn numbers start with "0", and if we try to assign those to the database those "0" will desapear, so it might be a VARCHAR
*/
CREATE TABLE books(
    book_id SERIAL PRIMARY KEY,
    author VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    year INT NOT NULL CHECK (year > 1484),
    isbn VARCHAR
);

CREATE TABLE users(
    user_id SERIAL PRIMARY KEY,
    user_name VARCHAR NOT NULL UNIQUE,
    pass_hash VARCHAR NOT NULL,
    email VARCHAR NOT NULL UNIQUE 
);

CREATE TABLE reviews(
    user_id INT REFERENCES users(user_id) NOT NULL,
    book_id BIGINT REFERENCES books(book_id) NOT NULL,
    score REAL NOT NULL CHECK (score >= 1 AND score <= 5),
    text_review VARCHAR(256)
    PRIMARY KEY (book_id, user_id)
);


CREATE VIEW books_scores AS
    SELECT
        b.book_id,
        b.author,
        b.title,
        b.year,
        b.isbn,
        count(r.*) AS review_count,
        avg(r.score) AS avrg_score
    FROM (books b
        RIGHT JOIN reviews r 
            ON (r.book_id = b.book_id))
        GROUP BY 
            b.book_id, 
            b.author, 
            b.title, 
            b.year,
            b.isbn;