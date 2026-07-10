# 连接器 jar 目录

把需要的连接器 jar 放到本目录（容器内挂载为 `/opt/lib`，只读），供 Spark / Flink 提交时引用，例如：

- Paimon：`paimon-spark-3.4-*.jar`、`paimon-flink-1.17-*.jar`
- MySQL：`mysql-connector-java-8.0.*.jar`
- 其它 Hive / Hudi / Iceberg 等连接器 jar

## 在 notebook 里使用

Spark 提交时指向本目录的 jar：

```python
from pyspark.sql import SparkSession

spark = (SparkSession.builder
    .config("spark.jars", "/opt/lib/paimon-spark-3.4-0.8.2.jar,/opt/lib/mysql-connector-j-8.0.33.jar")
    .getOrCreate())
```

Flink 提交（pyflink）通过 `flink run -C /opt/lib/paimon-flink-1.17-*.jar` 传连接器 jar。

> jar 文件名随版本变化，上面的示例文件名请替换成你实际下载的版本。

## 获取 jar

从 Maven 中央仓库下载（国内可用阿里云镜像）：

```bash
# Paimon for Spark 3.4
curl -L -o lib/paimon-spark-3.4-0.8.2.jar \
  https://repo1.maven.org/maven2/org/apache/paimon/paimon-spark-3.4/0.8.2/paimon-spark-3.4-0.8.2.jar
# MySQL Connector/J
curl -L -o lib/mysql-connector-j-8.0.33.jar \
  https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/8.0.33/mysql-connector-j-8.0.33.jar
```

本目录的 jar 已 .gitignore，不会入仓（jar 为环境特定的二进制，不入仓）。
