import os
import numpy as np
import csv
from osgeo import gdal
from scipy.ndimage import convolve

def calculate_slope(dem_path, output_path):
    """
    计算 DEM 的坡度并导出为栅格文件。

    参数：
        dem_path (str): 输入 DEM 文件路径。
        output_path (str): 输出坡度栅格文件路径。
    """
    # 打开 DEM 文件并获取地理变换信息
    dem_ds = gdal.Open(dem_path)
    transform = dem_ds.GetGeoTransform()
    cell_x, cell_y = transform[1], abs(transform[5])  # 像素分辨率
    
    # 读取 DEM 数据为 NumPy 数组
    band = dem_ds.GetRasterBand(1)
    dem_array = band.ReadAsArray().astype(float)

    # 获取 nodata 值
    nodata = band.GetNoDataValue()
    if nodata is not None:
        dem_array[dem_array == nodata] = np.nan  # 将 nodata 替换为 NaN

    # 边界处理：使用镜像填充扩展数组
    padded_dem_array = np.pad(dem_array, pad_width=1, mode='edge')

    # 定义卷积核
    kernel_dx = np.array([[1, 0, -1],
                          [2, 0, -2],
                          [1, 0, -1]]) / (8 * cell_x)  # X 方向梯度
    kernel_dy = np.array([[1, 2, 1],
                          [0, 0, 0],
                          [-1, -2, -1]]) / (8 * cell_y)  # Y 方向梯度

    # 计算坡度分量 dz/dx 和 dz/dy
    dz_dx = convolve(padded_dem_array, kernel_dx, mode='constant', cval=0.0)
    dz_dy = convolve(padded_dem_array, kernel_dy, mode='constant', cval=0.0)

    # 计算坡度值（角度）
    slope = np.degrees(np.arctan(np.sqrt(dz_dx**2 + dz_dy**2)))

    # 去掉填充部分，恢复原始大小
    slope = slope[1:-1, 1:-1]

    # 掩膜处理：只有 DSM 中有有效数据的地方才保留坡度值
    slope[np.isnan(dem_array)] = -9999  # 将无数据区域设置为nodata

    # 导出坡度结果为栅格文件
    export_raster(slope, dem_ds, output_path)

def export_raster(array, template_ds, output_path):
    """
    将 NumPy 数组导出为栅格文件。

    参数：
        array (np.ndarray): 要导出的数组。
        template_ds (gdal.Dataset): 模板栅格数据集（用于复制元数据）。
        output_path (str): 输出栅格文件路径。
    """
    # 获取模板栅格的基本信息
    driver = gdal.GetDriverByName("GTiff")  # 使用 GeoTIFF 格式
    rows, cols = array.shape
    bands = 1  # 单波段输出
    dtype = gdal.GDT_Float32  # 数据类型为 32 位浮点数

    # 创建输出栅格文件
    out_ds = driver.Create(output_path, cols, rows, bands, dtype)
    out_ds.SetGeoTransform(template_ds.GetGeoTransform())  # 设置地理变换参数
    out_ds.SetProjection(template_ds.GetProjection())      # 设置投影信息  

    # 写入坡度数组到栅格文件
    out_band = out_ds.GetRasterBand(1)
    out_band.WriteArray(array)
    out_band.SetNoDataValue(-9999)  # 设置无效值
    out_band.FlushCache()           # 确保数据写入磁盘

    # 关闭数据集
    out_ds = None

# 测试代码
if __name__ == '__main__':
    csv_file_path = '/data24t/weikezhao/fifth_limian/Dsm_Stats_inBuilding/city_list.csv'
    root_folder = '/data24t/weikezhao/fifth_limian/mpc_download/data'

    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)  # 假设 CSV 文件有表头：city_name, lat, lon, building_name
        for row in reader:
            city_name = row['city_name']
            dem_path = f"/data24t/weikezhao/fifth_limian/mpc_download/data/{city_name}/{city_name}_dsm_cropped.tif"       # 输入 DEM 文件路径
            output_path = f"/data24t/weikezhao/fifth_limian/area_cal_dsm/data/slp_tifs/{city_name}_slp.tif"  # 输出坡度栅格文件路径
            print(f'-----{city_name}-----')
            if not os.path.isfile(dem_path):
                print(f"DSM file not found: {dem_path}. Skipping...")
                continue
            calculate_slope(dem_path, output_path)