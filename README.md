# CNCityRisk-web

CNCityRisk-web 是一个用于展示城市风险评估结果的 Web 应用程序，使用 Flask 框架构建。

## 部署到服务器

###  配置环境

1. 克隆仓库：
    ```bash
    git clone https://github.com/youtian95/CNCityRisk-web.git
    ```
1. 使用conda创建虚拟环境并激活：
    ```bash
    source ~/.bashrc
    cd CNCityRisk-web
    conda create -p ./env python=3.11
    conda activate ./env
    ```
1. 将安装包`cncityrisk-0.1.0-py3-none-any.whl`上传到当前目录。
1. 安装依赖（GDAL用`pip install`会报错，所以先安装好）：
    ```bash
    conda install -c conda-forge GDAL=3.7.3
    pip install cncityrisk-0.1.0-py3-none-any.whl
    pip install -r requirements.txt
    ```
1. 将`maps.7z`损失图结果数据文件上传到`~/CNCityRisk-web/CNCityRiskWeb/static/maps`目录下。
1. 修改`~/CNCityRisk-web/.flaskenv`：
    ```bash
    vim ./.flaskenv
    ```
    修改为：
    ```
    FLASK_ENV=production
    FLASK_DEBUG=FALSE
    ...
    ```

### 使用 Gunicorn 运行应用

Gunicorn 是一个 WSGI 服务器，用于运行 Flask 应用，并将其作为后台服务。

1. 安装 Gunicorn
    ```
    pip install gunicorn
    ```
2. 运行 Flask 应用：
    ```bash
    gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
    ```

### 配置 Nginx 作为反向代理

将所有来自外部的请求转发到 Gunicorn 来处理。

1. 安装 Nginx：
    ```bash
    sudo apt-get install nginx
    ```

2. 创建 Nginx 配置文件：
    ```bash
    sudo vim /etc/nginx/sites-available/cncityrisk-web
    ```

    添加以下内容：
    ```nginx
    server {
        listen 80;
        server_name your_domain_or_IP; # 替换为你的域名或服务器的IP

        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    ```
1. 使用符号链接将配置文件链接到 sites-enabled：
    ```bash
    sudo ln -s /etc/nginx/sites-available/cncityrisk-web /etc/nginx/sites-enabled
    ```
1. 启用配置并重启 Nginx：
    ```bash
    sudo systemctl restart nginx
    ```

### 完成

在浏览器中打开 `http://your_domain_or_IP` 查看应用程序。

## 更新服务器上的代码

1. 拉取最新代码：
    ```bash
    cd ~/CNCityRisk-web
    git pull
    ```

2. 更新依赖：
    ```bash
    pip install -r requirements.txt
    ```

3. 重启 Gunicorn 服务：
    ```bash
    sudo systemctl restart gunicorn
    ```

4. 重启 Nginx 服务：
    ```bash
    sudo systemctl restart nginx
    ```
