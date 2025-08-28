/**
 * 地图底图样式配置文件
 * 统一管理所有地图界面的底图样式
 */

// 地图样式配置对象
const MapStyles = {
    // 当前使用的样式（可以通过修改这个值来切换底图）
    currentStyle: 'cartodb_light',
      // 底图样式配置
    styles: {
        // Stadia Maps 地形图（推荐）
        stadia_terrain: {
            name: 'Stadia 地形图',
            leaflet: {
                url: 'https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}{r}.png',
                options: {
                    maxZoom: 18,
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://stadiamaps.com/">Stadia Maps</a>'
                }
            },
            openlayers: {
                url: 'https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}.png',
                attribution: '© OpenStreetMap contributors © Stadia Maps'
            }
        },
        
        // CartoDB 简约图
        cartodb_light: {
            name: 'CartoDB 简约图',
            leaflet: {
                url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
                options: {
                    maxZoom: 19,
                    attribution: '© OpenStreetMap contributors © CARTO'
                }
            },
            openlayers: {
                url: 'https://{a-c}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
                attribution: '© OpenStreetMap contributors © CARTO'
            }
        },
        
        // ESRI 世界地形图
        esri_terrain: {
            name: 'ESRI 世界地形图',
            leaflet: {
                url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}',
                options: {
                    maxZoom: 13,
                    attribution: 'Tiles © Esri — Source: USGS, Esri, TANA, DeLorme, and NPS'
                }
            },
            openlayers: {
                url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}',
                attribution: 'Tiles © Esri — Source: USGS, Esri, TANA, DeLorme, and NPS'
            }
        },
        
        // OpenTopoMap 地形图
        opentopomap: {
            name: 'OpenTopo 地形图',
            leaflet: {
                url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
                options: {
                    maxZoom: 17,
                    attribution: '© OpenTopoMap (CC-BY-SA)'
                }
            },
            openlayers: {
                url: 'https://{a-c}.tile.opentopomap.org/{z}/{x}/{y}.png',
                attribution: '© OpenTopoMap (CC-BY-SA)'
            }
        },
        
        // Stadia Maps 简约图
        stadia_light: {
            name: 'Stadia 简约图',
            leaflet: {
                url: 'https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png',
                options: {
                    maxZoom: 20,
                    attribution: '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                }
            },
            openlayers: {
                url: 'https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}.png',
                attribution: '© Stadia Maps © OpenStreetMap contributors'
            }
        },
        
        // OpenStreetMap 标准图
        openstreetmap: {
            name: 'OpenStreetMap 标准图',
            leaflet: {
                url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                options: {
                    maxZoom: 19,
                    attribution: '© OpenStreetMap contributors'
                }
            },
            openlayers: {
                url: 'https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                attribution: '© OpenStreetMap contributors'
            }
        }
    },
    
    /**
     * 获取当前样式的配置
     * @param {string} mapLibrary - 地图库类型 ('leaflet' 或 'openlayers')
     * @returns {object} 样式配置对象
     */
    getCurrentStyle: function(mapLibrary = 'leaflet') {
        const style = this.styles[this.currentStyle];
        if (!style) {
            console.warn(`未找到样式: ${this.currentStyle}，使用默认样式`);
            return this.styles.cartodb_light[mapLibrary];
        }
        return style[mapLibrary];
    },
    
    /**
     * 设置当前样式
     * @param {string} styleName - 样式名称
     */
    setCurrentStyle: function(styleName) {
        if (this.styles[styleName]) {
            this.currentStyle = styleName;
        } else {
            console.warn(`未找到样式: ${styleName}`);
        }
    },
    
    /**
     * 获取所有可用样式的列表
     * @returns {object} 样式名称和显示名称的映射
     */
    getAvailableStyles: function() {
        const styleList = {};
        for (const [key, value] of Object.entries(this.styles)) {
            styleList[key] = value.name;
        }
        return styleList;
    },
    
    /**
     * 为 Leaflet 创建图层
     * @param {string} styleName - 样式名称（可选，默认使用当前样式）
     * @returns {L.TileLayer} Leaflet 图层对象
     */
    createLeafletLayer: function(styleName = null) {
        const style = styleName ? this.styles[styleName]?.leaflet : this.getCurrentStyle('leaflet');
        if (!style) {
            throw new Error(`无法创建图层，样式不存在: ${styleName || this.currentStyle}`);
        }
        return L.tileLayer(style.url, style.options);
    },
      /**
     * 为 OpenLayers 创建图层
     * @param {string} styleName - 样式名称（可选，默认使用当前样式）
     * @returns {ol.layer.Tile} OpenLayers 图层对象
     */
    createOpenLayersLayer: function(styleName = null) {
        const style = styleName ? this.styles[styleName]?.openlayers : this.getCurrentStyle('openlayers');
        if (!style) {
            throw new Error(`无法创建图层，样式不存在: ${styleName || this.currentStyle}`);
        }
        return new ol.layer.Tile({
            source: new ol.source.XYZ({
                url: style.url,
                attributions: style.attribution
            })
        });
    },
    
    /**
     * 创建底图切换控件（用于 Leaflet）
     * @param {L.Map} map - Leaflet 地图对象
     * @returns {L.Control} 底图切换控件
     */
    createLeafletStyleControl: function(map) {
        const StyleControl = L.Control.extend({
            onAdd: function() {
                const div = L.DomUtil.create('div', 'map-style-control');
                div.style.background = 'rgba(255, 255, 255, 0.9)';
                div.style.padding = '5px';
                div.style.borderRadius = '5px';
                div.style.border = '1px solid #ccc';
                
                const select = L.DomUtil.create('select', '', div);
                select.style.border = 'none';
                select.style.background = 'transparent';
                
                // 添加选项
                const styles = MapStyles.getAvailableStyles();
                for (const [key, name] of Object.entries(styles)) {
                    const option = L.DomUtil.create('option', '', select);
                    option.value = key;
                    option.textContent = name;
                    if (key === MapStyles.currentStyle) {
                        option.selected = true;
                    }
                }
                
                // 添加切换事件
                L.DomEvent.on(select, 'change', function() {
                    const newStyle = select.value;
                    MapStyles.setCurrentStyle(newStyle);
                    
                    // 移除现有图层并添加新图层
                    map.eachLayer(function(layer) {
                        if (layer instanceof L.TileLayer) {
                            map.removeLayer(layer);
                        }
                    });
                    
                    const newLayer = MapStyles.createLeafletLayer(newStyle);
                    newLayer.addTo(map);
                });
                
                return div;
            }
        });
        
        return new StyleControl({ position: 'bottomright' });
    },
    
    /**
     * 创建底图切换控件（用于 OpenLayers）
     * @param {ol.Map} map - OpenLayers 地图对象
     * @returns {ol.control.Control} 底图切换控件
     */
    createOpenLayersStyleControl: function(map) {        
        const element = document.createElement('div');
        element.className = 'map-style-control ol-unselectable ol-control';
        element.style.bottom = '5px';
        element.style.right = '30px';
        element.style.background = 'rgba(255, 255, 255, 0.9)';
        element.style.padding = '5px';
        element.style.borderRadius = '5px';
        element.style.border = '1px solid #ccc';
        
        const select = document.createElement('select');
        select.style.border = 'none';
        select.style.background = 'transparent';
        
        // 添加选项
        const styles = MapStyles.getAvailableStyles();
        for (const [key, name] of Object.entries(styles)) {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = name;
            if (key === MapStyles.currentStyle) {
                option.selected = true;
            }
            select.appendChild(option);
        }
        
        // 添加切换事件
        select.addEventListener('change', function() {
            const newStyle = select.value;
            MapStyles.setCurrentStyle(newStyle);
            
            // 移除现有底图层并添加新图层
            const layers = map.getLayers();
            const baseLayers = layers.getArray().filter(layer => 
                layer instanceof ol.layer.Tile && 
                layer.getSource() instanceof ol.source.XYZ
            );
            
            baseLayers.forEach(layer => {
                map.removeLayer(layer);
            });
            
            const newLayer = MapStyles.createOpenLayersLayer(newStyle);
            map.getLayers().insertAt(0, newLayer);
        });
        
        element.appendChild(select);
        
        return new ol.control.Control({
            element: element
        });
    },

    /**
     * 应用 OpenLayers 控件样式修复
     * 这个函数会创建并注入必要的CSS样式来修复OpenLayers控件位置
     */
    applyOpenLayersControlStyles: function() {
        // 检查是否已经添加了样式
        if (document.getElementById('ol-controls-fix')) {
            return;
        }

        const style = document.createElement('style');
        style.id = 'ol-controls-fix';
        style.textContent = `
            /* OpenLayers控件位置修复样式 */
            .ol-attribution {
                bottom: 3.5em !important;
                right: 0.5em !important;
                top: auto !important;
                left: auto !important;
                position: absolute !important;
                background: rgba(255, 255, 255, 0.8) !important;
                border-radius: 3px !important;
            }

            .ol-attribution ul {
                margin: 0 !important;
                padding: 0 !important;
                list-style: none !important;
                font-size: 11px !important;
            }

            .ol-attribution li {
                margin: 0 !important;
                padding: 0 !important;
            }

            /* 保持 attribution 的默认折叠行为 */
            .ol-attribution.ol-collapsed ul {
                display: none !important;
            }

            .ol-attribution:not(.ol-collapsed) ul {
                display: block !important;
                margin-left: 0.5em !important;
            }

            .ol-zoom {
                top: 0.5em !important;
                left: 0.5em !important;
                bottom: auto !important;
                right: auto !important;
                position: absolute !important;
            }

            .ol-control {
                position: absolute !important;
            }

            .ol-control button {
                background: rgba(255, 255, 255, 0.8) !important;
                border: none !important;
                border-radius: 2px !important;
            }

            .ol-full-screen {
                top: 0.5em !important;
                right: 0.5em !important;
                position: absolute !important;
            }

            .ol-rotate {
                top: 4.5em !important;
                left: 0.5em !important;
                position: absolute !important;
            }

            .map-style-control {
                position: absolute !important;
                bottom: 0.5em !important;
                right: 0.5em !important;
                background: rgba(255, 255, 255, 0.9) !important;
                padding: 5px !important;
                border-radius: 5px !important;
                border: 1px solid #ccc !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2) !important;
            }

            .map-style-control select {
                border: none !important;
                background: transparent !important;
                font-size: 12px !important;
                padding: 2px !important;
                outline: none !important;
                cursor: pointer !important;
            }
        `;
        
        document.head.appendChild(style);
    }
};

// 如果在浏览器环境中，将 MapStyles 添加到全局作用域
if (typeof window !== 'undefined') {
    window.MapStyles = MapStyles;
    
    // 页面加载完成后自动应用OpenLayers控件样式
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            MapStyles.applyOpenLayersControlStyles();
        });
    } else {
        // 如果文档已经加载完成，直接应用样式
        MapStyles.applyOpenLayersControlStyles();
    }
}

// 如果在 Node.js 环境中，导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MapStyles;
}
