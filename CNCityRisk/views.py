from flask import render_template, request, url_for, redirect, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user

from CNCityRisk import app
from CNCityRisk import models

# from CNCityRisk import db
# from CNCityRisk.models import User, Movie


@app.route('/', methods=['GET', 'POST'])
def index():

    provinces = list(models.Province_City_District.keys())
    if request.method == 'POST':
        current_province = request.form['province']
        cities = list(models.Province_City_District[current_province].keys())
        current_city = request.form['city']
        districts = list(models.Province_City_District[current_province][current_city])
        current_district = request.form['district']
    else:
        current_province = provinces[0]
        cities = list(models.Province_City_District[current_province].keys())
        current_city = cities[0]
        districts = list(models.Province_City_District[current_province][current_city])
        current_district = districts[0]
    
    return render_template('index.html', 
            provinces=provinces, current_province=current_province,
            cities=cities, current_city=current_city, 
            districts=districts, current_district=current_district)


@app.route('/get_city_list')
def get_city_list():
    province = request.args.get('province', '')
    
    cities = list(models.Province_City_District[province].keys())
    
    return jsonify({'cities': cities})


@app.route('/get_district_list')
def get_district_list():
    province = request.args.get('province', '')
    city = request.args.get('city', '')
    
    districts = list(models.Province_City_District[province][city])

    return jsonify({'districts': districts})

