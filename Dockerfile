FROM continuumio/miniconda3:latest

# 设置工作目录
WORKDIR /app

# 创建conda环境并安装特定版本的GDAL依赖
RUN conda create -n cncityriskweb python=3.12 -y

# 复制依赖文件
COPY requirements.txt .
COPY cncityrisk-0.2.0-py3-none-any.whl .
RUN grep -v "GDAL" requirements.txt > requirements_no_gdal.txt

# 安装Python依赖
RUN conda run -n cncityriskweb pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN conda install -n cncityriskweb -c conda-forge gdal=3.11.0 python=3.12 -y \
    && conda run -n cncityriskweb pip install cncityrisk-0.2.0-py3-none-any.whl \
    && conda run -n cncityriskweb pip install -r requirements_no_gdal.txt \
    && conda run -n cncityriskweb pip install gunicorn

# 复制应用程序代码
COPY . .

# 暴露端口
EXPOSE 8000

# 运行应用程序
CMD ["conda", "run", "-n", "cncityriskweb", "gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
