from werkzeug.security import generate_password_hash, check_password_hash
import CNCityRisk
import addressparser
import folium
import os
from pathlib import Path
import py7zr
import re

def get_city_list():
    base_path = os.path.join(os.path.dirname(CNCityRisk.__file__), 'Data', 'BldData')
    cities = [name for name in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, name))]
    return cities

def get_province(city):
    df = addressparser.transform([city])
    return df['省'][0]

def get_district_list(CityName):
    base_path = os.path.join(os.path.dirname(CNCityRisk.__file__), 'Data', 'BldData', CityName)
    districts = [os.path.splitext(name)[0] for name in os.listdir(base_path) if os.path.isfile(os.path.join(base_path, name))]
    return districts

# plot regional seismic loss
def get_map_regional_losses(CityName, DistrictName='武昌区', LossType='DS_Struct', i_rup: int = 0, iSim: int = 0, savedir =  Path(__file__).parent / 'static' / 'maps') -> Path:
    filename = f'RegionalLoss_{CityName}_{DistrictName}_{LossType}_{i_rup}_{iSim}.html'

    # 从 static/maps/maps.7z 中解压出filename的文件，并且放到static/maps/中，重命名为map.html
    zip_path = savedir / 'maps.7z'
    with py7zr.SevenZipFile(zip_path, mode='r') as archive:
        if filename in archive.getnames():
            archive.extract(targets=[filename], path=savedir)
            extracted_file = savedir / filename
            map_file = savedir / 'map.html'
            if map_file.exists():
                map_file.unlink()  # 删除已存在的 map.html 文件
            extracted_file.rename(map_file)
            return map_file
        else:
            return None
        
def get_EQ_info_from_map(filename = Path(__file__).parent / 'static' / 'maps' / 'map.html') -> dict:
    # <div>Magnitude: 5.55<br>Strike: 330.0<br>Dip: 45.0<br>Rake: 90.0<br>Depth: 15.0<br>Length: 4.3 km<br>Width: 4.6 km</div>
    info = {}
    with open(filename, 'r', encoding='utf-8') as file:
        content = file.read()
        pattern = re.compile(r'Magnitude:\s*([\d.]+).*?Strike:\s*([\d.]+).*?Dip:\s*([\d.]+).*?Rake:\s*([\d.]+).*?Depth:\s*([\d.]+).*?Length:\s*([\d.]+)\s*km.*?Width:\s*([\d.]+)\s*km', re.IGNORECASE | re.DOTALL)
        match = pattern.search(content)
        if match:
            info = {
                'Magnitude': float(match.group(1)),
                'Strike': float(match.group(2)),
                'Dip': float(match.group(3)),
                'Rake': float(match.group(4)),
                'Depth': float(match.group(5)),
                'Length': float(match.group(6)),
                'Width': float(match.group(7))
            }
    return info



# plot CDF of regional seismic loss
def get_image_CDF_regional_losses(CityName, LossType='DS_Struct', i_rup = 0, iSim = 0, savedir =  Path(__file__).parent / 'static' / 'maps') -> Path:
    filename = f'CDF_{CityName}_{LossType}_{i_rup}_{iSim}.jpg'

    # 从 static/maps/maps.7z 中解压出filename的文件，并且放到static/maps/中，重命名为CDF.jpg
    zip_path = savedir / 'maps.7z'
    with py7zr.SevenZipFile(zip_path, mode='r') as archive:
        if filename in archive.getnames():
            archive.extract(targets=[filename], path=savedir)
            extracted_file = savedir / filename
            image_file = savedir / 'CDF.jpg'
            if image_file.exists():
                image_file.unlink()  # 删除已存在的 CDF.jpg 文件
            extracted_file.rename(image_file)
            return image_file
        else:
            return None


# 从 CNCityRisk.Data.BldData 文件夹读取城市列表
city_list = get_city_list()
Province_City_District = {}
for city in city_list:
    province = get_province(city)
    if province not in Province_City_District:
        Province_City_District[province] = {}
    Province_City_District[province][city] = get_district_list(city)
