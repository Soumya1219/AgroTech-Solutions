from flask import Flask, flash, request, jsonify
from models import *
from private import DATABASE_URL, email, password, recipients  #create a private.py file and insert these values in it
from flask_cors import CORS
from sqlalchemy import func
from helpers import *
from flask_mail import Mail

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] =DATABASE_URL  #replace this DATABASE_URL with your database url or create a private file
db.init_app(app)


app.config['MAIL_SERVER'] = 'smtp.gmail.com'  
app.config['MAIL_PORT'] = 587  
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] =email   # replace this with your email if values not given in private file
app.config['MAIL_PASSWORD'] = password # eeplace this with your password if values not given in private file
app.config['MAIL_DEFAULT_SENDER'] = email
mail = Mail(app)

app.secret_key="sSngV$hYRbPcIg@lmnG#yui"


'''
this route is used to get all the crop types with or without location(location name). if location is given it will give the crop types with in 5 km radius
'''
@app.route("/crop_types", methods=["GET"])
def crop_types():
    #{request1-params:None}
    #{request2-params:location}
    if(request.method=="GET"):
        try:
            location=request.args.get('location')
            if(not location):
                crop_types=get_all_crop_types()
                response={"success":True, "message":"all crop types retrieved", "data":crop_types}
            else:
                crop_types=get_crop_types_by_location(location)
                response={"success":True, "message":"all crop types retrieved", "data":crop_types}

        except Exception as e:
            response={"error":str(e), "success":False, "message":"Exception occured"}
    else:
        response={"success":False, "message":"request is not GET"}
    return jsonify(response)

'''
this route is used to get all the crops of particular crop type with or wihtout location(location name).if location is given it will give the crops of that particular 
crop_type with in 5 km radius
'''
@app.route("/crops", methods=["GET"])
def crops():
    #{request1-params:crop_type, location}
    #{request2-params:crop_type}
    if(request.method=="GET"):
        try:
            location=request.args.get("location")
            crop_type=request.args.get("crop_type")
            if not location and not crop_type:
                response={"success":False, "message":"no location or crop type provided"}
            elif not location:
                crops=get_all_crops_by_crop_type(crop_type)
                response={"success":True, "message":"all crops of a crop_type are retrieved", "data":crops}
            else:
                crops=get_crops_by_crop_type_and_location(crop_type, location)
                response={"success":True, "message":"all crops of a crop_type are retrieved", "data":crops}
        except Exception as e:
            response={"error":str(e), "success":False, "message":"Exception occured"}
    else:
        response={"success":False, "message":"request is not GET"}
    return jsonify(response)

'''
this route is used to get all the farmers who yeild that crop using crop_name and with or without location(location name).if location is given it will give all the farmers 
yeilding that crop within 5 km radius of the given location
'''
@app.route("/farmers", methods=["GET"])
def farmers():
    #{request1-params : crop_name, location}
    #{request2-params : crop_name}

    if(request.method=="GET"):
        try:
            location=request.args.get("location")
            crop_name=request.args.get("crop_name")
            if not location and not crop_name:
                response={"success":False, "message":"no location and no crop name provided"}
            if not location:
                farmers=get_all_farmers_by_crop_name(crop_name)
                response={"success":True, "message":"all farmers of a crop_name are retrieved", "data":farmers}
            else:
                farmers=get_farmers_by_crop_name_and_location(crop_name, location)
                response={"success":True, "message":"all farmers of a crop_name are retrieved", "data":farmers}
        except Exception as e:
            response={"error":str(e), "success":False, "message":"Exception occured"}
    else:
        response={"success":False, "message":"request is not GET"}
    return jsonify(response)

'''
this route is used to  add a new user while signin
'''
@app.route("/newuser", methods=["POST"])
def add_new_user():
     #{request : email, google_id, user_type}
    if(request.method=="POST"):
        try:
            data=request.get_json()
            existing_user = UserAuth.query.filter_by(mail=data["email"]).first()
            if existing_user:
                response={"success":False, "message":"User already exists"}
            else:
                new_user=create_new_user_object(data)
                db.session.add(new_user)
                db.session.commit()
                response={"success":True, "message":"new User created"}
        except Exception as e:
            response={"error":str(e), "success":False, "message":"Exception occured"}
    else:
        response={"success":False, "message":"request not posted"}
    return jsonify(response)

'''
this route is used to  add farmer data which include crops he yeild,  name,  number, mail etc..,  
'''
@app.route("/farmer_data", methods=["POST"])
def fdata_ins():
    #{request1 : name, email, number, latitude, longitude, crop_type, crop_name}
    #{request2 : crop_type, crop_name, email}   
    if request.method=="POST":
        try:
            request_data=request.get_json()
            existing_user = User.query.filter_by(email=request_data["email"]).first()
            if existing_user:
                #request2
                id=existing_user.user_id
                exisisting_crop=Crop.query.filter_by(crop_name=request_data["crop_name"].title(), user_id=id).first()
                exisisting_crop_type=Crop.query.filter_by(crop_type=request_data["crop_type"].title(), user_id=id).first()
                if exisisting_crop and exisisting_crop_type:
                    response={"success":False, "message":"Crop with this name already registered by this farmer under this crop type"}
                else:
                    new_crop=create_crop_object(id, request_data)
                    db.session.add(new_crop)
                    db.session.commit()
                    response={'success':True, 'message': 'Crop data added successfully for existing farmer'}
            else:
                #request1
                new_user = create_user_object(request_data)
                db.session.add(new_user)
                db.session.commit()

                new_location = create_user_location_object(new_user.user_id, request_data)
                db.session.add(new_location)
                db.session.commit()

                new_crop = create_crop_object(new_user.user_id, request_data)
                db.session.add(new_crop)
                db.session.commit()

                response={'success':True, 'message': 'User and crop data added successfully'}
        except Exception as e:
            response={"error":str(e), "success":False, "message":"Exception occured"}
    else:
        response={"success":False, "message":"No  post given"}
    return jsonify(response)

'''
this route is used to get all the crop data which include cropstypes and cropnames that fall into that crop type.
'''
@app.route("/crop_data", methods=["GET"])
def get_crop_data():
    #{request-params : None}
    if(request.method=="GET"):
        try:
            crops_types_and_names=get_all_crop_names_in_along_crop_types()
            if crops_types_and_names:
                response={"success":True, "message":"all crop_types and names are retrieved", "data":crops_types_and_names}
            else:
                response={"success":True, "message":"no crop data present", "data":crops_types_and_names}
        except Exception as e:
            response={"error":str(e), "success":False, "message":"Exception occured"}

    else:
        response={"success":False, "message":"No get  given"}

    return jsonify(response)

'''
this route is used to get the all the farmer details using their user_id.
'''
@app.route("/farmer_details", methods=["GET"])
def farmer_details():
    #{request-params : user_id}
    if(request.method=="GET"):
        try:
            farmer_details=get_farmer_details(request.args.get('user_id'))
            if  farmer_details:
                response={"success":True, "message":"farmer details successfully retrieved", "data":farmer_details}
            else:
                response={"success":True, "message":"no data present with the info given"}
        except Exception as e:
            response={"error":str(e), "success":False, "message":"Exception occured"}

    else:
        response={"success":False, "message":"Request is not get"}

    return jsonify(response)

'''
this route is used to recommend a crop based on the details provided which include nitrogen, phosphorous, temperature etc.., 
'''
@app.route("/crop_recommendation", methods=["POST"])
def crop_recommendation():
    #{request-json : {"nitrogen",  "phosphorous",  "potassium",  "temperature",  "humidity",  "rainfall",  "pH"}}
    if request.method=="POST":
        try:
            request_data=request.get_json()
            crop_recommended=recommend_crop(request_data)
            if crop_recommended:
                response={"success":True, "crop":crop_recommended, "message":"Crop Recommended"}
            else:
                response={"success":False, "crop":crop_recommended, "message":"Data is invalid"}
        except Exception as e:
            response={"error":str(e), "success":False, "message":"Exception occured"}
    else:
        response={"success":False, "message":"no post "}

    return jsonify(response)

'''
this route is used to recommend a fertilizer based on the details provided which include nitrogen, phosphorous, temperature etc.., 
'''
@app.route("/fertilizer_recommendation", methods=["POST"])
def fertilizer_recommendation():
    #{request-json : {"nitrogen", "phosphorous",  "potassium",  "temperature",  "moisture",  "soil_type",  "crop_type",  "humidity"}}
    if request.method=="POST":
        try:
            request_data=request.get_json()
            fertilizer_recommended=recommend_fertilizer(request_data)
            if fertilizer_recommended!="":
                response={"success":True, "message":"fertilizer recommended", "fertilizer":fertilizer_recommended}
            else:
                response={"success":False, "message":"Data is Invalid"}
        except Exception as e:
            response={"success":False, "error":str(e), "message":"Exception occured"}
    else:
        response={"success":False, "message":"no post "}
    return jsonify(response)

'''
this route is used to predict a crop disease based on the image and the crop name provided.
'''
@app.route('/disease_predict',  methods=['POST', "GET"])
def crop_disease():
    #{request-form : crop_name, file}--form data
    response=dict()
    if(request.method=="POST"):
        try:
            file = request.files['file']
            cropName=request.form.get("crop_name")
            response["data"]=cropName   
            predictions = predict_disease(cropName, file)
            response={'success':True, "message":"Disease Predicted Successfully", 'predictions': predictions}
        except Exception as e:
            response={"success":False, "error":str(e), "message":"Exception occured"}

    else:
        response={"success":False, "message":"no post "}
    return jsonify(response)

'''
this route is used to send mail to our team using the details provided.
'''
@app.route("/contactus", methods=["POST"])
def contactus():
    #{request-json : {"query_type", "mail", "number", "query"}}
    if(request.method=="POST"):
        try:
            request_data=request.get_json()
            message=create_message(request_data, recipients)
            query_type = request_data['query_type']
            mail.send(message)
            flash('Email sent successfully!')
            response={"success":True, "queryType":query_type, "message":"Mail Succesfully sent", "alert":"We recieved your "+request_data["query_type"]}
        except Exception as e:
            response={"success":False, "error":str(e), "message":"Exception occured"}

    else:
        response={"success":False, "message":"no post "}
    return jsonify(response)

'''
this route is used to get weather data
'''
@app.route("/weather_data")
def weather():
    #{request-params : latitude,  longitude}
    if(request.method=="GET"):
        try:
            weather_data=get_weather_data(request)
            response={"success":True, "data":weather_data, "message":"Weather Data Fetched Succesfully"}
        except Exception as e:
            response={"success":False, "error":str(e), "message":"Exception occured"}
    else:
        response={"success":False, "message":"no get given"}
    return jsonify(response)


        







