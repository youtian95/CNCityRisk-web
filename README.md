# CNCityRisk-web

CNCityRisk-web 是一个用于展示城市风险评估结果的 Web 应用程序，使用 Flask 框架构建。

## [网站地址](http://cncityrisk.youtian95.cn/)

[![BldLoss](CNCityRiskWeb/static/images/BldLoss.png)](http://cncityrisk.youtian95.cn/)

## 说明文档

* [文档](https://youtian95.github.io/2025/01/09/CNCityRiskMap/)

---

## 使用 DockerHub 部署

### 从 DockerHub 部署 (服务器操作)

1. 创建工作目录并进入:
   ```bash
   mkdir CNCityRisk-web
   cd CNCityRisk-web
   ```

2. 创建 `docker-compose.yml`（可手动编辑或直接从仓库复制粘贴以下内容）:
   ```bash
   cat > docker-compose.yml <<'EOF'
   services:
     flask:
       image: youtian95/cncityrisk:latest
       restart: always
       networks:
         - app-network
       environment:
         - FLASK_ENV=production
         - FLASK_DEBUG=False
         - PYTHONUNBUFFERED=1

     nginx:
       image: youtian95/cncityrisk-nginx:latest
       restart: always
       ports:
         - "80:80"
       depends_on:
         - flask
       networks:
         - app-network

   networks:
     app-network:
       driver: bridge
   EOF
   ```

4. 拉取镜像并启动服务:
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

5. 访问应用:
   浏览器打开 `http://服务器IP地址` 即可访问应用。

### 更新应用 (使用 DockerHub)

当应用需要更新时:

```bash
# 在服务器上
cd CNCityRisk-web
docker-compose down
docker-compose pull
docker-compose up -d
```

### 停止应用

```bash
docker-compose down
```

---

## 本地开发

### 启动开发服务器

  ```bash
  flask run
  ```

### 本地运行容器

```bash
docker-compose up
```

### 上传镜像到 DockerHub

```bash
# 构建并标记 Flask 应用镜像
docker build -t youtian95/cncityrisk:latest .
docker tag youtian95/cncityrisk:latest youtian95/cncityrisk:0.3.2

# 构建并标记自定义 Nginx 镜像
docker build -f Dockerfile.nginx -t youtian95/cncityrisk-nginx:latest .
docker tag youtian95/cncityrisk-nginx:latest youtian95/cncityrisk-nginx:0.3.2

# 推送到 DockerHub（应用 + Nginx）
docker push youtian95/cncityrisk:latest
docker push youtian95/cncityrisk:0.3.2
docker push youtian95/cncityrisk-nginx:latest
docker push youtian95/cncityrisk-nginx:0.3.2
```


