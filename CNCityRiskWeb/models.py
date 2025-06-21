import CNCityRisk.EQsources
import CNCityRisk.Utilities
from werkzeug.security import generate_password_hash, check_password_hash
import CNCityRisk
import addressparser
import folium
import os
from pathlib import Path
import py7zr
import re
import base64
import sqlite3
from shapely.geometry import Polygon, MultiPolygon
import numpy as np
import pandas as pd
import json

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


def get_EQ_info_from_mbtiles(CityName, LossType='DS_Struct', i_rup=0):
    """从mbtiles文件的元数据中获取地震信息"""
    # 优先查找包含所有rup_index数据的文件
    mbtiles_path = Path(__file__).parent / 'static' / 'maps' / 'mbtiles' / f'RegionalLoss_{CityName}_{LossType}_0_ogr2ogr.mbtiles'
    
    if not mbtiles_path.exists():
        return {}
    
    try:
        conn = sqlite3.connect(str(mbtiles_path))
        cursor = conn.cursor()
        
        # 查询元数据
        cursor.execute("SELECT name, value FROM metadata")
        metadata = dict(cursor.fetchall())
        
        conn.close()
        
        # 尝试从元数据中解析地震信息
        info = {}
        if 'description' in metadata:
            # 假设描述中包含地震参数信息
            desc = metadata['description']
            pattern = re.compile(r'Magnitude:\s*([\d.]+).*?Strike:\s*([\d.]+).*?Dip:\s*([\d.]+).*?Rake:\s*([\d.]+).*?Depth:\s*([\d.]+).*?Length:\s*([\d.]+)\s*km.*?Width:\s*([\d.]+)\s*km', re.IGNORECASE | re.DOTALL)
            match = pattern.search(desc)
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
        
    except Exception as e:
        print(f"Error reading mbtiles metadata: {e}")
        return {}

# 从 CNCityRisk.Data.BldData 文件夹读取城市列表
city_list = get_city_list()
Province_City_District = {}
for city in city_list:
    province = get_province(city)
    if province not in Province_City_District:
        Province_City_District[province] = {}
    Province_City_District[province][city] = get_district_list(city)


def get_city_coordinates():
    """
    获取所有可用城市的地理坐标数据
    使用 CNCityRisk.Utilities.get_city_polygon 函数获取真实的城市边界数据
    """
    try:
        city_coordinates = {}
        
        # 获取所有可用城市
        for province, cities in Province_City_District.items():
            for city in cities.keys():
                try:
                    # 调用CNCityRisk.Utilities.get_city_polygon函数
                    polygon = CNCityRisk.Utilities.get_city_polygon(city)
                    if polygon:
                        # 处理Shapely几何对象
                        city_data = convert_shapely_to_leaflet_format(polygon)
                        if city_data:
                            city_coordinates[city] = city_data
                except Exception as e:
                    print(f"Error getting polygon for {city}: {e}")
                    continue
        
        if city_coordinates:
            return city_coordinates
        
    except Exception as e:
        print(f"Error using CNCityRisk.Utilities.get_city_polygon: {e}")
    
    return city_coordinates

def convert_shapely_to_leaflet_format(polygon):
    """
    将Shapely几何对象转换为Leaflet地图需要的格式
    
    Args:
        polygon: shapely.geometry.polygon.Polygon or shapely.geometry.multipolygon.MultiPolygon
        
    Returns:
        dict: 包含center, bounds, coordinates的字典，适用于Leaflet地图
    """
    try:
        
        if not polygon or polygon.is_empty:
            return None
        
        # 获取边界框
        minx, miny, maxx, maxy = polygon.bounds
        
        # 计算中心点
        centroid = polygon.centroid
        center = [centroid.y, centroid.x]  # Leaflet使用[lat, lng]格式
        
        # 创建边界框（矩形）用于简单显示
        bounds = [
            [miny, minx],  # 西南角
            [maxy, minx],  # 西北角
            [maxy, maxx],  # 东北角
            [miny, maxx]   # 东南角
        ]
        
        # 获取实际多边形坐标
        coordinates = []
        
        if isinstance(polygon, Polygon):
            # 单个多边形
            exterior_coords = list(polygon.exterior.coords)
            # 转换为[lat, lng]格式
            leaflet_coords = [[coord[1], coord[0]] for coord in exterior_coords]
            coordinates = leaflet_coords
            
        elif isinstance(polygon, MultiPolygon):
            # 多个多边形，取最大的一个
            largest_polygon = max(polygon.geoms, key=lambda p: p.area)
            exterior_coords = list(largest_polygon.exterior.coords)
            # 转换为[lat, lng]格式
            leaflet_coords = [[coord[1], coord[0]] for coord in exterior_coords]
            coordinates = leaflet_coords
        
        return {
            'center': center,
            'bounds': bounds,
            'coordinates': coordinates  # 实际多边形坐标
        }
        
    except Exception as e:
        print(f"Error converting shapely polygon to leaflet format: {e}")
        return None


def get_city_all_ruptures_for_map(city_name):
    """
    获取城市所有震源数据，用于在地图上显示
    
    Args:
        city_name: 城市名称
        
    Returns:
        list: 包含所有震源多边形和信息的列表
    """
    try:
        # 调用CNCityRisk.EQsources.ReadCityRuptures函数
        ruptures_df = CNCityRisk.EQsources.ReadCityRuptures(city_name)
        
        if ruptures_df is None or len(ruptures_df) == 0:
            return []
        
        ruptures_for_map = []
        
        for index, rupture_series in ruptures_df.iterrows():
            try:
                # 调用Create_a_Rupture_Polygon函数获取多边形
                _, latlon_polygon = CNCityRisk.EQsources.Create_a_Rupture_Polygon(
                    m=None,
                    rupture=rupture_series
                )
                
                # 准备震源信息
                rupture_info = {
                    'index': index,
                    'latlon_polygon': latlon_polygon,
                    'parameters': {
                        'magnitude': float(rupture_series['mag']),
                        'strike': float(rupture_series['strike']),
                        'dip': float(rupture_series['dip']),
                        'rake': float(rupture_series['rake']),
                        'depth': float(rupture_series['centroid_depth']),
                        'center_lat': float(rupture_series['centroid_lat']),
                        'center_lon': float(rupture_series['centroid_lon']),
                        'rupture_index': index
                    }
                }
                
                # 如果有宽度和长度信息，也包含进来
                if 'W_km' in rupture_series:
                    rupture_info['parameters']['width_km'] = float(rupture_series['W_km'])
                if 'length_km' in rupture_series:
                    rupture_info['parameters']['length_km'] = float(rupture_series['length_km'])
                
                ruptures_for_map.append(rupture_info)
                
            except Exception as e:
                print(f"Error processing rupture {index}: {e}")
                continue
        
        return ruptures_for_map
        
    except Exception as e:
        print(f"Error getting all ruptures for {city_name}: {e}")
        return []



