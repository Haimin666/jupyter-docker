# Hadoop 配置目录

把 CDH 集群的以下 XML 放到本目录（容器内挂载为 `/etc/hadoop/conf`，YARN 提交时 spark 据此连集群）：

- `core-site.xml`
- `hdfs-site.xml`
- `yarn-site.xml`
- `mapred-site.xml`（可选）

从集群节点拷贝：`scp cdh-node:/etc/hadoop/conf/*.xml ./hadoop-conf/`

本目录内容已 .gitignore，不会入仓。
