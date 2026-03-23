import os
from pathlib import Path
import logging

def check_data_integrity(app):
    """
    检查静态地图数据的完整性，并将结果记录到 app.logger
    """
    base_dir = Path(app.root_path)
    static_maps_dir = base_dir / 'static' / 'maps'
    
    if not static_maps_dir.exists():
        app.logger.error(f"Data Check: Static maps directory not found at {static_maps_dir}")
        return

    stats_dir = static_maps_dir / 'RegionalLossStatistics'
    rupture_dir = static_maps_dir / 'Ruptures'
    if not stats_dir.exists():
        app.logger.error(f"Data Check: RegionalLossStatistics directory not found at {stats_dir}")
        return
    if not rupture_dir.exists():
        app.logger.error(f"Data Check: Ruptures directory not found at {rupture_dir}")
        return

    # 获取城市列表
    cities = [d.name for d in stats_dir.iterdir() if d.is_dir()]
    app.logger.info(f"Data Check: Found cities: {cities}")

    missing_files = []
    checked_count = 0

    for city in cities:
        # 1. Check MBTiles
        # Pattern: RegionalLoss_{City}_DS_Struct_0_ogr2ogr.mbtiles
        mbtiles_path = static_maps_dir / 'mbtiles' / f'RegionalLoss_{city}_DS_Struct_0_ogr2ogr.mbtiles'
        if not mbtiles_path.exists():
            missing_files.append(str(mbtiles_path))
        checked_count += 1

        # 2. Check IMmap
        # Pattern: IM_mapdata_{City}.hdf5
        immap_path = static_maps_dir / 'IMmap' / f'IM_mapdata_{city}.hdf5'
        if not immap_path.exists():
            missing_files.append(str(immap_path))
        checked_count += 1

        # 3. Check RegionalLossStatistics JSONs
        json_files = [
            'RegionalLossStatistics_DS_Struct.json',
            'RegionalLossStatistics_RepairCost_Total.json',
            'RegionalLossStatistics_RepairTime.json'
        ]
        
        for json_file in json_files:
            json_path = stats_dir / city / json_file
            if not json_path.exists():
                missing_files.append(str(json_path))
            checked_count += 1

        # 4. Check rupture static data
        rupture_path = rupture_dir / f'{city}.csv'
        if not rupture_path.exists():
            missing_files.append(str(rupture_path))
        checked_count += 1

    if missing_files:
        app.logger.warning(f"Data Check: Found {len(missing_files)} missing data files!")
        for f in missing_files:
            app.logger.warning(f"  [MISSING] {f}")
    else:
        app.logger.info(f"Data Check: Integrity check passed. {checked_count} files verified.")
