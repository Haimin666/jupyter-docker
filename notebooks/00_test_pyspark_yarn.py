# %% [markdown]
# # PySpark ↔ YARN 集群连通性测试
#
# 本节点无法开防火墙端口，client 模式（AM 回连 driver）走不通，notebook 也不支持交互式 cluster 模式。
# 方案：用 `spark-submit --deploy-mode cluster` 提交独立作业 —— driver 跑在 YARN AM 内，
# notebook 只做出站提交 + 出站读 HDFS 结果，全程不开入站端口。
# 运行方式：JupyterLab 打开本文件，逐 cell 执行。

# %% [markdown]
# ## 0. 前置自检（不连集群，确认环境变量/配置就位）

# %%
import os, glob, shutil

print("JAVA_HOME =", os.environ.get("JAVA_HOME"))
print("HADOOP_CONF_DIR =", os.environ.get("HADOOP_CONF_DIR"))

confs = glob.glob("/etc/hadoop/conf/*.xml")
print("hadoop xml:", confs)
assert confs, "❌ /etc/hadoop/conf 下没有 *.xml，请先按 hadoop-conf/README.md 放集群配置"

# spark-submit 由 pyspark 自带，确认在 PATH
assert shutil.which("spark-submit"), "❌ 找不到 spark-submit，确认 pyspark 已装"
print("spark-submit:", shutil.which("spark-submit"))
print("✅ 环境自检通过")

# %% [markdown]
# ## 1. cluster 模式提交作业到 YARN
#
# - driver 在 YARN AM 里跑，notebook 只出站提交，不需集群回连本机
# - 作业结果写到 HDFS（cell 2 回读）
# - 退出码 0 + 出现 application_xxx 即提交成功

# %%
import os, subprocess, time, re

# >>> 改成你集群上实际能读写的 HDFS 用户 <<<
HDFS_USER = "hdfs"

# simple 认证下，设 HADOOP_USER_NAME 切换 HDFS/YARN 身份（容器 jovyan 用户集群无权限）
os.environ["HADOOP_USER_NAME"] = HDFS_USER

JOB = "/home/jovyan/work/test_job_cluster.py"
# 每次用唯一路径，避免 saveAsTextFile 目标已存在
OUT = f"/user/{HDFS_USER}/.sparkStaging/yarn_test_result_{int(time.time())}"

cmd = [
    "spark-submit",
    "--master", "yarn",
    "--deploy-mode", "cluster",
    "--conf", "spark.pyspark.python=python3",          # AM 上 Python driver + executor 用集群 python3
    "--conf", f"spark.yarn.stagingDir=/user/{HDFS_USER}/.sparkStaging",
    "--conf", "spark.sql.shuffle.partitions=2",
    JOB, OUT,
]
print("提交命令:", " ".join(cmd))
print("HDFS 输出:", OUT)
print("--- spark-submit 输出 ---")

app_ids = []
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
for line in proc.stdout:
    print(line, end="")
    m = re.search(r"application_\d+_\d+", line)
    if m and m.group(0) not in app_ids:
        app_ids.append(m.group(0))
proc.wait()
print("--- 结束 ---")
print("退出码:", proc.returncode)
print("YARN ApplicationID:", app_ids or "未捕获（看上面输出）")
assert proc.returncode == 0, "❌ spark-submit 失败，看上面输出"
print("✅ 作业提交并执行成功")

# %% [markdown]
# ## 2. 回读 HDFS 结果，确认算出来的是 1000
#
# 本地 SparkContext 读 HDFS（出站访问 NameNode，不开端口）。
# 读失败不影响连通性结论 —— cell 1 退出码 0 已证明 YARN 全链路通。

# %%
from pyspark.sql import SparkSession

rspark = (
    SparkSession.builder
    .appName("readback")
    .master("local[2]")
    .config("spark.pyspark.python", "python3")
    .getOrCreate()
)
rows = [r.value for r in rspark.read.text(OUT).collect()]
rspark.stop()
print("集群算出的 count =", rows)
assert rows == ["1000"], f"❌ 结果不符: {rows}"
print("✅ PySpark YARN 连通性测试通过（cluster 模式）")
