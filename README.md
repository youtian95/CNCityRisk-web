# CNCityRisk-web

CNCityRisk-web 是一个用于展示城市风险评估结果的 Web 应用程序，使用 Flask 框架构建。

## [网站地址](http://106.15.93.61/)

[![BldLoss](CNCityRiskWeb/static/images/BldLoss.png)](http://106.15.93.61/)

## 说明文档

* [文档](https://youtian95.github.io/2025/01/09/CNCityRiskMap/)

## 使用Docker部署

### 前提条件

- 安装 [Docker](https://www.docker.com/get-started)
- 安装 [Docker Compose](https://docs.docker.com/compose/install/)

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

3. 确保损失图结果数据文件已上传到`CNCityRiskWeb/static/maps`目录。

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
    ```powershell
    flask run
    ```
