# CNCityRisk-web

CNCityRisk-web 是一个用于展示城市风险评估结果的 Web 应用程序，使用 Flask 框架构建。

## [网站地址](http://106.15.93.61/)

[![BldLoss](CNCityRiskWeb/static/images/BldLoss.png)](http://106.15.93.61/)

## 说明文档

* [文档](https://youtian95.github.io/2025/01/09/CNCityRiskMap/)

## 使用 DockerHub 部署

除了从源代码构建之外，还可以使用预构建的 Docker 镜像进行快速部署。这种方法特别适合生产环境，能够保证环境一致性并节省构建时间。

### 1. 上传镜像到 DockerHub (开发者操作)

1. 构建并标记镜像:
   ```bash
   # 登录到 DockerHub
   docker login
   
   # 构建镜像并标记
   docker build -t youtian95/cncityrisk:latest .
   
   # 推送到 DockerHub
   docker push youtian95/cncityrisk:latest
   ```

### 2. 从 DockerHub 部署 (服务器操作)

1. 创建工作目录并进入:
   ```bash
   mkdir CNCityRisk-web
   cd CNCityRisk-web
   ```

2. 从GitHub仓库克隆配置文件:
   ```bash
   # 从GitHub下载所需配置文件
   git clone https://github.com/youtian95/CNCityRisk-web.git temp
   
   # 复制所需的配置文件
   cp temp/docker-compose.yml ./
   cp temp/nginx.conf ./
   cp temp/gunicorn.conf.py ./
   
   # 静态文件
   cp -r temp/CNCityRiskWeb/static ./CNCityRiskWeb/
   
   # 清理临时文件
   rm -rf temp
   
   # 创建 config.ini 文件（需要手动配置API密钥）
   cat > config.ini << 'EOF'
   [API]
   api_key_OpenTopography = your_key
   api_key_TDT = your_key
   EOF
   ```
   
   > **注意**: config.ini文件包含API密钥，需要手动创建并填入您自己的密钥。

3. 创建必要的目录结构(如果从GitHub复制的静态文件不包含maps目录):
   ```bash
   mkdir -p CNCityRiskWeb/static/maps
   ```

4. 上传数据文件: 将损失图数据上传到 `CNCityRiskWeb/static/maps` 目录

5. 拉取镜像并启动服务:
   ```bash
   docker-compose up
   ```

6. 访问应用:
   浏览器打开 `http://服务器IP地址` 即可访问应用。

### 3. 更新应用 (使用 DockerHub)

当应用需要更新时:

```bash
# 在开发机器上
docker build -t youtian95/cncityrisk:latest .
docker push youtian95/cncityrisk:latest

# 在服务器上
docker-compose down
docker pull youtian95/cncityrisk:latest
docker-compose up -d
```

## 从源代码使用Docker部署

### 前提条件

- 安装 [Docker](https://www.docker.com/get-started)
- 安装 [Docker Compose](https://docs.docker.com/compose/install/)
- 配置国内Docker镜像源：
  1. 在Linux系统上，创建或编辑Docker配置文件：
      ```bash
      sudo mkdir -p /etc/docker
      sudo vim /etc/docker/daemon.json
      ```
  2. 添加以下内容：
      ```json
      {
        "registry-mirrors": [
          "https://docker.1ms.run",
          "https://docker.xuanyuan.me"
        ]
      }
      ```
  3. 重启Docker服务：
      ```bash
      sudo systemctl daemon-reload
      sudo systemctl restart docker
      ```
  4. 验证配置：
      ```bash
      docker info
      ```
      查看输出中的"Registry Mirrors"部分确认设置已生效。

### 部署步骤

1. 克隆仓库：
    ```bash
    git clone https://github.com/youtian95/CNCityRisk-web.git
    cd CNCityRisk-web
    ```

2. 配置API密钥：
    ```bash
    # 创建或编辑config.ini文件
    vim config.ini
    ```
    添加以下内容：
    ```ini
    [API]
    api_key_OpenTopography = your_key
    api_key_TDT = your_key
    ```

3. 确保损失图结果数据已上传到`CNCityRiskWeb/static/maps`目录，cncityrisk安装包上传到工作目录

4. 构建并启动Docker容器：
    ```bash
    docker-compose up -d --build
    ```

5. 访问应用：
    浏览器打开 `http://localhost` 即可访问应用。

### 技术说明

- 本Docker配置使用Miniconda作为基础镜像
- GDAL库通过conda安装，避免了版本不匹配问题
- 其他Python依赖通过pip安装
- 应用在conda虚拟环境中运行

### 更新应用

当代码有更新时，运行以下命令重新构建并启动容器：

```bash
git pull
docker-compose up -d --build
```

### 查看日志

```bash
docker-compose logs -f
```

### 停止应用

```bash
docker-compose down
```

## 本地开发

启动开发服务器：
  ```bash
  flask run
  ```
