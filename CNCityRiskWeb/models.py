from werkzeug.security import generate_password_hash, check_password_hash
import addressparser
import folium
import os
from pathlib import Path
import re
import base64
import sqlite3
from shapely.geometry import Polygon, MultiPolygon
import numpy as np
import pandas as pd
import json
from cnmaps.maps import get_adm_names, get_adm_maps


STATIC_MAPS_DIR = Path(__file__).parent / 'static' / 'maps'
REGIONAL_STATS_DIR = STATIC_MAPS_DIR / 'RegionalLossStatistics'
ANNUALIZED_RISK_DIR = STATIC_MAPS_DIR / 'AnnualizedRisk'
RUPTURE_DATA_DIR = STATIC_MAPS_DIR / 'Ruptures'


def _get_available_cities_from_static_data():
    if not REGIONAL_STATS_DIR.exists():
        return []
    return sorted([d.name for d in REGIONAL_STATS_DIR.iterdir() if d.is_dir()])


def _get_default_province(city):
    try:
        df = addressparser.transform([city])
        if '省' in df and len(df['省']) > 0:
            province = df['省'][0]
            if isinstance(province, str) and province.strip():
                return province
    except Exception:
        pass
    return '未知'

def get_city_list():
    return _get_available_cities_from_static_data()

def get_province(city):
    return _get_default_province(city)

def get_district_list(CityName):
    # 使用 cnmaps 获取区县列表，兼容“武汉/武汉市”两种输入
    province = get_province(CityName)
    city_candidates = [CityName]

    if not CityName.endswith('市'):
        city_candidates.append(f'{CityName}市')

    for city_name in city_candidates:
        try:
            districts = get_adm_names(
                province=province if province != '未知' else None,
                city=city_name,
                level='区县'
            )
            if districts:
                # 去重并排序，保持前端下拉稳定
                return sorted(set(districts))
        except Exception:
            continue

    # 兜底，避免前端下拉为空
    return ['全市']

# get rupture map
def get_map_rupture(CityName: str) -> str:
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

city_list = get_city_list()
Province_City_District = {}
for city in city_list:
    province = get_province(city)
    if province not in Province_City_District:
        Province_City_District[province] = {}
    Province_City_District[province][city] = get_district_list(city)


def _build_rupture_polygon(center_lat, center_lon, length_km, width_km, strike_deg, dip_deg):
    """参考 Calc4CornersEQRupt 的方法计算破裂面四角点。"""
    half_length = max(length_km, 1.0) / 2.0
    # 宽度在地表投影为 W * cos(dip)
    half_width = max(width_km, 0.5) / 2.0 * np.cos(np.radians(dip_deg))

    # 与参考函数一致的走向与倾向单位向量
    unit_vec_strike = np.array([
        np.cos(np.radians(-strike_deg + 90.0)),
        np.sin(np.radians(-strike_deg + 90.0))
    ])
    unit_vec_dip = np.array([
        np.cos(np.radians(-strike_deg)),
        np.sin(np.radians(-strike_deg))
    ])

    # 按参考函数顺序给出四角点，并闭合为多边形
    corners = []
    for dx, dy in [
        (-half_length, -half_width),
        (half_length, -half_width),
        (half_length, half_width),
        (-half_length, half_width),
        (-half_length, -half_width)
    ]:
        d_vec = dx * unit_vec_strike + dy * unit_vec_dip
        d_lon_km = d_vec[0]
        d_lat_km = d_vec[1]

        # km -> degree (WGS84 局部近似)
        d_lon = d_lon_km * 1000.0 / max(np.cos(np.radians(center_lat)), 1e-6) / 6371000.0 * 180.0 / np.pi
        d_lat = d_lat_km * 1000.0 / 6371000.0 * 180.0 / np.pi
        corners.append([float(center_lat + d_lat), float(center_lon + d_lon)])

    return corners


def _get_rupture_file_path(city_name):
    city_candidates = [city_name]
    if not city_name.endswith('市'):
        city_candidates.append(f'{city_name}市')

    for candidate in city_candidates:
        path = RUPTURE_DATA_DIR / f'{candidate}.csv'
        if path.exists():
            return path
    return None


def _normalize_rupture_row(row, default_index):
    """将 rupture CSV 的一行记录统一为前端需要的结构。"""
    if row is None:
        return None

    def _num(name, default=0.0):
        if name not in row:
            return float(default)
        value = row[name]
        if pd.isna(value):
            return float(default)
        try:
            return float(value)
        except Exception:
            return float(default)

    index = int(_num('i_rup', default_index))
    magnitude = _num('mag', 5.0)
    strike = _num('strike', 0.0)
    dip = _num('dip', 90.0)
    rake = _num('rake', 0.0)
    depth = _num('centroid_depth', 0.0)
    center_lat = _num('centroid_lat', 0.0)
    center_lon = _num('centroid_lon', 0.0)

    if center_lat == 0.0 and center_lon == 0.0:
        return None

    length_km = _num('length_km', max(4.0, 10 ** (0.5 * magnitude - 1.8)))
    width_km = _num('width_km', max(3.0, length_km * 0.6))
    latlon_polygon = _build_rupture_polygon(
        center_lat=center_lat,
        center_lon=center_lon,
        length_km=length_km,
        width_km=width_km,
        strike_deg=strike,
        dip_deg=dip
    )

    return {
        'index': index,
        'latlon_polygon': latlon_polygon,
        'parameters': {
            'magnitude': magnitude,
            'strike': strike,
            'dip': dip,
            'rake': rake,
            'depth': depth,
            'center_lat': center_lat,
            'center_lon': center_lon,
            'rupture_index': index,
            'width_km': width_km,
            'length_km': length_km
        }
    }


def _get_city_polygon_from_cnmaps(city_name):
    """使用 cnmaps 获取城市边界多边形。"""
    province = get_province(city_name)
    city_candidates = [city_name]

    if not city_name.endswith('市'):
        city_candidates.append(f'{city_name}市')

    for candidate in city_candidates:
        try:
            polygon = get_adm_maps(
                province=province if province != '未知' else None,
                city=candidate,
                level='市',
                record='first',
                only_polygon=True
            )
            if isinstance(polygon, list):
                polygon = polygon[0] if polygon else None
            if polygon is not None and not polygon.is_empty:
                return polygon
        except Exception:
            continue

    return None


def get_city_coordinates(city_name=None):
    """
    获取城市的地理坐标数据
    纯展示模式下基于 cnmaps 行政边界数据构造城市多边形
    
    Args:
        city_name (str, optional): 指定城市名称。如果为None，返回所有城市的坐标数据
        
    Returns:
        dict: 城市坐标数据字典
            - 如果指定了city_name，返回 {city_name: {center, bounds, coordinates}}
            - 如果city_name为None，返回 {city1: {center, bounds, coordinates}, city2: {...}, ...}
    """
    city_coordinates = {}

    if city_name:
        candidate_cities = [city_name]
    else:
        candidate_cities = []
        for _, cities in Province_City_District.items():
            candidate_cities.extend(cities.keys())

    for city in candidate_cities:
        polygon = _get_city_polygon_from_cnmaps(city)
        if not polygon:
            continue

        city_data = convert_shapely_to_leaflet_format(polygon)
        if not city_data:
            continue

        city_coordinates[city] = city_data

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
            coordinates = [leaflet_coords]  # 包装成数组格式以保持一致性
            
        elif isinstance(polygon, MultiPolygon):
            # 多个多边形，返回所有多边形的坐标
            coordinates = []
            for geom in polygon.geoms:
                exterior_coords = list(geom.exterior.coords)
                # 转换为[lat, lng]格式
                leaflet_coords = [[coord[1], coord[0]] for coord in exterior_coords]
                coordinates.append(leaflet_coords)
        
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
        rupture_file = _get_rupture_file_path(city_name)
        if not rupture_file:
            return []

        rupture_df = pd.read_csv(rupture_file)
        if rupture_df.empty:
            return []

        ruptures_for_map = []

        for i, (_, row) in enumerate(rupture_df.iterrows()):
            rupture_info = _normalize_rupture_row(row, default_index=i)
            if rupture_info:
                ruptures_for_map.append(rupture_info)

        return ruptures_for_map

    except Exception as e:
        print(f"Error getting all ruptures for {city_name}: {e}")
        return []


def get_whole_city_annualized_loss(city_name):
    """
    获取指定城市的年均损失超越次数等数据
    
    returns:
        dict: 包含年均损失数据的字典，包含以下键：
            - 'freq_mag': 震级频率数据。字典格式，包含 {'Magnitude': [float列表], 'Frequency': [float列表]}
              注意：Frequency为震级年均超越次数（大于等于该震级的年均发生次数）
              例如: {'Magnitude': [5.0, 6.0, 7.0], 'Frequency': [0.1, 0.05, 0.01]}
            - 'freq_RepairCost_Total': 总修复成本的频率数据。字典格式，包含 {'RepairCost_Total': [float列表], 'Frequency': [float列表]}
              例如: {'RepairCost_Total': [1000000.0, 5000000.0], 'Frequency': [0.02, 0.01]}
            - 'freq_RepairTime': 修复时间的频率数据。字典格式，包含 {'RepairTime': [float列表], 'Frequency': [float列表]}
              例如: {'RepairTime': [30.0, 90.0, 180.0], 'Frequency': [0.03, 0.015, 0.005]}
            - 'annual_loss_RepairCost_Total': 总修复成本随时间变化的年损失数据。字典格式，包含 {'Year': [int列表], 'MeanAnnualLoss': [float列表]}
              例如: {'Year': [1, 5, 10, 20], 'MeanAnnualLoss': [50000.0, 49000.0, 48000.0, 47500.0]}
            - 'annual_loss_RepairTime': 修复时间随时间变化的年损失数据。字典格式，包含 {'Year': [int列表], 'MeanAnnualLoss': [float列表]}
              例如: {'Year': [1, 5, 10, 20], 'MeanAnnualLoss': [15.0, 14.8, 14.5, 14.2]}
        如果没有找到相关数据，返回 None
    """
    try:
        # 构建年均损失数据文件夹路径（静态展示数据）
        annualized_loss_dir = ANNUALIZED_RISK_DIR / city_name

        if not annualized_loss_dir.exists():
            return None
        
        annualized_loss_data = {}
        
        # 读取震级频率数据
        freq_mag_file = annualized_loss_dir / "mean_annual_freq_mag.csv"
        if freq_mag_file.exists():
            freq_mag_df = pd.read_csv(freq_mag_file)
            
            # 计算震级的年均超越次数
            # 原始数据是每个震级的年均发生次数，需要转换为超越次数
            magnitudes = freq_mag_df['Magnitude'].tolist()
            frequencies = freq_mag_df['Frequency'].tolist()
            
            # 将震级和频率配对，然后按震级从小到大排序
            mag_freq_pairs = list(zip(magnitudes, frequencies))
            mag_freq_pairs.sort(key=lambda x: x[0])  # 按震级排序
            
            # 分离排序后的震级和频率
            sorted_magnitudes = [pair[0] for pair in mag_freq_pairs]
            sorted_frequencies = [pair[1] for pair in mag_freq_pairs]
            
            # 计算超越次数：对于每个震级，累计大于等于该震级的所有发生次数
            exceedance_frequencies = []
            for i in range(len(sorted_magnitudes)):
                # 累计当前震级及更高震级的发生次数
                exceedance_freq = sum(sorted_frequencies[j] for j in range(i, len(sorted_frequencies)))
                exceedance_frequencies.append(exceedance_freq)
            
            annualized_loss_data['freq_mag'] = {
                'Magnitude': sorted_magnitudes,
                'Frequency': exceedance_frequencies
            }
        
        # 读取损失类型的频率和年损失数据
        loss_types = ['RepairCost_Total', 'RepairTime']
        for loss_type in loss_types:
            # 读取损失频率数据
            freq_loss_file = annualized_loss_dir / f"mean_annual_freq_{loss_type}.csv"
            if freq_loss_file.exists():
                freq_loss_df = pd.read_csv(freq_loss_file)
                annualized_loss_data[f'freq_{loss_type}'] = {
                    loss_type: freq_loss_df[loss_type].tolist(),
                    'Frequency': freq_loss_df['Frequency'].tolist()
                }
            
            # 读取年损失随时间变化数据
            annual_loss_file = annualized_loss_dir / f"mean_annual_loss_with_year_{loss_type}.csv"
            if annual_loss_file.exists():
                annual_loss_df = pd.read_csv(annual_loss_file)
                annualized_loss_data[f'annual_loss_{loss_type}'] = {
                    'Year': annual_loss_df['Year'].tolist(),
                    'MeanAnnualLoss': annual_loss_df['MeanAnnualLoss'].tolist()
                }
        
        return annualized_loss_data if annualized_loss_data else None

    except Exception as e:
        print(f"Error getting annualized loss data for {city_name}: {e}")
        return None
