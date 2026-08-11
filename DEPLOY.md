# 数据平台 Jupyter 服务 —— 部署与运维手册（bigdata-portal 接入版）

面向 **≤5 人内部团队**、以本地数据分析为主、Spark 偶尔提交，接入 **bigdata-portal** 门户的场景。

## 架构

```
浏览器
  │  HTTPS（门户网关终结）
  ▼
bigdata-portal 容器 :9910
  │  网关内置 /apps/jupyter 反代（HTTP + WebSocket + cookie 重写）
  │  JUPYTER_URL = http://host.docker.internal:8888
  ▼
jupyter 容器 :8888  （bridge 网络，base_url=/apps/jupyter）
  ├─ /home/jovyan/work/<user>/  每用户目录
  ├─ /home/jovyan/work/shared/  团队共享
  └─ /data                      共享只读数据集
```

要点：

- **不另起 nginx**：门户的 Express 网关（`bigdata-portal/server/index.js`）已内置 `/apps/jupyter` 的 HTTP/WebSocket 代理与会话 cookie 重写，同源 iframe 免重复登录。Jupyter 项目只需把 8888 发布到宿主机供门户访问。
- **门户零改动**：门户 compose 已配置 `JUPYTER_URL`（默认 `http://host.docker.internal:8888`），Jupyter 发布 8888 即被门户菜单"Jupyter开发"直接接入。
- **认证**：Jupyter 自身认证（`JUPYTER_TOKEN`）。用户在门户 iframe 首次打开时输一次 token，cookie 经门户 `onProxyRes` 重写种到门户域，之后免登录。
- **Spark client 模式**：固定端口段 `12000-12010` 映射供 executor 回连。

## 目录结构

```
.
├── docker-compose.yml          # 服务编排（仅 jupyter 容器）
├── .env                        # JUPYTER_TOKEN（不入仓）
├── notebooks/                  # 每用户子目录 + shared/
├── data/                       # 共享只读数据集（可选，挂载 /data:ro）
├── hadoop-conf/  hive-conf/    # 集群配置（只读挂载）
├── lib/                        # 连接器 jar（只读挂载）
└── deploy/
    └── scripts/backup.sh       # 备份脚本
```

## 快速开始

前置：宿主机已装 docker + docker compose v2（`docker compose version`），bigdata-portal 已部署。

1. **准备 .env**（`cp .env.example .env` 后修改）：

   ```bash
   JUPYTER_TOKEN=$(openssl rand -hex 32)   # 强随机，勿用示例值
   ```

2. **（可选）建数据目录**：`mkdir data`，放入离线数据集（容器内 `/data` 只读）。

3. **启动**：

   ```bash
   docker compose up -d --build
   docker compose ps          # jupyter 容器 healthy 后可用
   ```

4. **接入验证**：浏览器打开门户 → 菜单"Jupyter开发"（`/apps/jupyter/lab`），首次输 token 登录，之后免登录。

> 若门户与 Jupyter 不在同一台宿主机：把门户 `.env` 的 `JUPYTER_URL` 改为 `http://<该机器IP>:8888`，并在该机器防火墙放行 8888 来源。

## 认证与用户说明

- Jupyter 是**共享单容器 + 单 token**：所有用户首次打开时输同一个 token（5 人内部场景可接受）。
- 每位用户在 `notebooks/` 下用自己名字建子目录（如 `notebooks/zhangsan/`），共享放 `notebooks/shared/`。
- **诚实说明**：目录隔离是"防误操作"级别，不是安全边界（共享同一 OS 用户与 token）。需每用户独立登录/隔离时，升级为 JupyterHub 或每用户独立容器方案（另行评估）。
- token 轮换：改 `.env` 后 `docker compose up -d`（已登录用户 cookie 失效，需重新输一次）。

## 防火墙（宿主机）

| 端口 | 用途 | 建议 |
|---|---|---|
| 8888 | Jupyter（门户经此访问） | 仅放行门户机器/内网来源；不要暴露公网 |
| 12000-12010 | Spark client executor 回连 | 放行 YARN 集群节点来源（或按需收紧） |
| 9910 | 门户网关 | 门户侧管理，与本服务无关 |

## 目录与数据规划

- 离线数据放 `./data/` 只读共享；GB 级文件用 sftp/内网传输，勿用 Jupyter 上传页。
- 大文件分析建议：数据放 `./data` 或 HDFS，脚本放用户目录，中间结果写 `notebooks/<user>/`。

## Spark / YARN 提交（偶尔使用）

- executor 回连 driver 依赖宿主机放行 `12000-12010/tcp`，且 notebook 中 `spark.driver.host` 需指向**宿主机 IP**（client 模式固定端口段映射）。
- 同一时段仅一人提交，避免固定端口冲突；多人同时用 Spark 时把端口段拆开或改用 cluster 模式。
- **权限收口（强烈建议，集群侧配合）**：YARN 提交账号从 `hdfs` 超级用户改为受限账号 + 指定队列 + HDFS 只读，否则任何能登录 Jupyter 的人都拥有集群超级用户权限。
- 若完全不需要 Spark，可删除 compose 中 `12000-12010` 端口映射并去掉相关集群配置挂载。

## 备份与恢复

```bash
./deploy/scripts/backup.sh                 # 备份到 ./backups（保留最近 14 份）
# crontab 建议：0 2 * * * .../deploy/scripts/backup.sh >> /var/log/jupyter-backup.log 2>&1
```

备份内容：`notebooks/` 全部、compose/.env（含 token，备份文件需异地加密存放）。

恢复：解包到原路径后 `docker compose up -d` 即可；容器重建不丢数据（卷挂载）。

## 安全清单

- [ ] `.env` 的 `JUPYTER_TOKEN` 为强随机值（`openssl rand -hex 32`），未用示例值
- [ ] 宿主机防火墙仅放行 8888（门户/内网来源）与 12000-12010，未暴露公网
- [ ] 资源限制生效（`docker inspect jupyter` 可见 Memory/Cpus/Pids 限制）
- [ ] YARN 提交账号已收敛（非 hdfs 超级用户），或已禁用 Spark 提交
- [ ] 定期备份并有恢复演练

## 已知限制

- 单容器共享 OS 用户与单 token，目录隔离为防误操作级（见上）。
- Spark client 模式同一时段仅建议一人提交。
- 服务为单机部署，宿主机故障即整体不可用（5 人团队可接受；如需 HA 再评估）。
