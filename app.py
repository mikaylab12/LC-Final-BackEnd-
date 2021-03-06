import hmac
import sqlite3
from smtplib import SMTPRecipientsRefused
from flask import *
from flask_jwt import *
from flask_cors import *
from flask_mail import Mail, Message
from datetime import timedelta


# initializing the database
class Database(object):
    def __init__(self):
        self.conn = sqlite3.connect('adoption_centre.db')
        self.cursor = self.conn.cursor()

    # to commit multiple things
    def to_commit(self, query, values):
        self.cursor.execute(query, values)
        self.conn.commit()

    # one commit
    def single_commit(self, query):
        self.cursor.execute(query)
        self.conn.commit()

    # to fetch all
    def fetch_all(self):
        return self.cursor.fetchall()

    # to fetch one
    def fetch_one(self):
        return self.cursor.fetchone()


# creating a user object
class User(object):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password


# function to create user table
def init_user_table():
    conn = sqlite3.connect('adoption_centre.db')
    cursor = conn.cursor()
    print("Opened database successfully")
    cursor.execute("CREATE TABLE IF NOT EXISTS users "
                   "(user_number INTEGER PRIMARY KEY AUTOINCREMENT,"
                   "user_id TEXT NOT NULL, "
                   "first_name TEXT NOT NULL,"
                   "last_name TEXT NOT NULL, "
                   "email_address TEXT NOT NULL, "
                   "contact_number TEXT NOT NULL, "
                   "username TEXT unique, "
                   "password TEXT NOT NULL)")
    print("Users table created successfully")
    conn.close()


# calling function to create users table
init_user_table()


# fetching users from the user table
def fetch_users():
    db = Database()
    query = "SELECT * FROM users"
    db.single_commit(query)
    registered_users = db.fetch_all()

    new_data = []

    for data in registered_users:
        new_data.append(User(data[0], data[6], data[7]))
    return new_data


# calling function to fetch all users
all_users = fetch_users()


username_table = {u.username: u for u in all_users}
userid_table = {u.id: u for u in all_users}


# function to get unique token upon registration
def authenticate(username, password):
    user = username_table.get(username, None)
    if user and hmac.compare_digest(user.password.encode('utf-8'), password.encode('utf-8')):
        return user


# function to identify user
def identity(payload):
    user_id = payload['identity']
    return userid_table.get(user_id, None)


# initializing app
app = Flask(__name__)
CORS(app)
app.debug = True
app.config['SECRET_KEY'] = 'super-secret'
app.config["JWT_EXPIRATION_DELTA"] = timedelta(days=1)      # allows token to last a day
app.config['MAIL_SERVER'] = 'smtp.gmail.com'                # server for email to be sent on
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'mikayladummy2@gmail.com'     # sender email address
app.config['MAIL_PASSWORD'] = 'Dummy123!'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)
jwt = JWT(app, authenticate, identity)


@app.route('/protected')
@jwt_required()
def protected():
    return '%s' % current_identity


# route to register user
@app.route('/register/', methods=["POST"])
def registration():
    response = {}
    db = Database()
    try:
        id_number = request.json['user_id']
        first_name = request.json['first_name']
        last_name = request.json['last_name']
        email = request.json['email_address']
        contact = request.json['contact_number']
        username = request.json['username']
        password = request.json['password']
        if int(len(contact)) > 10 or int(len(contact)) < 10:
            response['message'] = "Please enter a valid phone number that consists of 10 digits."
            response['status_code'] = 400
            return response
        if int(len(id_number)) > 13 or int(len(id_number)) < 13:
            response['message'] = "Please enter a valid ID number that consists of 13 digits."
            response['status_code'] = 400
            return response
        if int(contact) == str:
            response['message'] = "Please enter a phone number consisting of digits only."
            response['status_code'] = 400
            return response
        else:
            query = "INSERT INTO users(user_id, first_name, last_name, email_address, contact_number, username, " \
                    "password) VALUES(?, ?, ?, ?, ?, ?, ?)"
            values = (id_number, first_name, last_name, email, contact, username, password)
            db.to_commit(query, values)

            msg = Message('Welcome Email', sender='mikayladummy2@gmail.com', recipients=[email])
            # message for the email
            msg.body = "Welcome " + str(username) + ", "\
                       "\n\nThank you for registering with us! " \
                       "\n\nWe look forward to completing your family with one of our furry friends. " \
                       "\n\nAdopt, don't only shop! \n\n Have a lovely day further!"
            mail.send(msg)

            response["message"] = "Successful Registration"
            response["status_code"] = 201
            return response
    except SMTPRecipientsRefused:
        response['message'] = "Please enter a valid email address."
        response['status_code'] = 400
        return response
    except ValueError:
        response['message'] = "Please enter a valid phone number containing digits only."
        response['status_code'] = 401
        return response
    except TypeError:
        response['message'] = "Please enter a valid phone number containing digits only."
        response['status_code'] = 402
        return response
    except sqlite3.IntegrityError:
        response['message'] = "Username already exists"
        response['status_code'] = 404
        return response


# route for user login
@app.route('/login/', methods=["POST"])
def user_login():
    response = {}
    if request.method == "POST":
        username = request.json['username']
        password = request.json['password']
        conn = sqlite3.connect("adoption_centre.db")
        cur = conn.cursor()
        query = f"SELECT * FROM users WHERE username= '{username}' and password = '{password}'"
        cur.execute(query)
        if not cur.fetchone():
            response['message'] = "Please enter valid credentials."
            response['status_code'] = 400
            return response
        else:
            response['message'] = "Welcome '" + username + "'!"
            response['status_code'] = 200
            return response
    else:
        return "Wrong Method"


# route to show all users
@app.route('/show-users/', methods=["GET"])
def show_users():
    response = {}
    db = Database()
    query = "SELECT * FROM users"
    db.single_commit(query)
    users = db.fetch_all()

    response['status_code'] = 200
    response['data'] = users
    return response


# calling function to show all users
all_users = show_users()


# route to edit user
@app.route('/edit-user/<int:user_number>/', methods=["PUT"])
def edit_user(user_number):
    response = {}
    db = Database()

    if request.method == "PUT":
        with sqlite3.connect('adoption_centre.db'):
            data_receive = dict(request.json)
            put_data = {}
            # edit user ID number
            if data_receive.get("user_id") is not None:
                put_data["user_id"] = data_receive.get("user_id")
                query = "UPDATE users SET user_id =? WHERE user_number=?"
                values = (put_data["user_id"], str(user_number))
                db.to_commit(query, values)

                response['user_id'] = "ID number update was successful."
                response['status_code'] = 200
            # edit user's first name
            if data_receive.get("first_name") is not None:
                put_data["first_name"] = data_receive.get("first_name")
                query = "UPDATE users SET first_name =? WHERE user_number=?"
                values = (put_data["first_name"], str(user_number))
                db.to_commit(query, values)

                response['first_name'] = "First name update was successful."
                response['status_code'] = 200
            # edit user's last name
            if data_receive.get("last_name") is not None:
                put_data['last_name'] = data_receive.get('last_name')
                query = "UPDATE users SET last_name =? WHERE user_number=?"
                values = (put_data["last_name"], str(user_number))
                db.to_commit(query, values)

                response["last_name"] = "Last name updated successfully"
                response["status_code"] = 200
            # edit user's email address
            if data_receive.get("email_address") is not None:
                put_data['email_address'] = data_receive.get('email_address')
                query = "UPDATE users SET email_address =? WHERE user_number=?"
                values = (put_data["email_address"], str(user_number))
                db.to_commit(query, values)

                response["email_address"] = "Email address updated successfully"
                response["status_code"] = 200
            # edit user's contact number
            if data_receive.get("contact_number") is not None:
                put_data['contact_number'] = data_receive.get('contact_number')
                query = "UPDATE users SET contact_number =? WHERE user_number=?"
                values = (put_data["contact_number"], str(user_number))
                db.to_commit(query, values)

                response["contact_number"] = "Contact Number updated successfully"
                response["status_code"] = 200
            # edit user's username
            if data_receive.get("username") is not None:
                put_data['username'] = data_receive.get('username')
                query = "UPDATE users SET username =? WHERE user_number=?"
                values = (put_data["username"], str(user_number))
                db.to_commit(query, values)

                response["username"] = "Username updated successfully"
                response["status_code"] = 200
            # edit user's password
            if data_receive.get("password") is not None:
                put_data['password'] = data_receive.get('password')
                query = "UPDATE users SET password =? WHERE user_number=?"
                values = (put_data["password"], str(user_number))
                db.to_commit(query, values)

                response["password"] = "Password updated successfully"
                response["status_code"] = 200
            return response


# route to delete user
@app.route("/delete-user/<int:user_number>")
def delete_user(user_number):
    response = {}
    db = Database()
    query = "DELETE FROM users WHERE user_number= ' " + str(user_number) + " ' "
    db.single_commit(query)
    response['status_code'] = 200
    response['message'] = "User deleted successfully."
    return response


# route to view single profile using user number
@app.route('/view-profile/<int:user_number>/', methods=["GET"])
def view_profile(user_number):
    response = {}
    if request.method == "GET":
        with sqlite3.connect("adoption_centre.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_number=" + str(user_number))
            data = cursor.fetchall()
            if data == []:
                return "User does not exit"
            else:
                response['message'] = "User retrieved successfully"
                response['data'] = data
                response['status_code'] = 200
        return response


# route to view single profile using username and password
@app.route('/user-profile/<username>/<password>', methods=["PATCH"])
def user_profile(username, password):
    response = {}
    if request.method == "PATCH":
        with sqlite3.connect("adoption_centre.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username='" + str(username) + "' "
                           "and password ='" + str(password) + "'")
            data = cursor.fetchall()
            if data == []:
                return "User does not exit"
            else:
                response['message'] = "User retrieved successfully"
                response['data'] = data
                response['status_code'] = 200
        return response


# creating an animals object
class Animals(object):
    def __init__(self, animal_number, animal_name, animal_type, animal_breed, animal_age, animal_gender, animal_price,
                 animal_description, animal_image):
        self.animal_number = animal_number
        self.animal_name = animal_name
        self.animal_type = animal_type
        self.animal_breed = animal_breed
        self.animal_age = animal_age
        self.animal_gender = animal_gender
        self.animal_price = animal_price
        self.animal_description = animal_description
        self.animal_image = animal_image


# function to create an animals table
def init_animal_table():
    db = Database()
    query = ("CREATE TABLE IF NOT EXISTS animals "
             "(animal_number INTEGER PRIMARY KEY AUTOINCREMENT, "
             "animal_name TEXT NOT NULL, "
             "animal_type TEXT NOT NULL, "
             "animal_breed TEXT NOT NULL, "
             "animal_age TEXT NOT NULL, "
             "animal_gender TEXT NOT NULL, "
             "animal_price TEXT NOT NULL, "
             "animal_description TEXT NOT NULL, "
             "animal_image TEXT NOT NULL)")
    db.single_commit(query)
    print("Animals table created successfully.")


# calling function to create animals table
init_animal_table()


# route to show all animals
@app.route('/show-animals/', methods=["GET"])
def show_animals():
    response = {}
    db = Database()
    query = "SELECT * FROM animals"
    db.single_commit(query)
    animals = db.fetch_all()

    response['status_code'] = 200
    response['data'] = animals
    return response


# calling function to show all animals
all_animals = show_animals()


# route to add an adoption animal
@app.route('/add-animal/', methods=["POST"])
# @jwt_required()
def add_animal():
    response = {}
    db = Database()
    if request.method == "POST":
        name = request.json['animal_name']
        type = request.json['animal_type']
        breed = request.json['animal_breed']
        age = request.json['animal_age']
        gender = request.json['animal_gender']
        price = request.json['animal_price']
        description = request.json['animal_description']
        image = request.json['animal_image']
        if name == '' or type == '' or breed == '' or age == '' or gender == '' or price == '' or description == '' or image == '':
            return "Please fill in all entry fields"
        else:
            query = "INSERT INTO animals (animal_name, animal_type, animal_breed, animal_age, animal_gender, " \
                    "animal_price, animal_description, animal_image) VALUES(?, ?, ?, ?, ?, ?, ?, ?)"
            values = (name, type, breed, age, gender, price, description, image)
            db.to_commit(query, values)

            response["status_code"] = 201
            response['description_message'] = "Animal added successfully"
            return response


# route to delete single existing adoption animal using the animal's ID
@app.route("/delete-animal/<int:animal_number>")
# @jwt_required()
def delete_animal(animal_number):
    response = {}
    db = Database()
    query = "DELETE FROM animals WHERE animal_number=" + str(animal_number)
    db.single_commit(query)
    response['status_code'] = 200
    response['message'] = "Animal deleted successfully."
    return response


# route to edit single existing adoption animal using the animal's ID
@app.route('/edit-animal/<int:animal_number>/', methods=["PUT"])
# @jwt_required()
def edit_animal(animal_number):
    response = {}
    db = Database()

    if request.method == "PUT":
        with sqlite3.connect('adoption_centre.db'):
            data_received = dict(request.json)
            put_data = {}
            # edit animal's ID
            if data_received.get("animal_name") is not None:
                put_data["animal_name"] = data_received.get("animal_name")
                query = "UPDATE animals SET animal_name =? WHERE animal_number=?"
                values = (put_data["animal_name"], animal_number)
                db.to_commit(query, values)

                response['animal_name'] = "Animal name update was successful."
                response['status_code'] = 200
            # edit animal's type
            if data_received.get("animal_type") is not None:
                put_data['animal_type'] = data_received.get('animal_type')
                query = "UPDATE animals SET animal_type =? WHERE animal_number=?"
                values = (put_data["animal_type"], str(animal_number))
                db.to_commit(query, values)

                response["animal_type"] = "Animal type updated successfully"
                response["status_code"] = 200
            # edit animal's breed
            if data_received.get("animal_breed") is not None:
                put_data['animal_breed'] = data_received.get('animal_breed')
                query = "UPDATE animals SET animal_breed =? WHERE animal_number=?"
                values = (put_data["animal_breed"], str(animal_number))
                db.to_commit(query, values)

                response["animal_breed"] = "Animal breed updated successfully"
                response["status_code"] = 200
            # edit animal's age
            if data_received.get("animal_age") is not None:
                put_data["animal_age"] = data_received.get("animal_age")
                query = "UPDATE animals SET animal_age =? WHERE animal_number=?"
                values = (put_data["animal_age"], animal_number)
                db.to_commit(query, values)

                response['animal_age'] = "Animal age update was successful."
                response['status_code'] = 200
            # edit animal's gender
            if data_received.get("animal_gender") is not None:
                put_data['animal_gender'] = data_received.get('animal_gender')
                query = "UPDATE animals SET animal_gender =? WHERE animal_number=?"
                values = (put_data["animal_gender"], str(animal_number))
                db.to_commit(query, values)

                response["animal_gender"] = "Animal gender updated successfully"
                response["status_code"] = 200
            # edit animal's price
            if data_received.get("animal_price") is not None:
                put_data['animal_price'] = data_received.get('animal_price')
                query = "UPDATE animals SET animal_price =? WHERE animal_number=?"
                values = (put_data["animal_price"], str(animal_number))
                db.to_commit(query, values)

                response["animal_price"] = "Animal price updated successfully"
                response["status_code"] = 200
            # edit animal's description
            if data_received.get("animal_description") is not None:
                put_data['animal_description'] = data_received.get('animal_description')
                query = "UPDATE animals SET animal_description =? WHERE animal_number=?"
                values = (put_data["animal_description"], str(animal_number))
                db.to_commit(query, values)

                response["animal_description"] = "Animal description updated successfully"
                response["status_code"] = 200
            # edit animal's image link
            if data_received.get("animal_image") is not None:
                put_data['animal_image'] = data_received.get('animal_image')
                query = "UPDATE animals SET animal_image =? WHERE animal_number=?"
                values = (put_data["animal_image"], str(animal_number))
                db.to_commit(query, values)

                response["animal_image"] = "Animal image updated successfully"
                response["status_code"] = 200
                return response


# route to view single existing adoption animal using animal's ID
@app.route('/view-animal/<int:animal_number>/', methods=["GET"])
def view_animal(animal_number):
    response = {}
    db = Database()
    query = ("SELECT * FROM animals WHERE animal_number=" + str(animal_number))
    db.single_commit(query)
    response["status_code"] = 200
    response["message_description"] = "Animal retrieved successfully"
    response["data"] = db.fetch_one()
    return response


# function for checkout when adopting
@app.route('/adopt-checkout/', methods=["POST"])
def adopt_checkout():
    response = {}
    try:
        email = request.json['email_address']
        contact = request.json['contact_number']
        username = request.json['username']
        total_price = request.json['total_price']
        if email != "":
            msg = Message('Adoption Confirmation', sender='mikayladummy2@gmail.com', recipients=[email])
            # message for the email
            msg.body = "Hello " + str(username) + "!" \
                       "\n\nThank you for requesting to adopt our furry friends!"\
                       "\n\nPlease note that the total price for your adoption is R " + str(total_price) + ""\
                       "\n\nOur team will contact you on " + str(contact) + " within the next " \
                       "24 hours regarding the way forward, payment method as well as to arrange a time and date to " \
                       "link up for inspection. \n\nIf this contact number is incorrect, please respond to this email."
            mail.send(msg)

            response["message"] = "Email sent successfully."
            response["status_code"] = 201
            return response
        else:
            response["message"] = "No valid email address given"
            response["status_code"] = 401
            return response
    except SMTPRecipientsRefused:
        response['message'] = "Please enter a valid email address."
        response['status_code'] = 403
        return response
    except ValueError:
        response['message'] = "Please enter a valid phone number containing digits only."
        response['status_code'] = 400
        return response
    except TypeError:
        response['message'] = "Please enter a valid phone number containing digits only."
        response['status_code'] = 402
        return response


# creating an admin object
class Admin(object):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password


# creating an admin table
def init_admin_table():
    conn = sqlite3.connect('adoption_centre.db')
    cursor = conn.cursor()
    print("Opened database successfully")
    cursor.execute("CREATE TABLE IF NOT EXISTS admin "
                   "(admin_number INTEGER PRIMARY KEY AUTOINCREMENT,"
                   "admin_id TEXT NOT NULL,"
                   "admin_name TEXT NOT NULL,"
                   "admin_surname TEXT NOT NULL, "
                   "admin_email TEXT NOT NULL, "
                   "admin_contact TEXT NOT NULL, "
                   "admin_username TEXT unique, "
                   "admin_password TEXT NOT NULL)")
    print("Admin table created successfully")
    conn.close()


# calling function to create admin table
init_admin_table()


# fetching admin users from the admin table
def fetch_admin():
    db = Database()
    query = "SELECT * FROM admin"
    db.single_commit(query)
    registered_admin = db.fetch_all()

    new_data = []

    for data in registered_admin:
        new_data.append(User(data[0], data[6], data[7]))
    return new_data


# calling function to fetch all admin users
all_admin = fetch_admin()


admin_username_table = {u.username: u for u in all_admin}
adminId_table = {u.id: u for u in all_admin}


# route to register admin
@app.route('/register-admin/', methods=["POST"])
def admin_registration():
    response = {}
    db = Database()
    try:
        admin_id = request.json['admin_id']
        first_name = request.json['admin_name']
        last_name = request.json['admin_surname']
        email = request.json['admin_email']
        contact = request.json['admin_contact']
        username = request.json['admin_username']
        password = request.json['admin_password']

        if int(len(contact)) > 10 or int(len(contact)) < 10:
            response['message'] = "Please enter a valid phone number that consists of 10 digits."
            response['status_code'] = 400
            return response
        if int(contact) == str:
            response['message'] = "Please enter a phone number consisting of digits only."
            response['status_code'] = 401
            return response
        else:
            query = "INSERT INTO admin(admin_id, admin_name, admin_surname, admin_email, admin_contact, " \
                    "admin_username, admin_password) VALUES(?, ?, ?, ?, ?, ?, ?)"
            values = (admin_id, first_name, last_name, email, contact, username, password)
            db.to_commit(query, values)

            msg = Message('Welcome Email', sender='mikayladummy2@gmail.com', recipients=[email])
            # message for the email
            msg.body = "Hello " + str(username) + "!"\
                       "\n\nThank you for registering as an Admin User! \n\nHave a lovely day further!"
            mail.send(msg)

            response["message"] = "Successful Registration"
            response["status_code"] = 201
            return response
    except SMTPRecipientsRefused:
        response['message'] = "Please enter a valid email address."
        response['status_code'] = 400
        return response
    except ValueError:
        response['message'] = "Please enter a valid phone number containing digits only."
        response['status_code'] = 401
        return response
    except TypeError:
        response['message'] = "Please enter a valid phone number containing digits only."
        response['status_code'] = 402
        return response
    except sqlite3.IntegrityError:
        response['message'] = "Username already exists"
        response['status_code'] = 404
        return response


# route to log in as admin
@app.route('/login-admin/', methods=["POST"])
def admin_login():
    response = {}
    if request.method == "POST":
        username = request.json['admin_username']
        password = request.json['admin_password']
        conn = sqlite3.connect("adoption_centre.db")
        cur = conn.cursor()
        query = f"SELECT * FROM admin WHERE admin_username= '{username}' and admin_password = '{password}'"
        cur.execute(query)
        if not cur.fetchone():
            response['message'] = "Please enter valid credentials."
            response['status_code'] = 401
            return response
        else:
            response['message'] = "Welcome Admin!"
            response['status_code'] = 200
            return response
    else:
        return "Wrong Method"


# route to view single admin user using admin ID
@app.route('/view-admin/<int:admin_number>/', methods=["GET"])
def view_admin(admin_number):
    response = {}
    db = Database()
    query = ("SELECT * FROM admin WHERE admin_number=" + str(admin_number))
    db.single_commit(query)
    response["status_code"] = 200
    response["message_description"] = "Admin user retrieved successfully"
    response["data"] = db.fetch_one()
    return response


# route to show all admin users
@app.route('/show-admin/', methods=["GET"])
def show_admin():
    response = {}
    db = Database()
    query = "SELECT * FROM admin"
    db.single_commit(query)
    users = db.fetch_all()

    response['status_code'] = 200
    response['data'] = users
    return response


# calling function to show all admin users
all_admin = show_admin()


# route to edit admin user
@app.route('/edit-admin/<int:admin_number>/', methods=["PUT"])
# @jwt_required()
def edit_admin(admin_number):
    response = {}
    db = Database()

    if request.method == "PUT":
        with sqlite3.connect('adoption_centre.db'):
            data_receive = dict(request.json)
            put_data = {}
            # edit admin ID
            if data_receive.get("admin_id") is not None:
                put_data["admin_id"] = data_receive.get("admin_id")
                query = "UPDATE admin SET admin_id =? WHERE admin_number=?"
                values = (put_data["admin_id"], str(admin_number))
                db.to_commit(query, values)

                response['admin_id'] = "ID number update was successful."
                response['status_code'] = 200
            # edit admin name
            if data_receive.get("admin_name") is not None:
                put_data["admin_name"] = data_receive.get("admin_name")
                query = "UPDATE admin SET admin_name =? WHERE admin_number=?"
                values = (put_data["admin_name"], str(admin_number))
                db.to_commit(query, values)

                response['admin_name'] = "First name update was successful."
                response['status_code'] = 200
            # edit admin surname
            if data_receive.get("admin_surname") is not None:
                put_data['admin_surname'] = data_receive.get('admin_surname')
                query = "UPDATE admin SET admin_surname =? WHERE admin_number=?"
                values = (put_data["admin_surname"], str(admin_number))
                db.to_commit(query, values)

                response["admin_surname"] = "Last name updated successfully"
                response["status_code"] = 200
            # edit admin email address
            if data_receive.get("admin_email") is not None:
                put_data['admin_email'] = data_receive.get('admin_email')
                query = "UPDATE admin SET admin_email =? WHERE admin_number=?"
                values = (put_data["admin_email"], str(admin_number))
                db.to_commit(query, values)

                response["admin_email"] = "Email address updated successfully"
                response["status_code"] = 200
            # edit admin contact number
            if data_receive.get("admin_contact") is not None:
                put_data['admin_contact'] = data_receive.get('admin_contact')
                query = "UPDATE admin SET admin_contact =? WHERE admin_number=?"
                values = (put_data["admin_contact"], str(admin_number))
                db.to_commit(query, values)

                response["admin_contact"] = "Contact Number updated successfully"
                response["status_code"] = 200
            # edit admin username
            if data_receive.get("username") is not None:
                put_data['admin_username'] = data_receive.get('admin_username')
                query = "UPDATE admin SET admin_username =? WHERE admin_number=?"
                values = (put_data["admin_username"], str(admin_number))
                db.to_commit(query, values)

                response["admin_username"] = "Username updated successfully"
                response["status_code"] = 200
            # edit admin password
            if data_receive.get("admin_password") is not None:
                put_data['admin_password'] = data_receive.get('admin_password')
                query = "UPDATE admin SET admin_password =? WHERE admin_number=?"
                values = (put_data["admin_password"], str(admin_number))
                db.to_commit(query, values)

                response["admin_password"] = "Password updated successfully"
                response["status_code"] = 200
            return response


# route to delete admin user
@app.route("/delete-admin/<int:admin_number>")
def delete_admin(admin_number):
    response = {}
    db = Database()
    query = "DELETE FROM admin WHERE admin_number= ' " + str(admin_number) + " ' "
    db.single_commit(query)
    response['status_code'] = 200
    response['message'] = "Admin user deleted successfully."
    return response


# creating a foster object
class Foster(object):
    def __init__(self, foster_number, foster_name, foster_type, foster_breed, foster_age, foster_gender,
                 foster_description, foster_image):
        self.foster_number = foster_number
        self.foster_name = foster_name
        self.foster_type = foster_type
        self.foster_breed = foster_breed
        self.foster_age = foster_age
        self.foster_gender = foster_gender
        self.foster_description = foster_description
        self.foster_image = foster_image
        
        
# creating a foster table
def init_foster_table():
    db = Database()
    query = ("CREATE TABLE IF NOT EXISTS foster "
             "(foster_number INTEGER PRIMARY KEY AUTOINCREMENT, "
             "foster_name TEXT NOT NULL, "
             "foster_type TEXT NOT NULL, "
             "foster_breed TEXT NOT NULL, "
             "foster_age TEXT NOT NULL, "
             "foster_gender TEXT NOT NULL, "
             "foster_description TEXT NOT NULL, "
             "foster_image TEXT NOT NULL)")
    db.single_commit(query)
    print("Foster table created successfully.")


# calling function to create products table
init_foster_table()


# route to add a foster animals
@app.route('/add-foster/', methods=["POST"])
# @jwt_required()
def add_foster():
    response = {}
    db = Database()
    if request.method == "POST":
        name = request.json['foster_name']
        type = request.json['foster_type']
        breed = request.json['foster_breed']
        age = request.json['foster_age']
        gender = request.json['foster_gender']
        description = request.json['foster_description']
        image = request.json['foster_image']
        if name == '' or type == '' or breed == '' or age == '' or gender == ''or description == '' or image == '':
            return "Please fill in all entry fields"
        else:
            query = "INSERT INTO foster (foster_name, foster_type, foster_breed, foster_age, foster_gender, " \
                    " foster_description, foster_image) VALUES(?, ?, ?, ?, ?, ?, ?)"
            values = (name, type, breed, age, gender, description, image)
            db.to_commit(query, values)

            response["status_code"] = 201
            response['description_message'] = "Foster animal added successfully"
            return response


# route to delete one foster animal
@app.route("/delete-foster/<int:foster_number>")
# @jwt_required()
def delete_foster(foster_number):
    response = {}
    db = Database()
    query = "DELETE FROM foster WHERE foster_number=" + str(foster_number)
    db.single_commit(query)
    response['status_code'] = 200
    response['message'] = "Foster animal deleted successfully."
    return response


# route to edit single foster animal
@app.route('/edit-foster/<int:foster_number>/', methods=["PUT"])
# @jwt_required()
def edit_foster(foster_number):
    response = {}
    db = Database()

    if request.method == "PUT":
        with sqlite3.connect('adoption_centre.db'):
            data_received = dict(request.json)
            put_data = {}
            # edit foster name
            if data_received.get("foster_name") is not None:
                put_data["foster_name"] = data_received.get("foster_name")
                query = "UPDATE foster SET foster_name =? WHERE foster_number=?"
                values = (put_data["foster_name"], foster_number)
                db.to_commit(query, values)

                response['foster_name'] = "Foster name update was successful."
                response['status_code'] = 200
            # edit foster type
            if data_received.get("foster_type") is not None:
                put_data['foster_type'] = data_received.get('foster_type')
                query = "UPDATE foster SET foster_type =? WHERE foster_number=?"
                values = (put_data["foster_type"], str(foster_number))
                db.to_commit(query, values)

                response["foster_type"] = "Foster type updated successfully"
                response["status_code"] = 200
            # edit foster breed
            if data_received.get("foster_breed") is not None:
                put_data['foster_breed'] = data_received.get('foster_breed')
                query = "UPDATE foster SET foster_breed =? WHERE foster_number=?"
                values = (put_data["foster_breed"], str(foster_number))
                db.to_commit(query, values)

                response["foster_breed"] = "Foster breed updated successfully"
                response["status_code"] = 200
            # edit foster age
            if data_received.get("foster_age") is not None:
                put_data["foster_age"] = data_received.get("foster_age")
                query = "UPDATE foster SET foster_age =? WHERE foster_number=?"
                values = (put_data["foster_age"],foster_number)
                db.to_commit(query, values)

                response['foster_age'] = "Foster age update was successful."
                response['status_code'] = 200
            # edit foster gender
            if data_received.get("foster_gender") is not None:
                put_data['foster_gender'] = data_received.get('foster_gender')
                query = "UPDATE foster SET foster_gender =? WHERE foster_number=?"
                values = (put_data["foster_gender"], str(foster_number))
                db.to_commit(query, values)

                response["foster_gender"] = "Foster gender updated successfully"
                response["status_code"] = 200
            # edit foster description
            if data_received.get("foster_description") is not None:
                put_data['foster_description'] = data_received.get('foster_description')
                query = "UPDATE foster SET foster_description =? WHERE foster_number=?"
                values = (put_data["foster_description"], str(foster_number))
                db.to_commit(query, values)

                response["foster_description"] = "Foster description updated successfully"
                response["status_code"] = 200
            # edit foster image link
            if data_received.get("foster_image") is not None:
                put_data['foster_image'] = data_received.get('foster_image')
                query = "UPDATE foster SET foster_image =? WHERE foster_number=?"
                values = (put_data["foster_image"], str(foster_number))
                db.to_commit(query, values)

                response["foster_image"] = "Foster image updated successfully"
                response["status_code"] = 200
                return response


# route to view single foster animal using animal ID
@app.route('/view-foster/<int:foster_number>/', methods=["GET"])
def view_foster(foster_number):
    response = {}
    db = Database()
    query = ("SELECT * FROM foster WHERE foster_number=" + str(foster_number))
    db.single_commit(query)
    response["status_code"] = 200
    response["message_description"] = "Foster animal retrieved successfully"
    response["data"] = db.fetch_one()
    return response


# route to show all foster animals
@app.route('/show-foster/', methods=["GET"])
def show_foster():
    response = {}
    db = Database()
    query = "SELECT * FROM foster"
    db.single_commit(query)
    fosters = db.fetch_all()

    response['status_code'] = 200
    response['data'] = fosters
    return response


# calling function to show all foster animals
all_foster = show_foster()


# function for checking out when fostering
@app.route('/foster-checkout/', methods=["POST"])
def foster_checkout():
    response = {}
    try:
        email = request.json['email_address']
        contact = request.json['contact_number']
        username = request.json['username']
        animal_name = request.json['animal_name']
        animal_breed = request.json['animal_breed']
        animal_type = request.json['animal_type']
        animal_age = request.json['animal_age']
        if email != "":
            msg = Message('Foster Confirmation', sender='mikayladummy2@gmail.com', recipients=[email])
            # message for the email
            msg.body = "Hello " + str(username) + "!" \
                       "\n\nThank you for requesting to foster " + str(animal_name) + "!"\
                       "\n\n" + str(animal_name) + "'s details are as follows: " \
                       "\n Animal type: " + str(animal_type) + "\nAnimal breed: " + str(animal_breed) + "" \
                       "\nAge: " + str(animal_age) + " Old\n\nOur team will contact you on " + str(contact) + "" \
                       " within the next 24 hours regarding the way forward as well as to arrange a time and date to " \
                       "link up for inspection and further details. \n\nIf this contact number is incorrect, please" \
                       " respond to this email."
            mail.send(msg)

            response["message"] = "Email sent successfully."
            response["status_code"] = 201
            return response
        else:
            response["message"] = "No valid email address given"
            response["status_code"] = 401
            return response
    except SMTPRecipientsRefused:
        response['message'] = "Please enter a valid email address."
        response['status_code'] = 403
        return response
    except ValueError:
        response['message'] = "Please enter a valid phone number containing digits only."
        response['status_code'] = 400
        return response
    except TypeError:
        response['message'] = "Please enter a valid phone number containing digits only."
        response['status_code'] = 402
        return response


if __name__ == "__main__":
    app.debug = True
    app.run()
