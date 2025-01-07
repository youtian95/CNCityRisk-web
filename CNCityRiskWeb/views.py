from flask import render_template, request, url_for, redirect, flash, jsonify
from pathlib import Path

from CNCityRiskWeb import app
from CNCityRiskWeb import models

@app.route('/', methods=['GET', 'POST'])
def index():

    provinces = list(models.Province_City_District.keys())
    if request.method == 'POST':
        current_province = request.form['province']
        cities = list(models.Province_City_District[current_province].keys())
        current_city = request.form['city']
        districts = list(models.Province_City_District[current_province][current_city])
        current_district = request.form['district']
        eq_i_rup = request.form['eq_i_rup']
        LossType = request.form['LossType']
    else:
        current_province = '湖北省'
        cities = list(models.Province_City_District[current_province].keys())
        current_city = '武汉'
        districts = list(models.Province_City_District[current_province][current_city])
        current_district = '武昌区'
        eq_i_rup = 0
        LossType='DS_Struct'

    # 地图文件
    map_path = models.get_map_regional_losses(current_city, current_district, i_rup=eq_i_rup, LossType=LossType, savedir=Path(app.static_folder) / 'maps')
    if not map_path:
        flash('地图文件不存在！')
        return redirect(url_for('index'))
    eq_info = models.get_EQ_info_from_map(map_path)
    map_path = str(map_path.relative_to(app.static_folder).as_posix())

    # CDF图文件
    CDF_img_path = models.get_image_CDF_regional_losses(current_city, LossType=LossType, i_rup = eq_i_rup, savedir=Path(app.static_folder) / 'maps')
    if not CDF_img_path:
        flash('CDF图文件不存在！')
        return redirect(url_for('index'))
    CDF_img_path = str(CDF_img_path.relative_to(app.static_folder).as_posix())
    
    return render_template('index.html', map_path=map_path, CDF_img_path=CDF_img_path,
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

