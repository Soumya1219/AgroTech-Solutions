import requests
from models import *
from sqlalchemy import func
import joblib
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from PIL import Image
from flask_mail import Mail, Message
from flask import render_template_string
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import json


cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

crop_disease_data=dict()
crop_disease_data["tomato"]=["Apple Scab","Black Rot","Cedar Apple rust","healthy"]
crop_disease_data["grape"]=["Black Rot","Esca","Leaf Blight","Healthy"]
crop_disease_data["maize"]=["CercoSpora Leaf Spot","Common Rust","Northern Leaf Blight","Healthy"]
crop_disease_data["mango"]=["Die Back","Healthy","Powdery Mildew","Sooty Mould"]

soil_map={'Black': 0, 'Clayey': 1, 'Loamy': 2, 'Red': 3, 'Sandy': 4}
crop_map={'Barley': 0, 'Cotton': 1, 'Ground Nuts': 2, 'Maize': 3, 'Millets': 4, 'Oil seeds': 5, 'Paddy': 6, 'Pulses': 7, 'Sugarcane': 8, 'Tobacco': 9, 'Wheat': 10}

def loc_to_latlon(location):
    latlon=dict()
    api_url = f'https://nominatim.openstreetmap.org/search?format=json&q={location}'
    response = requests.get(api_url)
    data = response.json()
    if data:
        latitude=data[0]['lat']
        longitude=data[0]['lon']
        latlon["lat"]=latitude
        latlon["lon"]=longitude
    return latlon

def latlon_to_loc(latitude,longitude):
    location_info = dict()
    api_url = f'https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}'
    response = requests.get(api_url)
    data = response.json()
    city= data.get('display_name').split(",")[0]
    if data and 'address' in data:
        location_info['city'] = data['address'].get('city', '')
        location_info['state'] = data['address'].get('state', '')
        location_info['country'] = data['address'].get('country', '')
    return city

def recommend_crop(request_data):
    Nitrogen=request_data["nitrogen"]
    Phosphorous=request_data["phosphorous"]
    Potassium=request_data["potassium"]
    Temperature=request_data["temperature"]
    Rainfall=request_data["rainfall"]
    pH=request_data["pH"]
    Humidity=request_data["humidity"]

    recommended_crop=""
    env_data=[Nitrogen,Phosphorous,Potassium,Temperature,Humidity,pH,Rainfall]
    model = joblib.load("./models/machine_learning/crop_recommendation/crop_recommendation.joblib")
    env_data_arr=np.array([env_data])
    recommended_crop=model.predict(env_data_arr)[0]

    return recommended_crop

def recommend_fertilizer(request_data):
    
    Nitrogen=request_data["nitrogen"]
    Phosphorous=request_data["phosphorous"]
    Potassium=request_data["potassium"]
    Temperature=request_data["temperature"]
    Moisture=request_data["moisture"]
    SoilType=request_data["soil_type"]
    CropType=request_data["crop_type"]
    Humidity=request_data["humidity"]
    recommended_fertilizer=""

    SoilName=SoilType.strip().title()
    CropName=CropType.strip().title()
    CropType=crop_map.get(CropName,False)
    SoilType=soil_map.get(SoilName,False)

    if(CropType and SoilType):
        env_data=[Temperature,Humidity,Moisture,SoilType,CropType,Nitrogen,Phosphorous,Potassium]
        model=joblib.load("./models/machine_learning/fertilizer_recommendation/fertilizer_recommendation.joblib")
        env_data_arr=np.array([env_data])
        recommended_fertilizer=model.predict(env_data_arr)[0]
        
    return recommended_fertilizer

def predict_disease(CropName,file):
    crop_name=CropName.strip().lower()
    deep_learning_models_path="./models/deep_learning/crop_disease_prediction/"
    crop_disease_model_rel_path=crop_name+"/"+crop_name+"_crop_disease_prediction_model.h5"
    model_path=deep_learning_models_path+crop_disease_model_rel_path
    model=load_model(model_path)
    disease_labels=crop_disease_data[crop_name]
    image_data = np.array(Image.open(file))
    class_label_number=predict_label(image_data,model)
    class_label=disease_labels[class_label_number]
    return class_label

def preprocess_image(image_data):
    img_array = tf.image.resize(image_data, (224, 224))
    img_array = img_array / 255.0  
    img_array = tf.expand_dims(img_array, axis=0)
    return img_array

def predict_label(image_data, model):
    img_array = preprocess_image(image_data)
    prediction = model.predict(img_array)
    predicted_class = np.argmax(prediction)
    confidence_score = np.max(prediction)
    return predicted_class

def create_crop_object(id,request_data):
    crop_type = request_data['crop_type'].title()
    crop_name = request_data['crop_name'].title()
    yeild_info=""
    user_id=id
    crop_obj = Crop(
        user_id=user_id,
        crop_type=crop_type,
        crop_name=crop_name,
        yield_info=yeild_info
    )
    return crop_obj

def create_user_object(request_data):
    name = request_data['name'].title()
    email = request_data['email']
    number= request_data['number']
    user_obj = User(
        name=name,
        email=email,
        phone_number=number
    )
    return user_obj
    
def create_user_location_object(id,request_data):
    latitude = request_data['latitude']
    longitude = request_data['longitude']
    city=latlon_to_loc(latitude,longitude)
    user_location_obj=UserLocation(
        user_id=id,
        latitude=latitude,
        longitude=longitude,
        city=city
    )
    return user_location_obj

def create_new_user_object(request_data):
    mail=request_data["email"]
    google_id=request_data["google_id"]
    user_type=request_data["user_type"]
    new_user_obj=UserAuth(
        mail=mail,
        google_id=google_id,
        user_type=user_type

    )
    return new_user_obj


def get_farmer_details(id):
    user_details = db.session.query(User.name, User.email, User.phone_number,
                                    UserLocation.city, Crop.crop_type, Crop.crop_name)\
        .join(UserLocation, UserLocation.user_id == User.user_id)\
        .join(Crop, Crop.user_id == User.user_id)\
        .filter(User.user_id == id)\
        .all()
    
    if user_details:
        crops_list = []
        for user_detail in user_details:
            crop_dict = {
                'name':user_detail[0],
                'crop_type': user_detail[4],
                'crop_name': user_detail[5]
            }
            crops_list.append(crop_dict)

        result_dict = {
            'name': user_details[0][0],
            'email': user_details[0][1],
            'number': user_details[0][2],
            'city': user_details[0][3],
            'crops': crops_list
        }

        return result_dict
    return{}

def lat_lon_boundaries(lat_lon_data,radius=5):
    boundary_value=0.009*radius
    latitude=lat_lon_data["lat"]
    longitude=lat_lon_data["lon"]
    left_boundary_latitude=float(latitude)-boundary_value
    right_boundary_latitude =float(latitude)+boundary_value
    left_boundary_longitude=float(longitude)-boundary_value
    right_boundary_longitude=float(longitude)+boundary_value
    return [left_boundary_latitude,right_boundary_latitude,left_boundary_longitude,right_boundary_longitude]

def get_all_crop_types():
    all_crop_types = db.session.query(Crop.crop_type).distinct().all()
    crop_types_list = [crop_type[0] for crop_type in all_crop_types]
    return crop_types_list

def get_crop_types_by_location(location):
    lat_lon_data=loc_to_latlon(location)
    lat_left,lat_right,lon_left,lon_right=lat_lon_boundaries(lat_lon_data,5)
    crop_types_by_location = db.session.query(Crop.crop_type)\
        .join(UserLocation, UserLocation.user_id == Crop.user_id)\
        .filter(UserLocation.latitude >lat_left,UserLocation.latitude < lat_right, UserLocation.longitude >lon_left, UserLocation.longitude <lon_right)\
        .distinct().all()

    crop_types_list = [crop_type[0] for crop_type in crop_types_by_location]
    return crop_types_list

def get_all_crops_by_crop_type(crop_type):
    crop_type=crop_type.title()
    crops_by_crop_type = db.session.query(Crop.crop_name)\
        .filter(Crop.crop_type == crop_type).distinct().all()

    # Extracting crop names from the result
    crop_names_list = [crop[0] for crop in crops_by_crop_type]
    return crop_names_list

def get_crops_by_crop_type_and_location(crop_type,location):
    crop_type=crop_type.title()
    lat_lon_data=loc_to_latlon(location)
    lat_left,lat_right,lon_left,lon_right=lat_lon_boundaries(lat_lon_data,5)
    crop_names_by_type_and_location = db.session.query(Crop.crop_name)\
        .join(UserLocation, UserLocation.user_id == Crop.user_id)\
        .filter(Crop.crop_type == crop_type,
                UserLocation.latitude >lat_left,UserLocation.latitude < lat_right, UserLocation.longitude >lon_left, UserLocation.longitude <lon_right).all()

    # Extracting crop names from the result
    crop_names_list = [crop[0] for crop in crop_names_by_type_and_location]
    return crop_names_list

def get_all_farmers_by_crop_name(crop_name):
    crop_name=crop_name.title()
    farmers_by_crop_name = db.session.query(User.name, UserLocation.city, User.user_id)\
        .join(Crop, Crop.user_id == User.user_id)\
        .join(UserLocation, UserLocation.user_id == User.user_id)\
        .filter(Crop.crop_name == crop_name).all()

    farmers_list = [{'name': farmer[0], 'city': farmer[1], 'user_id': farmer[2]} for farmer in farmers_by_crop_name]
    return farmers_list

def get_farmers_by_crop_name_and_location(crop_name,location):
    crop_name=crop_name.title()
    lat_lon_data=loc_to_latlon(location)
    lat_left,lat_right,lon_left,lon_right=lat_lon_boundaries(lat_lon_data,5)
    farmers_by_crop_name_and_location = db.session.query(User.name, UserLocation.city, User.user_id)\
        .join(Crop, Crop.user_id == User.user_id)\
        .join(UserLocation, UserLocation.user_id == User.user_id)\
        .filter(Crop.crop_name == crop_name,
                UserLocation.latitude >lat_left,UserLocation.latitude < lat_right, UserLocation.longitude >lon_left, UserLocation.longitude <lon_right).all()

    farmers_list = [{'name': farmer[0], 'city': farmer[1], 'user_id': farmer[2]} for farmer in farmers_by_crop_name_and_location]
    return farmers_list

def get_all_crop_names_in_along_crop_types():
    crop_types_and_names = db.session.query(Crop.crop_type, Crop.crop_name).distinct().all()

    crop_data_dict = {}
    for crop_type, crop_name in crop_types_and_names:
        if crop_type not in crop_data_dict:
            crop_data_dict[crop_type] = [crop_name]
        else:
            if(crop_name not in crop_data_dict[crop_type]):
                crop_data_dict[crop_type].append(crop_name)
    return crop_data_dict

def create_message(request_data,recipients):
    subject = request_data['query_type']
    body = request_data['query']
    customer_mail=request_data['mail']
    customer_number=request_data["number"]
    
    message = Message(subject, recipients=recipients)

    html_body = render_template_string(
        """
        <p>{{ body }}</p>
        <p>Contact the customer at: <a href="mailto:{{ customer_mail }}">{{ customer_mail }}</a></p>
        <p>Customer Contact Number : <a href="">{{ customer_number }}</a></p>
        """,
        body=body,
        customer_mail=customer_mail,
        customer_number=customer_number

    )

    message.body = body
    message.html = html_body
    return message

def get_weather_response(latitude,longitude):
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ["temperature_2m", "apparent_temperature", "weather_code", "cloud_cover", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"],
        "minutely_15": ["temperature_2m", "dew_point_2m", "apparent_temperature", "weather_code", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"],
        "hourly": ["temperature_2m", "dew_point_2m", "apparent_temperature", "precipitation_probability", "weather_code", "cloud_cover", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"],
        "timezone": "auto",
        "forecast_minutely_15": 96
    }
    responses = openmeteo.weather_api(url, params=params)
    return responses[0]


def get_weather_data(request):
    latitude=request.args.get('latitude')
    longitude=request.args.get('longitude')
    response=get_weather_response(latitude,longitude)
    weather_data=dict()
    time_diff=response.UtcOffsetSeconds()

    current_dict=dict()
    current = response.Current()
    start_time=current.Time()+time_diff
    end_time=current.TimeEnd()+time_diff
    current_dict["date_time"]=pd.date_range(
        start = pd.to_datetime(start_time, unit = "s"),
        end = pd.to_datetime(end_time, unit = "s"),
        freq = pd.Timedelta(seconds = current.Interval()),
        inclusive = "left"
    ).tolist()
    current_dict["temperature"] = current.Variables(0).Value()
    current_dict["apparent_temperature"] = current.Variables(1).Value()
    current_dict["weather_code"] = current.Variables(2).Value()
    current_dict["cloud_cover"] = current.Variables(3).Value()
    current_dict["wind_speed"] = current.Variables(4).Value()
    current_dict["wind_direction"] = current.Variables(5).Value()
    current_dict["wind_gusts"] = current.Variables(6).Value()
    

    minutely_15_dict=dict()
    
    minutely_15 = response.Minutely15()
    start_time=minutely_15.Time()+time_diff
    end_time=minutely_15.TimeEnd()+time_diff
    minutely_15_dict["date_time"]=pd.date_range(
        start = pd.to_datetime(start_time, unit = "s"),
        end = pd.to_datetime(end_time, unit = "s"),
        freq = pd.Timedelta(seconds = minutely_15.Interval()),
        inclusive = "left"
    ).tolist()
    minutely_15_dict["temperature"] = minutely_15.Variables(0).ValuesAsNumpy().tolist()
    minutely_15_dict["dew_point"] = minutely_15.Variables(1).ValuesAsNumpy().tolist()
    minutely_15_dict["apparent_temperature"] = minutely_15.Variables(2).ValuesAsNumpy().tolist()
    minutely_15_dict["weather_code"] = minutely_15.Variables(3).ValuesAsNumpy().tolist()
    minutely_15_dict["wind_speed"] = minutely_15.Variables(4).ValuesAsNumpy().tolist()
    minutely_15_dict["wind_direction"] = minutely_15.Variables(5).ValuesAsNumpy().tolist()
    minutely_15_dict["wind_gusts"] = minutely_15.Variables(6).ValuesAsNumpy().tolist()


    hourly_dict=dict()
    hourly = response.Hourly()
    start_time=hourly.Time()+time_diff
    end_time=hourly.TimeEnd()+time_diff
    hourly_dict["date_time"] =  pd.date_range(
        start = pd.to_datetime(start_time, unit = "s"),
        end = pd.to_datetime(end_time, unit = "s"),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left"
    ).tolist()
    hourly_dict["temperature"] = hourly.Variables(0).ValuesAsNumpy().tolist()
    hourly_dict["dew_point"] = hourly.Variables(1).ValuesAsNumpy().tolist()
    hourly_dict["apparent_temperature"] = hourly.Variables(2).ValuesAsNumpy().tolist()
    hourly_dict["precipitation_probability"] = hourly.Variables(3).ValuesAsNumpy().tolist()
    hourly_dict["weather_code"] = hourly.Variables(4).ValuesAsNumpy().tolist()
    hourly_dict["cloud_cover"] = hourly.Variables(5).ValuesAsNumpy().tolist()
    hourly_dict["wind_speed"] = hourly.Variables(6).ValuesAsNumpy().tolist()
    hourly_dict["wind_direction"] = hourly.Variables(7).ValuesAsNumpy().tolist()
    hourly_dict["wind_gusts"] = hourly.Variables(8).ValuesAsNumpy().tolist()

    weather_data["current"]=current_dict
    weather_data["minutely_15"]=minutely_15_dict
    weather_data["hourly"]=hourly_dict

    return weather_data














    





