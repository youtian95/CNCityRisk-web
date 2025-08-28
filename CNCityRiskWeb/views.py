from flask import render_template, request, url_for, redirect, flash, jsonify, send_file, abort
from pathlib import Path
import sqlite3
import os
from urllib.parse import unquote, quote
import io
import gzip
import json
import ijson
import h5py
import numpy as np

from CNCityRiskWeb import app
from CNCityRiskWeb import models

provinces = list(models.Province_City_District.keys())

@app.route('/')
def index():
    """新的首页 - 城市选择地图界面"""
    return render_template('city_selection_map.html', available_cities=models.Province_City_District)

@app.route('/LossMap', methods=['GET'])
def LossMap():
    """
    损失地图页面路由
    只支持GET请求，仅使用mbtiles格式地图
    """
    # 获取请求参数
    current_city = request.args.get('city')
    eq_i_rup = request.args.get('eq_i_rup', '0')
    LossType = request.args.get('LossType', 'DS_Struct')
    iSim = request.args.get('iSim', '0') 

    # 验证必需参数
    if not current_city:
        flash('缺少必需的参数', 'error')
        return redirect(url_for('index'))
    
    # 检查mbtiles文件是否存在
    mbtiles_path = Path(app.static_folder) / 'maps' / 'mbtiles' / f'RegionalLoss_{current_city}_{LossType}_{iSim}_ogr2ogr.mbtiles'
    has_mbtiles = mbtiles_path.exists()
    
    # 如果没有mbtiles文件，返回错误
    if not has_mbtiles:
        app.logger.error(f'MBTiles file not found: {mbtiles_path}')
        flash(f'城市 {current_city} 的损失地图数据不存在', 'error')
        return redirect(url_for('rupture_selection', city=current_city))
    
    # 模板上下文数据
    template_context = {
        'current_city': current_city,
        'eq_i_rup': eq_i_rup,
        'LossType': LossType,
        'has_mbtiles': has_mbtiles,
        'iSim': iSim
    }
    
    # 只使用mbtiles地图模板
    app.logger.info(f'Rendering mbtiles map for {current_city}, rupture {eq_i_rup}')
    return render_template('lossmap_mbtiles.html', **template_context)

# 新增异步获取建筑群损失地图数据的路由
@app.route('/get_map_data')
def get_map_data():
    """
    获取区域损失地图数据，则返回瓦片URL和边界信息
    """
    current_city = request.args.get('city')
    eq_i_rup = int(request.args.get('eq_i_rup', 0))
    LossType = request.args.get('LossType', 'DS_Struct')
    iSim = request.args.get('iSim', '0')
    
    # 使用mbtiles矢量瓦片
    # 修改文件路径逻辑：使用 iSim 参数
    mbtiles_path = Path(app.static_folder) / 'maps' / 'mbtiles' / f'RegionalLoss_{current_city}_{LossType}_{iSim}_ogr2ogr.mbtiles'
    
    if not mbtiles_path.exists():
        return jsonify({'error': 'MBTiles文件不存在！'}), 404
        
    encoded_city = quote(current_city)
    tile_url = f"{request.url_root}tiles/{encoded_city}/{LossType}/{{z}}/{{x}}/{{y}}.pbf"
    
    # 获取MBTiles边界信息
    bounds = None
    try:
        conn = sqlite3.connect(str(mbtiles_path))
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE name='bounds'")
        bounds_result = cursor.fetchone()
        if bounds_result:
            bounds = [float(x) for x in bounds_result[0].split(',')]
        conn.close()
    except Exception as e:
        app.logger.warning(f"Could not get bounds from MBTiles: {e}")
    # 从mbtiles获取地震信息（如果有的话）
    eq_info = models.get_EQ_info_from_mbtiles(current_city, LossType, eq_i_rup)
    
    return jsonify({
        'use_mbtiles': True,
        'tile_url': tile_url,
        'bounds': bounds,
        'eq_info': eq_info
    })


@app.route('/LossStatistics', methods=['GET'])
def LossStatistics():
    """
    建筑群损失统计信息页面路由
    显示指定城市和损失类型的所有地震事件统计信息
    """
    # 获取请求参数
    current_city = request.args.get('city')
    LossType = request.args.get('LossType', 'DS_Struct')
    eq_i_rup = request.args.get('eq_i_rup', '0')
    iSim = request.args.get('iSim', '0')
    
    # 验证必需参数
    if not current_city:
        flash('缺少必需的参数', 'error')
        return redirect(url_for('index'))
    
    # 检查统计文件是否存在
    stats_path = Path(app.static_folder) / 'maps' / 'RegionalLossStatistics' / current_city / f'RegionalLossStatistics_{LossType}.json'
    
    if not stats_path.exists():
        app.logger.error(f'Statistics file not found: {stats_path}')
        flash(f'城市 {current_city} 的损失统计数据不存在', 'error')
        return redirect(url_for('index'))
    
    # 模板上下文数据
    template_context = {
        'current_city': current_city,
        'LossType': LossType,
        'iSim': iSim,
        'eq_i_rup': eq_i_rup
    }
    
    app.logger.info(f'Rendering loss statistics for {current_city}, loss type {LossType}')
    return render_template('loss_statistics.html', **template_context)

@app.route('/get_loss_statistics')
def get_loss_statistics():
    """
    获取损失统计数据的API端点，支持获取单个震源或所有震源的统计信息

    参数:
        city: 城市名称
        LossType: 损失类型
        eq_i_rup: 震源索引，如果提供则只返回该震源的统计信息；如果不提供则返回所有震源

    返回格式:
        {
            "CityName": "城市名称",
            "LossType": "损失类型",
            "generated_at": "生成时间戳 (ISO格式)",
            "total_earthquakes": "地震事件总数 (int)",
            "earthquake_events": [
                {
                    "i_rup": "震源索引 (int)",
                    "rup_id": "震源ID (str)",
                    "earthquake_info": {
                        "magnitude": "震级 (float)",
                        "centroid_lat": "震中纬度 (float)",
                        "centroid_lon": "震中经度 (float)", 
                        "hypo_depth": "震源深度 (float)",
                        "strike": "走向角 (float)",
                        "dip": "倾角 (float)",
                        "rake": "滑动角 (float)",
                        "trt": "构造类型 (str)",
                        "source_id": "震源ID (str)"
                    },
                    "simulation_info": {
                        "total_simulations": "该震源的总模拟次数 (int)",
                        "selected_iSim": "选择的模拟索引 (int)",
                        "simulation_indices": "所有模拟索引列表 (list[int])"
                    },
                    "loss_statistics": {
                        "total_loss_sim": "所有模拟的损失分布 (N_DS x N_sim 数组)",
                        "total_loss_iSim": "指定模拟的总损失 (N_DS 数组)",
                        "percentiles_iSim": "指定模拟在分布中的百分位数 (N_DS 数组)",
                        "damage_state_names": "损伤状态名称列表 (仅损伤状态类型)",
                        "loss_description": "损失描述 (str)"
                    }
                }
            ],
            "summary": {
                "successful_events": "成功处理的事件数 (int)",
                "failed_events": "处理失败的事件数 (int)",
                "success_rate": "成功率 (float, 0-1)"
            }
        }

    损失统计数据说明:
        - 对于损伤状态类型 (DS_*):
            * N_DS = 5 (对应5个损伤状态: 'DS0', 'DS1', 'DS2', 'DS3', 'DS4')
            * total_loss_sim[i,j]: 第j次模拟中处于第i个损伤状态的建筑物数量
            * total_loss_iSim[i]: 指定模拟中处于第i个损伤状态的建筑物数量
            * percentiles_iSim[i]: 指定模拟中第i个损伤状态建筑数量在所有模拟中的百分位数
        
        - 对于连续损失类型 (RepairCost_*, RepairTime等):
            * N_DS = 1
            * total_loss_sim[0,j]: 第j次模拟的总损失值
            * total_loss_iSim[0]: 指定模拟的总损失值
            * percentiles_iSim[0]: 指定模拟的总损失值在所有模拟中的百分位数
    """
    current_city = request.args.get('city')
    LossType = request.args.get('LossType', 'DS_Struct')
    eq_i_rup = request.args.get('eq_i_rup')  # 可选参数
    
    if not current_city:
        return jsonify({'error': '缺少城市参数'}), 400
    
    # 读取统计文件
    stats_path = Path(app.static_folder) / 'maps' / 'RegionalLossStatistics' / current_city / f'RegionalLossStatistics_{LossType}.json'
    
    if not stats_path.exists():
        return jsonify({'error': '统计文件不存在'}), 404
    
    try:
        with open(stats_path, 'r', encoding='utf-8') as f:
            stats_data = json.load(f)
        
        # 如果指定了震源索引，只返回该震源的信息
        if eq_i_rup is not None:
            try:
                eq_i_rup = int(eq_i_rup)
            except ValueError:
                return jsonify({'error': '震源索引必须是整数'}), 400
            
            # 查找指定的震源事件
            target_event = None
            for event in stats_data.get('earthquake_events', []):
                if event.get('i_rup') == eq_i_rup:
                    target_event = event
                    break
            
            if target_event is None:
                return jsonify({'error': f'未找到震源索引 {eq_i_rup} 的统计数据'}), 404
            
            # 返回单个震源的信息
            return jsonify({
                'CityName': stats_data.get('CityName'),
                'LossType': stats_data.get('LossType'),
                'generated_at': stats_data.get('generated_at'),
                'eq_i_rup': eq_i_rup,
                'earthquake_event': target_event
            })
        else:
            # 返回所有震源的统计信息
            return jsonify(stats_data)
            
    except Exception as e:
        app.logger.error(f"Error reading statistics file: {e}")
        return jsonify({'error': '读取统计文件失败'}), 500


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

@app.route('/get_city_coordinates')
def get_city_coordinates():
    """
    获取城市的地理坐标数据
    
    该函数通过调用 models.get_city_coordinates() 获取城市的地理边界和中心坐标信息。
    如果提供了城市名参数，则只返回该城市的坐标数据；否则返回所有可用城市的坐标数据。
    
    Args:
        city (str, optional): 城市名称，通过 URL 参数传递。如果提供，只返回该城市的坐标数据。
    
    Returns:
        JSON: 包含城市坐标信息的字典，格式如下：
        
        当请求单个城市时 (GET /get_city_coordinates?city=武汉):
        {
            "province": "省份名",
            "center": [纬度, 经度],  # 城市中心坐标
            "bounds": [[south, west], [north, west], [north, east], [south, east]],  # 城市边界矩形
            "coordinates": [[[纬度1, 经度1], [纬度2, 经度2], ...], [[纬度3, 经度3], ...]],  # 城市边界多边形数组，每个子数组是一个多边形的坐标点
            "district_count": 区县数量
        }
        
        当请求所有城市时 (GET /get_city_coordinates):
        {
            "城市名": {
                "province": "省份名",
                "center": [纬度, 经度],
                "bounds": [[south, west], [north, west], [north, east], [south, east]],
                "coordinates": [[[纬度1, 经度1], [纬度2, 经度2], ...], [[纬度3, 经度3], ...]],  # 城市边界多边形数组，每个子数组是一个多边形的坐标点
                "district_count": 区县数量
            },
            ...
        }
    
    注意:
        - 坐标格式统一为 [纬度, 经度]
        - center: 城市的地理中心点坐标
        - bounds: 城市的最小外接矩形，按 [south, west], [north, west], [north, east], [south, east] 顺序
        - coordinates: 城市实际边界的多边形数组，每个元素是一个多边形的坐标点数组。对于单个多边形的城市，仍然是数组格式[[多边形坐标]]；对于多个多边形的城市，包含所有多边形的坐标[多边形1坐标, 多边形2坐标, ...]
        - 只返回在系统中有区县数据支持的城市
        - 如果请求的城市不存在，返回 404 错误
    
    Examples:
        GET /get_city_coordinates  # 获取所有城市坐标
        GET /get_city_coordinates?city=武汉  # 获取武汉的坐标
    """    
    # 获取请求参数
    requested_city = request.args.get('city')
    
    # 根据请求参数调用相应的函数
    if requested_city:
        # 如果指定了城市，只获取该城市的数据
        coordinates = models.get_city_coordinates(requested_city)
        
        if not coordinates:
            return jsonify({'error': f'城市 "{requested_city}" 不存在或没有坐标数据'}), 404
        
        # 获取城市的省份和区县信息
        province = None
        district_count = 0
        for prov, cities in models.Province_City_District.items():
            if requested_city in cities:
                province = prov
                district_count = len(cities[requested_city])
                break
        
        # 构建返回数据
        city_data = coordinates[requested_city]
        city_data['province'] = province
        city_data['district_count'] = district_count
        
        return jsonify(city_data)
    else:
        # 获取所有城市坐标数据
        coordinates = models.get_city_coordinates()
        
        # 构建可用城市的坐标数据
        available_coordinates = {}
        for province, cities in models.Province_City_District.items():
            for city in cities.keys():
                if city in coordinates:
                    available_coordinates[city] = {
                        'province': province,
                        'center': coordinates[city]['center'],
                        'bounds': coordinates[city]['bounds'],
                        'coordinates': coordinates[city]['coordinates'],
                        'district_count': len(cities[city])
                    }
        
        # 返回所有可用城市的坐标
        return jsonify(available_coordinates)

# 新增mbtiles瓦片服务路由 - 修改为不包含rup_index的路由
@app.route('/tiles/<city>/<loss_type>/<int:z>/<int:x>/<int:y>.pbf')
def serve_mbtiles(city, loss_type, z, x, y):
    """服务mbtiles矢量瓦片 - 所有rup_index数据在同一个文件中"""

    # 解码URL编码的城市名称
    city = unquote(city)
    
    # 修改文件路径：移除rup_index，假设所有数据在一个文件中
    mbtiles_path = Path(app.static_folder) / 'maps' / 'mbtiles' / f'RegionalLoss_{city}_{loss_type}_0_ogr2ogr.mbtiles'
    
    if not mbtiles_path.exists():
        abort(404)
    
    try:
        conn = sqlite3.connect(mbtiles_path)
        cursor = conn.cursor()          
        # MBTiles中tile_row是TMS规范，需转换为XYZ规范（y = (2^z - 1) - y）
        y_tms = (2 ** z - 1) - y
        cursor.execute("SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?", (z, x, y_tms))
        result = cursor.fetchone()
        conn.close()
        
        if result is None:
            # 瓦片不存在，这是正常的
            app.logger.warning(f"Tile not found: {city}/{loss_type}/{z}/{x}/{y}")
            abort(404)
        
        tile_data = result[0]        
        # 检查数据是否被gzip压缩（mbtiles通常会压缩瓦片数据）
        if tile_data[:2] == b'\x1f\x8b':  # gzip 文件头
            try:
                tile_data = gzip.decompress(tile_data)
            except Exception as e:
                app.logger.error(f"解压瓦片数据失败: {e}")
                abort(500)
        
        app.logger.info(f"Served tile {city}/{loss_type}/{z}/{x}/{y}")
        return send_file(io.BytesIO(tile_data), mimetype='application/vnd.mapbox-vector-tile')
    
    except sqlite3.Error as e:
        if 'conn' in locals():
            conn.close()
        app.logger.error(f"SQLite error serving tile {city}/{loss_type}/{z}/{x}/{y}: {str(e)}")
        abort(500)
    
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        # 如果是404错误，直接重新抛出
        if '404 Not Found' in str(e):
            raise
        app.logger.error(f"Unexpected error serving tile {city}/{loss_type}/{z}/{x}/{y}: {str(e)}")
        abort(500)

@app.route('/rupture_selection')
def rupture_selection():
    """震源选择界面"""
    current_city = request.args.get('city', '武汉')
    
    # 获取城市所有震源数据
    ruptures_data = models.get_city_all_ruptures_for_map(current_city)
    
    # 如果有震源数据，使用第一个震源的中心作为地图中心
    center_lat, center_lon = 30.5928, 114.3055  # 默认武汉坐标
    if ruptures_data:
        center_lat = ruptures_data[0]['parameters']['center_lat']
        center_lon = ruptures_data[0]['parameters']['center_lon']
    
    return render_template('rupture_selection.html',
        current_city=current_city,
        center_lat=center_lat,
        center_lon=center_lon,
        ruptures_data=ruptures_data)


@app.route('/get_city_all_ruptures/<city_name>')
def get_city_all_ruptures(city_name):
    """获取指定城市的所有震源多边形数据"""
    try:
        ruptures_data = models.get_city_all_ruptures_for_map(city_name)
        return jsonify({
            'success': True,
            'data': ruptures_data,
            'count': len(ruptures_data)
        })
    except Exception as e:
        return jsonify({'error': f'获取城市震源数据失败: {str(e)}'}), 500

@app.route('/IMMap', methods=['GET'])
def IMMap():
    """
    IM中值云图页面路由
    显示某城市某破裂面的IM中值云图
    """
    # 获取请求参数
    current_city = request.args.get('city', '武汉')
    eq_i_rup = request.args.get('eq_i_rup', '0')
    period_index = request.args.get('period_index', '0')
    
    # 转换索引为整数
    try:
        eq_i_rup = int(eq_i_rup)
        period_index = int(period_index)
    except ValueError:
        eq_i_rup = 0
        period_index = 0
    # 检查IM网格数据文件是否存在 - 更新为HDF5格式
    im_data_path = Path(app.static_folder) / 'maps' / 'IMmap' / f'IM_mapdata_{current_city}.hdf5'
    
    if not im_data_path.exists():
        app.logger.error(f'IM grid data file not found: {im_data_path}')
        flash(f'城市 {current_city} 的IM网格数据不存在', 'error')
        return redirect(url_for('rupture_selection', city=current_city))
    
    # 从HDF5文件获取IM元数据
    try:
        with h5py.File(im_data_path, 'r') as hf:
            # 读取全局元数据并转换为JSON可序列化的格式
            im_metadata = {}
            for key, value in hf.attrs.items():
                if isinstance(value, np.integer):
                    im_metadata[key] = int(value)
                elif isinstance(value, np.floating):
                    im_metadata[key] = float(value)
                elif isinstance(value, np.ndarray):
                    im_metadata[key] = value.tolist()
                elif isinstance(value, bytes):
                    im_metadata[key] = value.decode('utf-8')
                else:
                    im_metadata[key] = value
            
            # 处理periods数据为前端期望的格式
            if 'periods' in hf:
                periods_array = hf['periods'][:]
                im_metadata['periods'] = {}
                for i, p in enumerate(periods_array):
                    period_val = float(p)
                    if np.isfinite(period_val):
                        im_metadata['periods'][i] = {
                            'period_value': period_val,
                            'index': i
                        }
            else:
                im_metadata['periods'] = {}
            
            # 验证和修正参数范围
            total_ruptures = im_metadata.get('total_ruptures', 0)
            total_periods = im_metadata.get('total_periods', 0)
            
            if not (0 <= eq_i_rup < total_ruptures):
                eq_i_rup = 0
            if not (0 <= period_index < total_periods):
                period_index = 0
                
    except Exception as e:
        app.logger.error(f'Failed to read IM metadata from {im_data_path}: {e}')
        flash(f'无法读取城市 {current_city} 的IM地图元数据', 'error')
        return redirect(url_for('rupture_selection', city=current_city))
    # 准备模板数据（移除震源几何数据，由前端API获取）
    template_context = {
        'current_city': current_city,
        'eq_i_rup': eq_i_rup,
        'period_index': period_index,
        'im_metadata': im_metadata
    }
    app.logger.info(f'Rendering IM map for {current_city}, rupture {eq_i_rup}, period {period_index}')
    return render_template('im_map.html', **template_context)

@app.route('/get_im_grid_data')
def get_im_grid_data():
    """
    获取IM网格数据用于等值线生成
    从 IM_mapdata_{city}.hdf5 文件中提取指定破裂面和周期的数据
    """
    current_city = request.args.get('city')
    eq_i_rup = request.args.get('eq_i_rup')
    period_index = request.args.get('period_index')
    isim = request.args.get('isim', default=None)
    
    if isim is not None:
        try:
            isim = int(isim)
        except ValueError:
            return jsonify({'error': 'isim参数必须为整数'}), 400
    
    # 验证必需参数
    if not current_city or eq_i_rup is None or period_index is None:
        return jsonify({'error': '缺少必需的参数: city, eq_i_rup, period_index'}), 400
    
    try:
        eq_i_rup = int(eq_i_rup)
        period_index = int(period_index)
    except ValueError:
        return jsonify({'error': '破裂面索引和周期索引必须是整数'}), 400
    
    # 构建IM网格数据文件路径 - 更新为HDF5格式
    im_data_path = Path(app.static_folder) / 'maps' / 'IMmap' / f'IM_mapdata_{current_city}.hdf5'
    
    if not im_data_path.exists():
        return jsonify({'error': f'城市 {current_city} 的IM网格数据文件不存在'}), 404
    
    try:
        with h5py.File(im_data_path, 'r') as hf:
            # 读取全局元数据并转换为JSON可序列化的格式
            metadata = {}
            for key, value in hf.attrs.items():
                if isinstance(value, np.integer):
                    metadata[key] = int(value)
                elif isinstance(value, np.floating):
                    metadata[key] = float(value)
                elif isinstance(value, np.ndarray):
                    metadata[key] = value.tolist()
                elif isinstance(value, bytes):
                    metadata[key] = value.decode('utf-8')
                else:
                    metadata[key] = value
            
            total_ruptures = metadata.get('total_ruptures', 0)
            total_periods = metadata.get('total_periods', 0)
            selected_iSim = metadata.get('selected_iSim', 0)
            
            # 验证参数范围
            if not (0 <= eq_i_rup < total_ruptures):
                return jsonify({'error': f'破裂面索引 {eq_i_rup} 超出范围 [0, {total_ruptures-1}]'}), 400
            
            if not (0 <= period_index < total_periods):
                return jsonify({'error': f'周期索引 {period_index} 超出范围 [0, {total_periods-1}]'}), 400
            
            # 如果指定了isim，验证范围
            if isim is not None and isim != selected_iSim:
                return jsonify({'error': f'指定的isim索引 {isim} 与HDF5文件中的选定索引 {selected_iSim} 不匹配'}), 400
            
            # 读取站点坐标数据
            site_coords = hf['site_coordinates']
            site_ids = site_coords['site_id'][:]
            longitudes = site_coords['longitude'][:]
            latitudes = site_coords['latitude'][:]
            
            # 读取周期数据
            periods = hf['periods'][:]
            
            # 读取指定破裂面的数据
            rupture_group_name = f'rupture_{eq_i_rup}'
            if rupture_group_name not in hf:
                return jsonify({'error': f'破裂面 {eq_i_rup} 的数据不存在'}), 404
            
            rupture_group = hf[rupture_group_name]
            rupture_metadata = {}
            for key, value in rupture_group.attrs.items():
                if isinstance(value, np.integer):
                    rupture_metadata[key] = int(value)
                elif isinstance(value, np.floating):
                    rupture_metadata[key] = float(value)
                elif isinstance(value, np.ndarray):
                    rupture_metadata[key] = value.tolist()
                elif isinstance(value, bytes):
                    rupture_metadata[key] = value.decode('utf-8')
                else:
                    rupture_metadata[key] = value
            
            # 根据isim参数选择数据集：isim为None时使用中值数据，否则使用随机数据
            dataset_name = 'im_median' if isim is None else 'im_random'
            
            if dataset_name not in rupture_group:
                return jsonify({'error': f'破裂面 {eq_i_rup} 的{dataset_name}数据不存在'}), 404
            
            # 读取IM数据 - 形状为 [n_sites, n_periods]
            im_data = rupture_group[dataset_name][:, period_index]
            
            # 构建网格数据
            grid_data = []
            for lon, lat, im_value in zip(longitudes, latitudes, im_data):
                if np.isfinite(im_value) and im_value > 0:
                    grid_data.append([float(lon), float(lat), float(im_value)])
            
            # 计算数据边界
            bounds = {}
            if grid_data:
                lons = [point[0] for point in grid_data]
                lats = [point[1] for point in grid_data]
                values = [point[2] for point in grid_data]
                
                bounds = {
                    'min_lon': min(lons),
                    'max_lon': max(lons),
                    'min_lat': min(lats),
                    'max_lat': max(lats),
                    'min_value': min(values),
                    'max_value': max(values)
                }
            
            # 返回结果
            return jsonify({
                'grid_data': grid_data,
                'metadata': {
                    'city': current_city,
                    'rupture_index': eq_i_rup,
                    'period_index': period_index,
                    'data_type': dataset_name,
                    'total_points': len(grid_data),
                    'total_sites': len(site_ids),
                    'rupture_info': {
                        'rupture_id': rupture_metadata.get('rupture_id', ''),
                        'magnitude': rupture_metadata.get('magnitude', 0.0),
                        'index': rupture_metadata.get('index', eq_i_rup)
                    },
                    'period_info': {
                        'period_value': float(periods[period_index]),
                        'index': period_index
                    },
                    'hdf5_metadata': {
                        'total_ruptures': total_ruptures,
                        'total_periods': total_periods,
                        'selected_iSim': selected_iSim,
                        'data_structure': metadata.get('description', '')
                    },
                    'bounds': bounds
                }
            })
    
    except (OSError, IOError) as e:
        # HDF5文件相关的IO错误
        app.logger.error(f'读取HDF5文件失败: {e}')
        return jsonify({'error': 'HDF5数据文件格式错误或损坏'}), 500
    except KeyError as e:
        app.logger.error(f'HDF5文件中缺少必需的数据集: {e}')
        return jsonify({'error': f'数据文件中缺少必需的数据: {e}'}), 500
    except FileNotFoundError as e:
        app.logger.error(f'IM数据文件未找到: {e}')
        return jsonify({'error': 'IM数据文件不存在'}), 404
    except MemoryError as e:
        app.logger.error(f'内存不足，无法处理IM数据文件: {e}')
        return jsonify({'error': '数据文件过大，内存不足'}), 507
    except Exception as e:
        app.logger.error(f'获取IM网格数据时发生错误: {e}')
        return jsonify({'error': '服务器内部错误'}), 500

@app.route('/annualized_risk/<city_name>')
def annualized_risk(city_name):
    """
    年化损失分析页面路由
    显示指定城市的年化损失分析页面
    """
    return render_template('annualized_risk.html', city_name=city_name)


@app.route('/get_whole_city_annualized_loss/<city_name>')
def get_whole_city_annualized_loss(city_name):
    """
    获取指定城市的年化损失数据
    
    返回格式为JSON，包含年化损失和相关信息

    returns:
        dict: 包含年均损失数据的字典，包含以下键：
            - 'freq_mag': 震级频率数据。字典格式，包含 {'Magnitude': [float列表], 'Frequency': [float列表]}
              例如: {'Magnitude': [5.0, 6.0, 7.0], 'Frequency': [0.1, 0.05, 0.01]}
            - 'freq_RepairCost_Total': 总修复成本的频率数据。字典格式，包含 {'RepairCost_Total': [float列表], 'Frequency': [float列表]}
              例如: {'RepairCost_Total': [1000000.0, 5000000.0], 'Frequency': [0.02, 0.01]}
            - 'freq_RepairTime': 修复时间的频率数据。字典格式，包含 {'RepairTime': [float列表], 'Frequency': [float列表]}
              例如: {'RepairTime': [30.0, 90.0, 180.0], 'Frequency': [0.03, 0.015, 0.005]}
            - 'annual_loss_RepairCost_Total': 总修复成本随时间变化的年损失数据。字典格式，包含 {'Year': [int列表], 'MeanAnnualLoss': [float列表]}
              例如: {'Year': [1, 5, 10, 20], 'MeanAnnualLoss': [50000.0, 49000.0, 48000.0, 47500.0]}
            - 'annual_loss_RepairTime': 修复时间随时间变化的年损失数据。字典格式，包含 {'Year': [int列表], 'MeanAnnualLoss': [float列表]}
              例如: {'Year': [1, 5, 10, 20], 'MeanAnnualLoss': [15.0, 14.8, 14.5, 14.2]}
    """
    try:
        # 从模型中获取年化损失数据
        annualized_loss_data = models.get_whole_city_annualized_loss(city_name)
        
        if not annualized_loss_data:
            return jsonify({'error': f'城市 {city_name} 的年化损失数据不存在'}), 404
        
        return jsonify(annualized_loss_data)
    
    except Exception as e:
        app.logger.error(f"获取城市 {city_name} 年化损失数据时发生错误: {e}")
        return jsonify({'error': '服务器内部错误'}), 500