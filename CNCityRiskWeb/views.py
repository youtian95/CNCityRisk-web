from flask import render_template, request, url_for, redirect, flash, jsonify
from pathlib import Path

from CNCityRiskWeb import app
from CNCityRiskWeb import models

provinces = list(models.Province_City_District.keys())

@app.route('/', methods=['GET','POST'])
def index():
    if request.method == 'GET':
        current_province = request.args.get('province', '湖北省')
        cities = list(models.Province_City_District[current_province].keys())
        current_city = request.args.get('city', '武汉')
        districts = list(models.Province_City_District[current_province][current_city])
        current_district = request.args.get('district', '武昌区')

        html_content = models.get_map_rupture(current_city)
        return render_template('index.html', 
            html_content=html_content,
            eq_i_rup=0,
            provinces=provinces, current_province=current_province,
            cities=cities, current_city=current_city, 
            districts=districts, current_district=current_district)
    else:
        action = request.form.get('action')
        current_province = request.form['province']
        current_city = request.form['city']
        current_district = request.form['district']
        eq_i_rup = request.form['eq_i_rup']

        if action == "切换城市":
            cities = list(models.Province_City_District[current_province].keys())
            districts = list(models.Province_City_District[current_province][current_city])
            html_content = models.get_map_rupture(current_city)
            return render_template('index.html', 
                html_content=html_content,
                eq_i_rup=eq_i_rup,
                provinces=provinces, current_province=current_province,
                cities=cities, current_city=current_city,
                districts=districts, current_district=current_district)
        elif action == "显示损失分布图":
            return redirect(url_for('LossMap', province=current_province, city=current_city, district=current_district, eq_i_rup=eq_i_rup))

@app.route('/LossMap', methods=['GET','POST'])
def LossMap():

    if request.method == 'GET':
        current_province = request.args.get('province')
        current_city = request.args.get('city')
        current_district = request.args.get('district')
        eq_i_rup = request.args.get('eq_i_rup')
        LossType = 'DS_Struct'
    else:
        action = request.form.get('action')

        current_province = request.form['province']
        current_city = request.form['city']
        current_district = request.form['district']
        eq_i_rup = request.form['eq_i_rup']
        LossType = request.form['LossType']

        if action == "切换城市":
            return redirect(url_for('index', province=current_province, city=current_city, district=current_district))
        elif action == "更新损失地图":
            pass
        
    cities = list(models.Province_City_District[current_province].keys())
    districts = list(models.Province_City_District[current_province][current_city])

    # 地图文件
    html_content = models.get_map_regional_losses(current_city, current_district, i_rup=eq_i_rup, LossType=LossType, savedir=Path(app.static_folder) / 'maps')
    if not html_content:
        return '地图文件不存在！', 404
    eq_info = models.get_EQ_info_from_map(html_content)

    # CDF图文件
    CDF_img_content = models.get_image_CDF_regional_losses(current_city, LossType=LossType, i_rup = eq_i_rup, savedir=Path(app.static_folder) / 'maps')
    # if not CDF_img_content:
    #     return 'CDF图文件不存在！', 404
    
    return render_template('lossmap.html', 
            html_content=html_content, 
            CDF_img_content=CDF_img_content,
            provinces=provinces, current_province=current_province,
            cities=cities, current_city=current_city, 
            districts=districts, current_district=current_district, 
            eq_i_rup=eq_i_rup,
            LossType=LossType,
            eq_magnitude=eq_info['Magnitude'], eq_strike=eq_info['Strike'], eq_dip=eq_info['Dip'], eq_rake=eq_info['Rake'], eq_depth=eq_info['Depth'], eq_length=eq_info['Length'], eq_width=eq_info['Width'])


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

