/**
 * 地震城市风险系统 - 共享地图功能
 * 包含震源几何、等值线生成、颜色计算等共用代码
 */

// 共享的全局变量和常量
const MAP_CONFIG = {
    DEFAULT_CENTER: [114.3055, 30.5928], // 默认武汉坐标
    DEFAULT_ZOOM: 10,
    MIN_ZOOM: 6,
    MAX_ZOOM: 18,
    CONTOUR_LEVELS: 20,
    FIXED_MIN_VALUE: 0.0,
    FIXED_MAX_VALUE: 1.0,
    USE_GEOGRAPHIC: false // 是否使用地理坐标系，默认为否
};

/**
 * 设置坐标系模式
 */
function setGeographicMode(useGeographic = true) {
    MAP_CONFIG.USE_GEOGRAPHIC = useGeographic;
}

/**
 * 获取城市坐标和缩放级别
 */
async function getCityCoordinates(cityName) {
    try {
        const response = await fetch(`/get_city_coordinates?city=${encodeURIComponent(cityName)}`);
        const cityData = await response.json();
        
        let centerCoords = MAP_CONFIG.DEFAULT_CENTER;
        let initialZoom = MAP_CONFIG.DEFAULT_ZOOM;
        let bounds = null;
        
        if (cityData.center) {
            // 转换坐标格式：[纬度, 经度] -> [经度, 纬度]
            centerCoords = [cityData.center[1], cityData.center[0]];
        }
        
        if (cityData.bounds) {
            bounds = cityData.bounds;
            // 根据城市边界计算合适的缩放级别
            const latDiff = Math.abs(bounds[2][0] - bounds[0][0]);
            const lonDiff = Math.abs(bounds[2][1] - bounds[0][1]);
            const maxDiff = Math.max(latDiff, lonDiff);
            
            if (maxDiff > 2) initialZoom = 8;
            else if (maxDiff > 1) initialZoom = 9;
            else if (maxDiff > 0.5) initialZoom = 10;
            else initialZoom = 11;
        }
        
        return { center: centerCoords, zoom: initialZoom, bounds: bounds };
    } catch (error) {
        console.error('获取城市坐标失败，使用默认坐标:', error);
        return { center: MAP_CONFIG.DEFAULT_CENTER, zoom: MAP_CONFIG.DEFAULT_ZOOM, bounds: null };
    }
}

/**
 * 获取震源几何数据
 */
async function fetchRuptureGeometry(cityName, ruptureIndex) {
    try {
        const response = await fetch(`/get_city_all_ruptures/${encodeURIComponent(cityName)}`);
        const data = await response.json();
        
        if (data.data && Array.isArray(data.data)) {
            for (const rupture of data.data) {
                if (rupture.parameters.rupture_index === ruptureIndex) {
                    const coordinates = rupture.latlon_polygon.map(point => {
                        if (Array.isArray(point) && point.length >= 2) {
                            return [point[1], point[0]]; // [lon, lat]
                        }
                        return point;
                    });
                    
                    return {
                        type: 'Polygon',
                        coordinates: [coordinates]
                    };
                }
            }
        }
        return null;
    } catch (error) {
        console.error('获取震源几何数据失败:', error);
        return null;
    }
}

/**
 * 转换坐标（根据设置自动选择是否需要投影变换）
 */
function transformCoordinate(lon, lat) {
    if (MAP_CONFIG.USE_GEOGRAPHIC) {
        return [lon, lat];
    } else {
        return ol.proj.fromLonLat([lon, lat]);
    }
}

/**
 * 创建震源轮廓图层
 */
async function createRuptureLayer(map, cityName, ruptureIndex, zIndex = 100) {
    try {
        const ruptureGeometry = await fetchRuptureGeometry(cityName, ruptureIndex);
        const ruptureSource = new ol.source.Vector();
        
        if (ruptureGeometry && ruptureGeometry.coordinates && ruptureGeometry.coordinates.length > 0) {
            const coordinates = ruptureGeometry.coordinates[0];
            const transformedCoords = coordinates.map(coord => transformCoordinate(coord[0], coord[1]));
            
            const ruptureFeature = new ol.Feature({
                geometry: new ol.geom.Polygon([transformedCoords]),
                rupture_index: ruptureIndex,
                type: 'rupture'
            });
            
            ruptureSource.addFeature(ruptureFeature);
        }
        
        const ruptureLayer = new ol.layer.Vector({
            source: ruptureSource,
            style: new ol.style.Style({
                fill: new ol.style.Fill({
                    color: 'rgba(255, 255, 0, 0.1)'
                }),
                stroke: new ol.style.Stroke({
                    color: '#ff0000',
                    width: 2,
                    lineDash: [5, 5]
                })
            }),
            zIndex: zIndex
        });
        
        map.addLayer(ruptureLayer);
        return ruptureLayer;
    } catch (error) {
        console.error('创建震源图层失败:', error);
        return null;
    }
}

/**
 * 获取IM网格数据
 */
async function fetchIMGridData(cityName, ruptureIndex, periodIndex = 0, isim = null) {
    try {
        let url = `/get_im_grid_data?city=${encodeURIComponent(cityName)}&eq_i_rup=${ruptureIndex}&period_index=${periodIndex}`;
        if (isim !== null) {
            url += `&isim=${isim}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.error) {
            console.warn('IM数据获取失败:', data.error);
            return [];
        }
        
        const dataPoints = [];
        if (data.grid_data && Array.isArray(data.grid_data)) {
            data.grid_data.forEach(point => {
                if (Array.isArray(point) && point.length >= 3) {
                    const [lon, lat, imValue] = point;
                    if (lon !== null && lat !== null && imValue !== null && 
                        !isNaN(lon) && !isNaN(lat) && !isNaN(imValue) && imValue > 0) {
                        dataPoints.push([lon, lat, imValue]);
                    }
                }
            });
        }
        
        return removeDuplicatePoints(dataPoints);
    } catch (error) {
        console.error('获取IM网格数据失败:', error);
        return [];
    }
}

/**
 * 去除重复数据点
 */
function removeDuplicatePoints(points) {
    const uniquePoints = [];
    const seen = new Set();
    
    points.forEach(point => {
        const key = `${point[0].toFixed(6)},${point[1].toFixed(6)}`;
        if (!seen.has(key)) {
            seen.add(key);
            uniquePoints.push(point);
        }
    });
    
    return uniquePoints;
}

/**
 * 生成等值线
 */
function generateContours(dataPoints, contourSource) {
    if (!dataPoints || dataPoints.length < 10) {
        return;
    }
    
    const lons = dataPoints.map(d => d[0]);
    const lats = dataPoints.map(d => d[1]);
    const values = dataPoints.map(d => d[2]);
    
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    
    const dataSpread = Math.max(maxLon - minLon, maxLat - minLat);
    const gridSize = Math.min(Math.max(Math.floor(dataSpread * 2000), 100), 300);
    const width = gridSize;
    const height = gridSize;
    
    const gridData = new Array(width * height);
    
    // 插值算法
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const lon = minLon + (maxLon - minLon) * x / (width - 1);
            const lat = minLat + (maxLat - minLat) * y / (height - 1);
            
            let weightSum = 0;
            let valueSum = 0;
            let minDistance = Infinity;
            let nearestValue = minValue;
            
            const avgSpacing = Math.sqrt((maxLon - minLon) * (maxLat - minLat) / dataPoints.length);
            const maxDistance = Math.max(avgSpacing * 2.5, 0.01);
            
            dataPoints.forEach(point => {
                const dLon = (point[0] - lon) * Math.cos((point[1] + lat) * Math.PI / 360);
                const dLat = point[1] - lat;
                const distance = Math.sqrt(dLon * dLon + dLat * dLat);
                
                if (distance < minDistance) {
                    minDistance = distance;
                    nearestValue = point[2];
                }
                
                if (distance < 0.00001) {
                    gridData[y * width + x] = point[2];
                    return;
                } else if (distance < maxDistance) {
                    const normalizedDistance = distance / maxDistance;
                    const gaussianWeight = Math.exp(-4 * normalizedDistance * normalizedDistance);
                    const splineWeight = Math.pow(1 - normalizedDistance, 4);
                    const weight = (gaussianWeight + splineWeight) * 0.5;
                    
                    if (weight > 0.001) {
                        weightSum += weight;
                        valueSum += weight * point[2];
                    }
                }
            });
            
            if (weightSum > 0) {
                gridData[y * width + x] = valueSum / weightSum;
            } else {
                gridData[y * width + x] = nearestValue;
            }
        }
    }
    
    // 生成等值线阈值
    const thresholds = [];
    for (let i = 1; i <= MAP_CONFIG.CONTOUR_LEVELS; i++) {
        const ratio = i / (MAP_CONFIG.CONTOUR_LEVELS + 1);
        let adjustedRatio;
        if (ratio < 0.3) {
            adjustedRatio = Math.sqrt(ratio / 0.3) * 0.15;
        } else if (ratio < 0.7) {
            adjustedRatio = 0.15 + (ratio - 0.3) / 0.4 * 0.45;
        } else {
            adjustedRatio = 0.6 + Math.pow((ratio - 0.7) / 0.3, 0.7) * 0.4;
        }
        const threshold = MAP_CONFIG.FIXED_MIN_VALUE + (MAP_CONFIG.FIXED_MAX_VALUE - MAP_CONFIG.FIXED_MIN_VALUE) * adjustedRatio;
        if (threshold > 0.02) {
            thresholds.push(threshold);
        }
    }
    
    // 使用 d3-contour 生成等值线
    const contours = d3.contours()
        .size([width, height])
        .thresholds(thresholds);
    
    const contourData = contours(gridData);    // 转换等值线为 OpenLayers 要素
    contourData.forEach(contour => {
        const level = contour.value;
        contour.coordinates.forEach(ring => {
            ring.forEach(polygon => {
                const coords = polygon.map(point => {
                    const lon = minLon + (maxLon - minLon) * point[0] / (width - 1);
                    const lat = minLat + (maxLat - minLat) * point[1] / (height - 1);
                    return transformCoordinate(lon, lat);
                });
                
                if (coords.length > 2) {
                    const feature = new ol.Feature({
                        geometry: new ol.geom.Polygon([coords]),
                        level: level,
                        minValue: minValue,
                        maxValue: maxValue
                    });
                    contourSource.addFeature(feature);
                }
            });
        });
    });
}

/**
 * 创建等值线图层
 */
async function createContourLayer(map, cityName, ruptureIndex, periodIndex = 0, isim = null, zIndex = 200) {
    try {
        const contourSource = new ol.source.Vector();
        const dataPoints = await fetchIMGridData(cityName, ruptureIndex, periodIndex, isim);
        
        if (dataPoints && dataPoints.length > 10) {
            generateContours(dataPoints, contourSource);
        }
        
        const contourLayer = new ol.layer.Vector({
            source: contourSource,
            style: function(feature) {
                const level = feature.get('level');
                const minValue = feature.get('minValue') || 0;
                const maxValue = feature.get('maxValue') || 1;
                return new ol.style.Style({
                    fill: new ol.style.Fill({
                        color: getContourColor(level, minValue, maxValue, 0.6)
                    }),
                    stroke: new ol.style.Stroke({
                        color: getContourColor(level, minValue, maxValue, 0.2),
                        width: 0.1
                    })
                });
            },
            zIndex: zIndex
        });
        
        map.addLayer(contourLayer);
        return contourLayer;
    } catch (error) {
        console.error('创建等值线图层失败:', error);
        return null;
    }
}

/**
 * 获取等值线颜色
 */
function getContourColor(level, minValue, maxValue, baseAlpha = 1.0) {
    const normalizedLevel = Math.max(0, Math.min(1, (level - MAP_CONFIG.FIXED_MIN_VALUE) / (MAP_CONFIG.FIXED_MAX_VALUE - MAP_CONFIG.FIXED_MIN_VALUE)));
    const clampedLevel = Math.max(0.001, Math.min(1.0, normalizedLevel));
    
    let adaptiveAlpha;
    if (clampedLevel < 0.05) {
        adaptiveAlpha = 0.02 + clampedLevel * 1.6;
    } else if (clampedLevel < 0.3) {
        adaptiveAlpha = 0.1 + (clampedLevel - 0.05) * 0.6;
    } else if (clampedLevel < 0.7) {
        adaptiveAlpha = 0.25 + (clampedLevel - 0.3) * 0.375;
    } else {
        const highRatio = (clampedLevel - 0.7) / 0.3;
        adaptiveAlpha = 0.4 + Math.log(1 + highRatio * 9) / Math.log(10) * 0.15;
    }
    adaptiveAlpha = adaptiveAlpha * baseAlpha;
    
    if (adaptiveAlpha < 0.015) {
        return 'rgba(0, 0, 0, 0)';
    }
    
    const hue = 0;
    let saturation, value;
    
    if (clampedLevel < 0.2) {
        saturation = clampedLevel * 2.5;
        value = 0.98 - clampedLevel * 0.1;
    } else if (clampedLevel < 0.6) {
        const ratio = (clampedLevel - 0.2) / 0.4;
        saturation = 0.5 + ratio * 0.4;
        value = 0.96 - ratio * 0.25;
    } else {
        const ratio = (clampedLevel - 0.6) / 0.4;
        saturation = 0.9 + ratio * 0.1;
        value = 0.71 - ratio * 0.15;
    }
    
    const rgb = hsvToRgb(hue, saturation, value);
    return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${adaptiveAlpha})`;
}

/**
 * HSV转RGB
 */
function hsvToRgb(h, s, v) {
    h = h / 60;
    const c = v * s;
    const x = c * (1 - Math.abs((h % 2) - 1));
    const m = v - c;
    
    let rgb;
    if (h >= 0 && h < 1) {
        rgb = [c, x, 0];
    } else if (h >= 1 && h < 2) {
        rgb = [x, c, 0];
    } else if (h >= 2 && h < 3) {
        rgb = [0, c, x];
    } else if (h >= 3 && h < 4) {
        rgb = [0, x, c];
    } else if (h >= 4 && h < 5) {
        rgb = [x, 0, c];
    } else {
        rgb = [c, 0, x];
    }
    
    return [
        Math.round((rgb[0] + m) * 255),
        Math.round((rgb[1] + m) * 255),
        Math.round((rgb[2] + m) * 255)
    ];
}

/**
 * 调整地图视图以适应数据范围
 */
function adjustMapViewToData(map, layers, padding = [50, 50, 50, 50], maxZoom = 15) {
    let extent = null;
    
    // 尝试从传入的图层中获取范围
    for (const layer of layers) {
        if (layer && layer.getSource) {
            const layerExtent = layer.getSource().getExtent();
            if (layerExtent && layerExtent.every(coord => isFinite(coord))) {
                if (!extent) {
                    extent = layerExtent;
                } else {
                    extent = ol.extent.extend(extent, layerExtent);
                }
            }
        }
    }
    
    // 如果有有效的范围，调整地图视图
    if (extent) {
        map.getView().fit(extent, {
            padding: padding,
            maxZoom: maxZoom,
            duration: 1000
        });
    }
}

/**
 * 创建通用的弹窗
 */
function createPopup(map, coordinate, content, duration = 3000) {
    // 移除现有弹窗
    const existingPopup = document.getElementById('popup');
    if (existingPopup) {
        existingPopup.remove();
    }
    
    const popupElement = document.createElement('div');
    popupElement.id = 'popup';
    popupElement.innerHTML = content;

    const popup = new ol.Overlay({
        element: popupElement,
        positioning: 'bottom-center',
        stopEvent: false,
        offset: [0, -10]
    });

    map.addOverlay(popup);
    popup.setPosition(coordinate);

    // 自动关闭弹窗
    if (duration > 0) {
        setTimeout(() => {
            map.removeOverlay(popup);
            popupElement.remove();
        }, duration);
    }
    
    return popup;
}
