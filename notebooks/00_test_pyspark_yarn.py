# %% [markdown]
# # PySpark ↔ YARN 集群连通性测试（cluster 模式 spark-submit）
#
# 本集群 executor 无 python3，client 模式下 python 配置传不到 executor（实测 conf/env 均不生效）。
# 改用与生产一致的 cluster 模式 spark-submit：driver 跑在 YARN AM 内，--archives ship py38 环境，
# spark.yarn.appMasterEnv/executorEnv.PYSPARK_PYTHON 指向 ship 的 python。此模式生产已验证可用。
#
# notebook 用 subprocess 调 spark-submit，作业结果写 HDFS，再用本地 SparkContext 读回。
# 全程出站，不需 docker 宿主机开端口。

# %% [markdown]
# ## 0. 前置自检

# %%
import os, glob, shutil

print("JAVA_HOME =", os.environ.get("JAVA_HOME"))
print("HADOOP_CONF_DIR =", os.environ.get("HADOOP_CONF_DIR"))
assert glob.glob("/etc/hadoop/conf/*.xml"), "❌ /etc/hadoop/conf 下没有 *.xml，先放集群配置"
assert shutil.which("spark-submit"), "❌ 找不到 spark-submit"
print("✅ 环境自检通过")

# %% [markdown]
# ## 1. cluster 模式提交作业到 YARN
#
# flags 与生产 spark-submit 一致：--archives ship py38 环境 + PYSPARK_PYTHON 指向 ship 的 python。
# 退出码 0 + 出现 application_xxx 即提交成功。

# %%
import os, subprocess, time, re

# >>> 改成你集群上实际能读写的 HDFS 用户 <<<
HDFS_USER = "hdfs"
os.environ["HADOOP_USER_NAME"] = HDFS_USER  # simple 认证切换身份

JOB = "/home/jovyan/work/test_job_cluster.py"
OUT = f"/user/{HDFS_USER}/.sparkStaging/yarn_test_result_{int(time.time())}"

cmd = [
    "spark-submit",
    "--master", "yarn",
    "--deploy-mode", "cluster",
    "--archives", "hdfs:///spark_envs/py38_spark.tar.gz#py38_env",
    "--conf", "spark.yarn.appMasterEnv.PYSPARK_PYTHON=./py38_env/bin/python",
    "--conf", "spark.executorEnv.PYSPARK_PYTHON=./py38_env/bin/python",
    "--conf", f"spark.yarn.stagingDir=/user/{HDFS_USER}/.sparkStaging",
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
# 本地 SparkContext 读 HDFS（出站访问 NameNode，不开端口，不需 executor python）。
# 读失败不影响连通性结论 —— cell 1 退出码 0 已证明 YARN 全链路通。

# %%
from pyspark.sql import SparkSession

rspark = (
    SparkSession.builder
    .appName("readback")
    .master("local[2]")
    .getOrCreate()
)
rows = [r.value for r in rspark.read.text(OUT).collect()]
rspark.stop()
print("集群算出的 count =", rows)
assert rows == ["1000"], f"❌ 结果不符: {rows}"
print("✅ PySpark YARN 连通性测试通过（cluster 模式）")
