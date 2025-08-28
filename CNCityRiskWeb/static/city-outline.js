/**
 * 城市轮廓功能模块
 * 提供城市边界多边形的加载、显示和交互功能
 */

class CityOutline {
    constructor(map, options = {}) {
        this.map = map;
        this.options = {
            // 默认样式配置
            defaultStyle: {
                fillColor: 'rgba(33, 149, 243, 0.2)',
                strokeColor: '#2196F3',
                strokeWidth: 2
            },
            hoveredStyle: {
                fillColor: 'rgba(129, 199, 132, 0.3)',
                strokeColor: '#81C784',
                strokeWidth: 2
            },
            selectedStyle: {
                fillColor: 'rgba(46, 125, 50, 0.4)',
                strokeColor: '#2E7D32',
                strokeWidth: 3
            },
            // 是否可点击选择
            clickable: true,
            // 是否显示悬停效果
            hoverable: true,
            // 是否只显示指定城市
            filterCity: null,
            // 是否使用地理坐标系（默认false，使用Web Mercator）
            useGeographic: false,
            // 图层层级
            zIndex: 50,
            // 回调函数
            onCityClick: null,
            onCityHover: null,
            ...options
        };
        
        // 检测当前地图是否使用地理坐标系（如果没有明确指定的话）
        if (this.options.useGeographic === undefined) {
            const projection = this.map.getView().getProjection();
            console.log('地图投影系统:', projection ? projection.getCode() : 'unknown');
            
            // 先尝试直接检测 EPSG:4326
            if (projection && (projection.getCode() === 'EPSG:4326' || projection.getCode().includes('4326'))) {
                this.options.useGeographic = true;
                console.log('检测到地理坐标系，启用地理模式');
            } else {
                // 使用更可靠的方法：测试坐标转换行为
                try {
                    // 测试一个已知的地理坐标点
                    const testLonLat = [116.4, 39.9]; // 北京坐标 [经度, 纬度]
                    const projected = ol.proj.fromLonLat(testLonLat);
                    
                    // 如果投影后的坐标与原坐标相近，说明使用的是地理坐标系
                    const isGeographic = Math.abs(projected[0] - testLonLat[0]) < 0.01 && 
                                       Math.abs(projected[1] - testLonLat[1]) < 0.01;
                    
                    if (isGeographic) {
                        this.options.useGeographic = true;
                        console.log('通过坐标测试检测到地理坐标系，启用地理模式');
                    } else {
                        this.options.useGeographic = false;
                        console.log('使用Web Mercator投影模式，投影后坐标:', projected);
                    }
                } catch (e) {
                    this.options.useGeographic = false;
                    console.log('使用Web Mercator投影模式（测试失败）:', e.message);
                }
            }
        } else {
            console.log('使用强制指定的坐标模式:', this.options.useGeographic ? '地理坐标系' : 'Web Mercator');
        }
        
        // 内部状态
        this.cityCoordinates = {};
        this.cityPolygons = {};
        this.selectedCity = null;
        this.hoveredFeature = null;
        
        // 创建矢量图层
        this.vectorSource = new ol.source.Vector();
        this.vectorLayer = new ol.layer.Vector({
            source: this.vectorSource,
            zIndex: this.options.zIndex // 使用配置的zIndex
        });
        
        // 添加到地图
        this.map.addLayer(this.vectorLayer);
        
        // 初始化事件监听
        this.initEventHandlers();
    }
    
    /**
     * 初始化事件处理
     */
    initEventHandlers() {
        if (this.options.clickable) {
            this.map.on('singleclick', (evt) => {
                const feature = this.map.forEachFeatureAtPixel(evt.pixel, (feature) => {
                    // 只处理城市轮廓图层的要素
                    if (this.vectorSource.getFeatures().includes(feature)) {
                        return feature;
                    }
                    return null;
                });
                
                if (feature) {
                    const cityName = feature.get('cityName');
                    const provinceName = feature.get('provinceName');
                    this.selectCity(cityName, provinceName);
                    
                    if (this.options.onCityClick) {
                        this.options.onCityClick(cityName, provinceName, feature);
                    }
                } else {
                    this.clearSelection();
                }
            });
        }
        
        if (this.options.hoverable) {
            this.map.on('pointermove', (evt) => {
                const feature = this.map.forEachFeatureAtPixel(evt.pixel, (feature) => {
                    // 只处理城市轮廓图层的要素
                    if (this.vectorSource.getFeatures().includes(feature)) {
                        return feature;
                    }
                    return null;
                });
                
                this.handleHover(feature);
            });
        }
    }
    
    /**
     * 处理鼠标悬停
     */
    handleHover(feature) {
        // 重置之前悬停的要素
        if (this.hoveredFeature && this.hoveredFeature !== feature) {
            const cityName = this.hoveredFeature.get('cityName');
            const isSelected = (this.selectedCity === cityName);
            this.hoveredFeature.setStyle(this.createCityStyle(isSelected, false));
        }
        
        // 设置新的悬停要素
        this.hoveredFeature = feature;
        if (feature) {
            const cityName = feature.get('cityName');
            const provinceName = feature.get('provinceName');
            const isSelected = (this.selectedCity === cityName);
            
            if (!isSelected) {
                feature.setStyle(this.createCityStyle(false, true));
            }
            
            if (this.options.onCityHover) {
                this.options.onCityHover(cityName, provinceName, feature);
            }
        }
    }
    
    /**
     * 创建城市样式
     */
    createCityStyle(isSelected, isHovered = false) {
        let styleConfig;
        
        if (isSelected) {
            styleConfig = this.options.selectedStyle;
        } else if (isHovered) {
            styleConfig = this.options.hoveredStyle;
        } else {
            styleConfig = this.options.defaultStyle;
        }
        
        return new ol.style.Style({
            fill: new ol.style.Fill({
                color: styleConfig.fillColor
            }),
            stroke: new ol.style.Stroke({
                color: styleConfig.strokeColor,
                width: styleConfig.strokeWidth
            })
        });
    }
    
    /**
     * 加载城市坐标数据
     */
    async loadCityData() {
        try {
            console.log('开始加载城市坐标数据...');
            const response = await fetch('/get_city_coordinates');
            const data = await response.json();
            console.log('城市坐标数据加载成功:', data);
            
            this.cityCoordinates = data;
            this.addCityPolygons();
            
            return data;
        } catch (error) {
            console.error('Error loading city coordinates:', error);
            throw error;
        }
    }
    
    /**
     * 添加城市多边形
     */
    addCityPolygons() {
        console.log('开始添加城市多边形，城市数量:', Object.keys(this.cityCoordinates).length);
        
        // 清除现有的城市多边形
        this.vectorSource.clear();
        this.cityPolygons = {};
        
        // 为每个有坐标数据的城市创建多边形
        Object.keys(this.cityCoordinates).forEach(city => {
            // 如果指定了筛选城市，只显示该城市
            if (this.options.filterCity && city !== this.options.filterCity) {
                return;
            }
            
            const cityData = this.cityCoordinates[city];
            let polygonCoordsArray = cityData.coordinates; // 现在是多边形数组
            
            console.log(`处理城市 ${city}:`, polygonCoordsArray);
            
            // 为每个城市的所有多边形创建要素
            const cityFeatures = [];
            polygonCoordsArray.forEach((polygonCoords, index) => {
                let coordinates;
                
                if (this.options.useGeographic) {
                    // 地理坐标系模式：坐标格式是[lat, lng]，需要转换为[lng, lat]
                    coordinates = [polygonCoords.map(coord => [coord[1], coord[0]])];
                } else {
                    // Web Mercator模式：坐标格式是[lat, lng]，需要转换为[lng, lat]再投影
                    coordinates = [polygonCoords.map(coord => ol.proj.fromLonLat([coord[1], coord[0]]))];
                }
                
                // 创建多边形几何
                const polygon = new ol.geom.Polygon(coordinates);
                
                // 创建要素
                const feature = new ol.Feature({
                    geometry: polygon,
                    cityName: city,
                    provinceName: cityData.province,
                    polygonIndex: index // 添加索引以区分同一城市的不同多边形
                });
                
                // 设置默认样式
                feature.setStyle(this.createCityStyle(false));
                
                // 添加到矢量源
                this.vectorSource.addFeature(feature);
                
                cityFeatures.push(feature);
            });
            
            // 存储要素引用（现在是数组）
            this.cityPolygons[city] = cityFeatures;
            
            console.log(`城市 ${city} 多边形添加成功，数量: ${cityFeatures.length}`);
        });
        
        console.log('所有城市多边形添加完成');
        
        // 检查图层状态
        if (this.vectorSource.getFeatures().length === 0) {
            console.warn('警告：没有成功添加任何城市轮廓要素！');
        } else {
            console.log(`成功添加 ${this.vectorSource.getFeatures().length} 个城市轮廓要素`);
        }
    }
    
    /**
     * 选择城市
     */
    selectCity(cityName, provinceName = null) {
        // 重置之前选择的城市样式
        if (this.selectedCity && this.cityPolygons[this.selectedCity]) {
            this.cityPolygons[this.selectedCity].forEach(feature => {
                feature.setStyle(this.createCityStyle(false));
            });
        }
        
        // 设置新选择的城市样式
        this.selectedCity = cityName;
        
        if (this.cityPolygons[cityName]) {
            this.cityPolygons[cityName].forEach(feature => {
                feature.setStyle(this.createCityStyle(true));
            });
        }
        
        return {
            cityName,
            provinceName: provinceName || (this.cityCoordinates[cityName] ? this.cityCoordinates[cityName].province : null),
            districtCount: this.cityCoordinates[cityName] ? this.cityCoordinates[cityName].district_count : 0
        };
    }
    
    /**
     * 清除选择
     */
    clearSelection() {
        // 重置之前选择的城市样式
        if (this.selectedCity && this.cityPolygons[this.selectedCity]) {
            this.cityPolygons[this.selectedCity].forEach(feature => {
                feature.setStyle(this.createCityStyle(false));
            });
        }
        
        // 清除选择状态
        this.selectedCity = null;
    }
    
    /**
     * 获取选中的城市信息
     */
    getSelectedCity() {
        if (!this.selectedCity) {
            return null;
        }
        
        return {
            cityName: this.selectedCity,
            provinceName: this.cityCoordinates[this.selectedCity] ? this.cityCoordinates[this.selectedCity].province : null,
            districtCount: this.cityCoordinates[this.selectedCity] ? this.cityCoordinates[this.selectedCity].district_count : 0
        };
    }
    
    /**
     * 缩放到指定城市
     */
    zoomToCity(cityName) {
        if (!this.cityPolygons[cityName]) {
            console.warn(`城市 ${cityName} 不存在`);
            return;
        }
        
        // 计算所有多边形的边界
        let extent = ol.extent.createEmpty();
        this.cityPolygons[cityName].forEach(feature => {
            ol.extent.extend(extent, feature.getGeometry().getExtent());
        });
        
        // 缩放到边界
        this.map.getView().fit(extent, {
            padding: [50, 50, 50, 50],
            duration: 1000
        });
    }
    
    /**
     * 显示/隐藏城市轮廓图层
     */
    setVisible(visible) {
        this.vectorLayer.setVisible(visible);
    }
    
    /**
     * 销毁实例
     */
    destroy() {
        this.map.removeLayer(this.vectorLayer);
        this.vectorSource.clear();
        this.cityPolygons = {};
        this.cityCoordinates = {};
    }
}

// 导出到全局作用域，以便在模板中使用
window.CityOutline = CityOutline;
