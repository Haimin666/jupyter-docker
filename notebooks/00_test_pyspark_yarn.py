# %% [markdown]
# # PySpark ↔ YARN 集群连通性测试
#
# 目的：在 Jupyter 里提交一个最小 Spark 作业到 YARN，验证容器 → 集群链路打通。
# 运行方式：JupyterLab 打开本文件，逐 cell 执行（或复制到 Notebook）。

# %% [markdown]
# ## 0. 前置自检（不连集群，先确认环境变量/配置就位）

# %%
import os, glob

# Java8 必须就位（Spark 启动 JVM 用）
print("JAVA_HOME =", os.environ.get("JAVA_HOME"))
print("HADOOP_CONF_DIR =", os.environ.get("HADOOP_CONF_DIR"))

# 挂载进来的集群 XML 必须存在，否则 spark 不知道 ResourceManager / NameNode 在哪
confs = glob.glob("/etc/hadoop/conf/*.xml")
print("hadoop xml:", confs)
assert confs, "❌ /etc/hadoop/conf 下没有 *.xml，请先按 hadoop-conf/README.md 放集群配置"
print("✅ 环境自检通过")

# %% [markdown]
# ## 1. 构造 SparkSession（YARN client 模式）
#
# - `master=yarn` + `deployMode=client`：driver 跑在容器里，executor 在集群
# - `spark.pyspark.python=python3`：executor 走集群节点的 python3（镜像里没全局设，按需在这里设）
# - `spark.yarn.stagingDir` 改成你的 HDFS 用户目录，避免权限问题

# %%
from pyspark.sql import SparkSession

# >>> 改成你集群上实际能读写的 HDFS 用户 / 目录 <<<
HDFS_USER = "hdfs"  # 例如 "hive" / 你的业务账号

spark = (
    SparkSession.builder
    .appName("jupyter-yarn-test")
    .master("yarn")
    .deployMode("client")
    .config("spark.pyspark.python", "python3")  # executor 端 python；driver 用 venv python（sys.executable），不覆盖
    .config("spark.yarn.stagingDir", f"/user/{HDFS_USER}/.sparkStaging")
    .config("spark.sql.shuffle.partitions", "2")
    .getOrCreate()
)

sc = spark.sparkContext
print("Spark 版本:", sc.version)
print("YARN ApplicationID:", sc.applicationId)  # 出现 application_xxx 说明已提交到 YARN

# %% [markdown]
# ## 2. 跑一个最小算子（range + count），验证 executor 真能起来干活

# %%
n = sc.range(0, 1000).count()
print("count =", n)
assert n == 1000
print("✅ PySpark YARN 连通性测试通过")

# %% [markdown]
# ## 3. 顺带验证能读 HDFS（真正确认 NameNode 通）
# 没有现成数据的话跳过这个 cell。

# %%
# spark.read.text("/tmp/集群上任意一个存在的文件路径").show(5)

# %% [markdown]
# ## 4. 收尾，释放 YARN 资源

# %%
spark.stop()
print("session stopped")
