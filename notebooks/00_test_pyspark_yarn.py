# %% [markdown]
# # PySpark ↔ YARN 集群连通性测试（client 模式，静默 WARN）
#
# 前提：docker 宿主机 IP 从集群可达（已验证 10.25.100.126:12000 通），集群 DNS 解析不到宿主机主机名，
# 所以用 spark.driver.host=IP 绕开。日志压到 ERROR，屏蔽 topology.py / jars 上传 / Another SparkContext 等 WARN。

# %% [markdown]
# ## 0. 前置自检

# %%
import os, glob, shutil

print("JAVA_HOME =", os.environ.get("JAVA_HOME"))
print("HADOOP_CONF_DIR =", os.environ.get("HADOOP_CONF_DIR"))
confs = glob.glob("/etc/hadoop/conf/*.xml")
assert confs, "❌ /etc/hadoop/conf 下没有 *.xml，先放集群配置"
assert shutil.which("spark-submit"), "❌ 找不到 spark-submit"
print("✅ 环境自检通过")

# %% [markdown]
# ## 1. 构造 SparkSession（YARN client 模式 + 静默日志）

# %%
import os
from pyspark.sql import SparkSession

# >>> 按你的环境改这三项 <<<
HDFS_USER = "hdfs"               # 集群上有权限的 HDFS 用户
DRIVER_HOST = "10.25.100.126"    # docker 宿主机 IP（集群可达；主机名解析不到所以用 IP）
DRIVER_PORT = "12000"            # 已验证从集群可达的端口

# simple 认证下切换 HDFS/YARN 身份（容器 jovyan 用户集群无权限）
os.environ["HADOOP_USER_NAME"] = HDFS_USER

# 写 log4j 配置，根级别压到 ERROR，构造期 WARN（含 topology.py、jars 上传、Another SparkContext）一并屏蔽
log4j_conf = """
log4j.rootLogger=ERROR, console
log4j.appender.console=org.apache.log4j.ConsoleAppender
log4j.appender.console.target=System.err
log4j.appender.console.layout=org.apache.log4j.PatternLayout
log4j.appender.console.layout.ConversionPattern=%d{yy/MM/dd HH:mm:ss} %-5p %c{1}: %m%n
log4j.logger.org.apache.hadoop.net.ScriptBasedMapping=ERROR
log4j.logger.org.apache.spark.SparkContext=ERROR
log4j.logger.org.apache.spark.deploy.yarn.Client=ERROR
"""
log4j_path = "/tmp/log4j.properties"
with open(log4j_path, "w") as f:
    f.write(log4j_conf)

spark = (
    SparkSession.builder
    .appName("jupyter-yarn-test")
    .master("yarn")
    .config("spark.submit.deployMode", "client")
    # 集群无 python3，ship 一个 py38 环境给 executor（与生产 spark-submit --archives 一致）。
    # 用 conf 显式指定 Python（优先级最高，高于 PYSPARK_PYTHON 环境变量）。
    # 实测本集群 spark.executorEnv.PYSPARK_PYTHON 没传到 executor，必须用 conf 才生效。
    .config("spark.archives", "hdfs:///spark_envs/py38_spark.tar.gz#py38_env")
    .config("spark.pyspark.python", "./py38_env/bin/python")        # executor 用 ship 的 py38
    .config("spark.pyspark.driver.python", "/opt/venv/bin/python")  # driver 用容器 venv python（有 pyspark）
    .config("spark.yarn.stagingDir", f"/user/{HDFS_USER}/.sparkStaging")
    .config("spark.driver.host", DRIVER_HOST)
    .config("spark.driver.port", DRIVER_PORT)
    .config("spark.driver.blockManager.port", str(int(DRIVER_PORT) + 1))
    .config("spark.port.maxRetries", "10")
    .config("spark.ui.showConsoleProgress", "false")
    .config("spark.driver.extraJavaOptions", f"-Dlog4j.configuration=file:{log4j_path}")
    .config("spark.sql.shuffle.partitions", "2")
    .getOrCreate()
)
sc = spark.sparkContext
sc.setLogLevel("ERROR")  # 运行时再保底压一次

print("Spark 版本:", sc.version)
print("YARN ApplicationID:", sc.applicationId)

# %% [markdown]
# ## 2. 最小算子验证

# %%
n = sc.range(0, 1000).count()
print("count =", n)
assert n == 1000
print("✅ PySpark YARN client 模式连通性测试通过")

# %% [markdown]
# ## 3. 收尾，释放 YARN 资源

# %%
spark.stop()
print("session stopped")
