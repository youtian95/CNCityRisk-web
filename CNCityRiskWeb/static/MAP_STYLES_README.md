# 地图底图样式配置说明

## 概述

`map-styles.js` 文件提供了统一的地图底图样式管理功能，支持 Leaflet 和 OpenLayers 两种地图库。

## 可用底图样式

1. **stadia_terrain** - Stadia 地形图（默认）
   - 清晰的地形展示，适合地震风险可视化
   - 最大缩放级别：18

2. **cartodb_light** - CartoDB 简约图
   - 简约风格，突出数据展示
   - 最大缩放级别：19

3. **esri_terrain** - ESRI 世界地形图
   - 专业地形图，文字较少
   - 最大缩放级别：13

4. **opentopomap** - OpenTopo 地形图
   - 开源地形图，地形细节丰富
   - 最大缩放级别：17

5. **stadia_light** - Stadia 简约图
   - 清新简约，适合数据叠加
   - 最大缩放级别：20

6. **openstreetmap** - OpenStreetMap 标准图
   - 经典地图样式，信息丰富
   - 最大缩放级别：19

## 使用方法

### 1. 在 HTML 中引用

```html
<script src="{{ url_for('static', filename='map-styles.js') }}"></script>
```

### 2. 切换默认底图样式

修改 `map-styles.js` 中的 `currentStyle` 值：

```javascript
currentStyle: 'cartodb_light',  // 改为想要的样式
```

### 3. 在代码中使用

#### Leaflet

```javascript
// 创建当前样式的图层
const tileLayer = MapStyles.createLeafletLayer();
tileLayer.addTo(map);

// 或创建指定样式的图层
const customLayer = MapStyles.createLeafletLayer('esri_terrain');
customLayer.addTo(map);

// 添加底图切换控件
const styleControl = MapStyles.createLeafletStyleControl(map);
styleControl.addTo(map);
```

#### OpenLayers

```javascript
// 创建当前样式的图层
const layer = MapStyles.createOpenLayersLayer();
map.addLayer(layer);

// 或创建指定样式的图层
const customLayer = MapStyles.createOpenLayersLayer('cartodb_light');
map.addLayer(customLayer);

// 添加底图切换控件
const styleControl = MapStyles.createOpenLayersStyleControl(map);
map.addControl(styleControl);
```

## 底图切换控件

系统已为所有地图页面添加了底图切换控件：
- **位置**：地图右上角
- **功能**：下拉菜单选择不同底图样式
- **实时切换**：选择后立即生效

## 已集成的页面

- `city_selection_map.html` - 城市选择地图（Leaflet）
- `rupture_selection.html` - 震源选择地图（Leaflet） 
- `lossmap_mbtiles.html` - 损失地图（OpenLayers）

## 扩展说明

如需添加新的底图样式：

1. 在 `styles` 对象中添加新配置
2. 提供 `leaflet` 和 `openlayers` 两种格式的配置
3. 指定正确的 URL 模板和属性信息

示例：
```javascript
new_style: {
    name: '新底图样式',
    leaflet: {
        url: 'https://example.com/{z}/{x}/{y}.png',
        options: {
            maxZoom: 18,
            attribution: '© 数据提供方'
        }
    },
    openlayers: {
        url: 'https://example.com/{z}/{x}/{y}.png',
        attribution: '© 数据提供方'
    }
}
```
