FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装Python依赖
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
RUN pip install --no-cache-dir cnmaps==1.0.1 cartopy folium addressparser flask flask_compress gunicorn ijson h5py python-dotenv

# 复制应用程序代码
COPY . .

# 暴露端口
EXPOSE 8000

# 运行应用程序
CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
