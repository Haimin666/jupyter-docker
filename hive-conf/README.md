# Hive 配置目录

把 CDH 集群的 `hive-site.xml` 放到本目录（容器内挂载为 `/etc/hive/conf`，PyHive / spark-hive 据此连 Hive Metastore）：

- `hive-site.xml`

从集群节点拷贝：`scp cdh-node:/etc/hive/conf/hive-site.xml ./hive-conf/`

本目录内容已 .gitignore，不会入仓。
