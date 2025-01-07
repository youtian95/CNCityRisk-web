import CNCityRisk.EQsources
from werkzeug.security import generate_password_hash, check_password_hash
import CNCityRisk
import addressparser
import folium
import os
from pathlib import Path
import py7zr
import re
import base64

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

# get rupture map
def get_map_rupture(CityName: str) -> str:
    results_dir = CNCityRisk.EQsources.EQ_SOURCES_OUTPUT_DIR / CityName
    filename = results_dir / 'ruptures.html'
    if not filename.exists():
        return None
    else:
        with open(filename, 'r') as f:
            html_content = f.read()
        return html_content

# get regional seismic loss map
def get_map_regional_losses(CityName, DistrictName='武昌区', LossType='DS_Struct', i_rup: int = 0, iSim: int = 0, savedir = Path(__file__).parent / 'static' / 'maps'):
    filename = f'RegionalLoss_{CityName}_{DistrictName}_{LossType}_{i_rup}_{iSim}.html'

    # 从 static/maps/maps.7z 中读取 filename 的文件，并返回其内容
    zip_path = savedir / 'maps.7z'
    with py7zr.SevenZipFile(zip_path, mode='r') as archive:
        if filename in archive.getnames():
            file_content = archive.read([filename])
            return file_content[filename].read().decode('utf-8')
    return None
        
def get_EQ_info_from_map(html_content) -> dict:
    # <div>Magnitude: 5.55<br>Strike: 330.0<br>Dip: 45.0<br>Rake: 90.0<br>Depth: 15.0<br>Length: 4.3 km<br>Width: 4.6 km</div>
    info = {}
    pattern = re.compile(r'Magnitude:\s*([\d.]+).*?Strike:\s*([\d.]+).*?Dip:\s*([\d.]+).*?Rake:\s*([\d.]+).*?Depth:\s*([\d.]+).*?Length:\s*([\d.]+)\s*km.*?Width:\s*([\d.]+)\s*km', re.IGNORECASE | re.DOTALL)
    match = pattern.search(html_content)
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
def get_image_CDF_regional_losses(CityName, LossType='DS_Struct', i_rup = 0, iSim = 0, savedir =  Path(__file__).parent / 'static' / 'maps'):
    filename = f'CDF_{CityName}_{LossType}_{i_rup}_{iSim}.jpg'
    # 从 static/maps/maps.7z 中读取 filename 的文件，并返回其二进制内容
    zip_path = savedir / 'maps.7z'
    with py7zr.SevenZipFile(zip_path, mode='r') as archive:
        if filename in archive.getnames():
            file_content = archive.read([filename])
            file_content = base64.b64encode(file_content[filename].read()).decode('utf-8')
            return file_content
    return None

def get_image_legend(savedir =  Path(__file__).parent / 'static' / 'maps'):
    filename = 'legend_Bld.png'
    file_path = savedir / filename
    if not file_path.exists():
        return None
    with open(file_path, 'rb') as file:
        file_content = base64.b64encode(file.read()).decode('utf-8')
        return file_content


# 从 CNCityRisk.Data.BldData 文件夹读取城市列表
city_list = get_city_list()
Province_City_District = {}
for city in city_list:
    province = get_province(city)
    if province not in Province_City_District:
        Province_City_District[province] = {}
    Province_City_District[province][city] = get_district_list(city)
