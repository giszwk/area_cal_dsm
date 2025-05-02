import geopandas as gpd
from osgeo import gdal
import rasterio as rio
from rasterio.mask import mask
import numpy as np
import os
import csv

def calculate_building_surface_area(slope_raster_path, buildings_shp_path, output_shp_path):
    """
    计算每个建筑足迹矢量范围内建筑屋顶的表面积。

    参数：
        slope_raster_path (str): 坡度栅格文件路径。
        buildings_shp_path (str): 建筑足迹矢量文件路径。
        output_shp_path (str): 输出包含表面积字段的矢量文件路径。
    """
    # 检查文件是否存在
    if not os.path.isfile(slope_raster_path):
        print(f"DSM file not found: {slope_raster_path}. Skipping...")
        return
    if not os.path.isfile(buildings_shp_path):
        print(f"DSM file not found: {buildings_shp_path}. Skipping...")
        return

    # 读取坡度栅格数据
    with rio.open(slope_raster_path) as slope_ds:
        slope_crs = slope_ds.crs
        
        # 读取建筑足迹矢量数据
        buildings_gdf = gpd.read_file(buildings_shp_path)
        
        # 确保建筑足迹矢量数据与坡度栅格的 CRS 一致
        if buildings_gdf.crs != slope_crs:
            buildings_gdf = buildings_gdf.to_crs(slope_crs)

        # 初始化存储表面积的列表
        surface_areas = []
        planar_areas = []
        area_ratios = []

        for idx, row in buildings_gdf.iterrows():
            # 获取当前建筑足迹的几何对象
            geometry = row.geometry
            
            try:
                # 裁剪坡度栅格
                out_image, out_transform = mask(slope_ds, [geometry.__geo_interface__], crop=True, nodata=-9999)
                
                # 将裁剪结果展平为一维数组
                slope_values = out_image[0].flatten()
                
                # 过滤无效值（如 nodata 或填充值）
                valid_slope_values = slope_values[(slope_values > 0) & (slope_values < 80)]
                
                if len(valid_slope_values) == 0:
                    # print(f"建筑 {idx} 的坡度值无效，跳过")
                    surface_areas.append(None)
                    planar_areas.append(None)
                    area_ratios.append(None)
                    continue
                
                # 计算平均坡度（以弧度为单位）
                mean_slope_rad = np.radians(np.mean(valid_slope_values))
                
                # 计算平面投影面积
                planar_area = geometry.area
                
                # 计算表面积
                sec_slope = 1 / np.cos(mean_slope_rad)
                surface_area = planar_area * sec_slope
                
                # 存储表面积
                surface_areas.append(surface_area)
                planar_areas.append(planar_area)
                area_ratios.append(surface_area / planar_area)
            except Exception as e:
                print(f"处理建筑 {idx} 时出错: {e}")
                surface_areas.append(None)
        
        # 将表面积添加到 GeoDataFrame 中
        buildings_gdf['surface_area'] = surface_areas
        buildings_gdf['planar_area'] = planar_areas
        buildings_gdf['area_ratio'] = area_ratios
        # 导出为新的 Shapefile
        buildings_gdf.to_file(output_shp_path)
        print(f"包含表面积字段的 Shapefile 已保存至: {output_shp_path}")

if __name__ == '__main__':
    csv_file_path = '/data24t/weikezhao/fifth_limian/Dsm_Stats_inBuilding/city_list.csv'

    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)  # 假设 CSV 文件有表头：city_name, lat, lon, building_name
        for row in reader:
            city_name = row['city_name']
            slope_raster_path = f"/data24t/weikezhao/fifth_limian/area_cal_dsm/data/slp_tifs/{city_name}_slp.tif"  # 坡度栅格文件路径
            buildings_shp_path = f"/data24t/weikezhao/fifth_limian/Dsm_Stats_inBuilding/data/3d_globfp/output/{city_name}_stats.shp" # 建筑足迹矢量文件路径
            output_shp_path =  f"/data24t/weikezhao/fifth_limian/area_cal_dsm/data/area_shp/{city_name}_area.shp" # 输出 Shapefile 路径
            
            calculate_building_surface_area(slope_raster_path, buildings_shp_path, output_shp_path)