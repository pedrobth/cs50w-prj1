class Review:
    def __init__(self, user_id, book_id, score):
        self.user_id = user_id
        self.book_id = book_id
        self.score = score

# Although the class user wasn't direcly used in code, the practice of using classmethods, with decorators, with the option of easyer maintai
class User:
    def __init__(self, user_name, pass_hash, email, i=0):
        self.user_name = user_name
        self.pass_hash = pass_hash
        self.email = email
    
    @classmethod
    def from_generate(cls, amount):
        user_name = 'generated_user' + str(amount)
        pass_hash = 'GEN_u$er' + str(amount)
        email = 'generated_user' + str(amount) + "@fakedomain.com"
        return cls(user_name, pass_hash, email)

#user_1 = User('fake', 'P@ssw0rt', 'fake.user@domain.com')
#, print(user_1.email)
