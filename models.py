from flask_sqlalchemy import SQLAlchemy


db=SQLAlchemy()

class UserAuth(db.Model):
    __tablename__ = 'user_auth'
    user_id = db.Column(db.Integer, primary_key=True)
    mail = db.Column(db.String(255), unique=True, nullable=False)
    google_id = db.Column(db.String(255), unique=True, nullable=False)
    user_type = db.Column(db.String(10), nullable=False, server_default='customer')

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone_number = db.Column(db.String(15))  # Assuming a string representation of the phone number
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

    def __init__(self, name, email, phone_number):
        self.name = name
        self.email = email
        self.phone_number = phone_number
    
class UserLocation(db.Model):
    __tablename__ = 'user_location'
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    city = db.Column(db.String(255))

    def __init__(self, user_id, latitude, longitude, city):
        self.user_id = user_id
        self.latitude = latitude
        self.longitude = longitude
        self.city = city
    
class Crop(db.Model):
    __tablename__ = 'crops'
    crop_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    crop_type = db.Column(db.String(255), nullable=False)
    crop_name = db.Column(db.String(255), nullable=False)
    yield_info = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

    def __init__(self, user_id, crop_type, crop_name, yield_info):
        self.user_id = user_id
        self.crop_type = crop_type
        self.crop_name = crop_name
        self.yield_info = yield_info





