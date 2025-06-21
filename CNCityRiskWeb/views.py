from flask import render_template, request, url_for, redirect, flash, jsonify, send_file, abort
from pathlib import Path
import sqlite3
import os
from urllib.parse import unquote, quote
import io
import gzip
import json

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
    """# 获取请求参数
    current_city = request.args.get('city')
    eq_i_rup = request.args.get('eq_i_rup', '0')
    LossType = request.args.get('LossType', 'DS_Struct')
    # 验证必需参数
    if not current_city:
        flash('缺少必需的参数', 'error')
        return redirect(url_for('index'))
    
    # 转换震源索引为整数
    try:
        eq_i_rup_int = int(eq_i_rup)
    except ValueError:
        eq_i_rup_int = 0
        eq_i_rup = '0'
    # 检查mbtiles文件是否存在
    mbtiles_path = Path(app.static_folder) / 'maps' / 'mbtiles' / f'RegionalLoss_{current_city}_{LossType}_0_ogr2ogr.mbtiles'
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
        'has_mbtiles': has_mbtiles
    }
    
    # 只使用mbtiles地图模板
    app.logger.info(f'Rendering mbtiles map for {current_city}, rupture {eq_i_rup}')
    return render_template('lossmap_mbtiles.html', **template_context)

# 新增异步获取地图数据的路由
@app.route('/get_map_data')
def get_map_data():
    """
    获取区域损失地图数据，支持mbtiles和HTML地图两种方式
     - 如果使用mbtiles，则返回瓦片URL和边界信息
     - 如果使用HTML地图，则返回HTML内容和CDF图像
    """
    current_city = request.args.get('city')
    current_district = request.args.get('district')
    eq_i_rup = int(request.args.get('eq_i_rup', 0))
    LossType = request.args.get('LossType', 'DS_Struct')
    use_mbtiles = request.args.get('use_mbtiles', 'true').lower() == 'true'
    
    if use_mbtiles:
        # 使用mbtiles矢量瓦片
        # 修改文件路径逻辑：优先查找包含所有rup_index数据的文件
        mbtiles_path = Path(app.static_folder) / 'maps' / 'mbtiles' / f'RegionalLoss_{current_city}_{LossType}_0_ogr2ogr.mbtiles'
        
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
        
        # CDF图文件
        CDF_img_content = models.get_image_CDF_regional_losses(current_city, LossType=LossType, i_rup=eq_i_rup, savedir=Path(app.static_folder) / 'maps')
        
        return jsonify({
            'use_mbtiles': True,
            'tile_url': tile_url,
            'bounds': bounds,
            'CDF_img_content': CDF_img_content,
            'eq_info': eq_info
        })
    else:
        # 使用原有的HTML地图
        html_content = models.get_map_regional_losses(current_city, current_district, i_rup=eq_i_rup, LossType=LossType, savedir=Path(app.static_folder) / 'maps')
        if not html_content:
            return jsonify({'error': '地图文件不存在！'}), 404
        
        eq_info = models.get_EQ_info_from_map(html_content)
        
        # CDF图文件
        CDF_img_content = models.get_image_CDF_regional_losses(current_city, LossType=LossType, i_rup=eq_i_rup, savedir=Path(app.static_folder) / 'maps')
        
        return jsonify({
            'use_mbtiles': False,
            'html_content': html_content,
            'CDF_img_content': CDF_img_content,
            'eq_info': eq_info
        })


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
    """获取所有可用城市的地理坐标数据"""
    coordinates = models.get_city_coordinates()
    # 只返回可用城市的坐标
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
    # 检查IM网格数据文件是否存在
    im_data_path = Path(app.static_folder) / 'maps' / f'IM_median_mapdata_{current_city}.json'
    
    if not im_data_path.exists():
        app.logger.error(f'IM grid data file not found: {im_data_path}')
        flash(f'城市 {current_city} 的IM网格数据不存在', 'error')
        return redirect(url_for('rupture_selection', city=current_city))
    # 从JSON文件获取IM元数据
    try:
        with open(im_data_path, 'r', encoding='utf-8') as f:
            im_data = json.load(f)
        im_metadata = im_data.get('metadata', {})
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
    从 IM_median_mapdata_{city}.json 文件中提取指定破裂面和周期的数据
    """
    current_city = request.args.get('city')
    eq_i_rup = request.args.get('eq_i_rup')
    period_index = request.args.get('period_index')
    
    # 验证必需参数
    if not current_city or eq_i_rup is None or period_index is None:
        return jsonify({'error': '缺少必需的参数: city, eq_i_rup, period_index'}), 400
    
    try:
        eq_i_rup = int(eq_i_rup)
        period_index = int(period_index)
    except ValueError:
        return jsonify({'error': '破裂面索引和周期索引必须是整数'}), 400
    
    # 构建IM网格数据文件路径
    im_data_path = Path(app.static_folder) / 'maps' / f'IM_median_mapdata_{current_city}.json'
    
    if not im_data_path.exists():
        return jsonify({'error': f'城市 {current_city} 的IM网格数据文件不存在'}), 404
    
    try:
        # 读取IM网格数据文件
        with open(im_data_path, 'r', encoding='utf-8') as f:
            im_data = json.load(f)
        
        # 验证破裂面和周期索引的有效性
        metadata = im_data.get('metadata', {})
        total_ruptures = metadata.get('total_ruptures', 0)
        total_periods = metadata.get('total_periods', 0)
        
        if eq_i_rup >= total_ruptures or eq_i_rup < 0:
            return jsonify({'error': f'破裂面索引 {eq_i_rup} 超出范围 [0, {total_ruptures-1}]'}), 400
        
        if period_index >= total_periods or period_index < 0:
            return jsonify({'error': f'周期索引 {period_index} 超出范围 [0, {total_periods-1}]'}), 400
        
        # 提取指定破裂面和周期的网格数据
        grid_data = []
        sites = im_data.get('sites', [])
        
        app.logger.info(f'开始提取IM网格数据: 城市={current_city}, 破裂面={eq_i_rup}, 周期={period_index}, 总站点数={len(sites)}')
        
        for site in sites:
            lon = site.get('lon')
            lat = site.get('lat')
            im_matrix = site.get('im_matrix')
            
            if lon is None or lat is None or im_matrix is None:
                continue
            
            # 检查im_matrix结构并提取IM值
            if (isinstance(im_matrix, list) and 
                eq_i_rup < len(im_matrix) and 
                isinstance(im_matrix[eq_i_rup], list) and 
                period_index < len(im_matrix[eq_i_rup])):
                
                im_value = im_matrix[eq_i_rup][period_index]
                
                # 检查IM值的有效性
                if im_value is not None and not (isinstance(im_value, float) and (im_value != im_value)):  # 检查NaN
                    grid_data.append([lon, lat, im_value])
        
        app.logger.info(f'IM网格数据提取完成: 有效数据点 {len(grid_data)} 个')
        
        # 返回网格数据和元数据
        response_data = {
            'grid_data': grid_data,
            'metadata': {
                'city': current_city,
                'rupture_index': eq_i_rup,
                'period_index': period_index,
                'total_points': len(grid_data),
                'rupture_info': metadata.get('ruptures', {}).get(str(eq_i_rup), {}),
                'period_info': metadata.get('periods', {}).get(str(period_index), {}),
                'bounds': {
                    'min_lon': min(point[0] for point in grid_data) if grid_data else None,
                    'max_lon': max(point[0] for point in grid_data) if grid_data else None,
                    'min_lat': min(point[1] for point in grid_data) if grid_data else None,
                    'max_lat': max(point[1] for point in grid_data) if grid_data else None,
                    'min_value': min(point[2] for point in grid_data) if grid_data else None,
                    'max_value': max(point[2] for point in grid_data) if grid_data else None
                }
            }
        }
        
        return jsonify(response_data)
        
    except json.JSONDecodeError as e:
        app.logger.error(f'解析IM数据文件失败: {e}')
        return jsonify({'error': 'IM数据文件格式错误'}), 500
    except Exception as e:
        app.logger.error(f'获取IM网格数据时发生错误: {e}')
        return jsonify({'error': '服务器内部错误'}), 500