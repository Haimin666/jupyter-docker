# %% [markdown]
# # PyFlink ↔ YARN 集群连通性测试
#
# ⚠️ 前置知识：pip 装的 `apache-flink` 是 **hadoop-free** 版。
#    提交到 YARN/HDFS 需要额外 hadoop 类，见下方 Cell 0 的检查与说明。
#    先用 Cell 1（本地模式）确认 pyflink 本身在容器里能跑，再用 Cell 2 测 YARN。

# %% [markdown]
# ## 0. 环境自检：定位 pyflink 自带的 flink 发行版，并检查 hadoop jar

# %%
import os, glob, pyflink

print("JAVA_HOME =", os.environ.get("JAVA_HOME"))
print("pyflink 路径 =", os.path.dirname(pyflink.__file__))

flink_home = os.path.dirname(pyflink.__file__)  # pyflink 包目录即发行版根
lib_dir = os.path.join(flink_home, "lib")
jars = glob.glob(os.path.join(lib_dir, "*.jar"))
print("lib jars 数量:", len(jars))

# 关键：有没有 hadoop 相关 jar（flink-shaded-hadoop2-uber / flink-hadoop*）
hadoop_jars = [j for j in jars if "hadoop" in os.path.basename(j).lower()]
print("hadoop 相关 jar:", [os.path.basename(j) for j in hadoop_jars] or "❌ 无 —— 提交 YARN 会报 NoClassDefFoundError")

if not hadoop_jars:
    print("""
    >>> 解决方法（任选其一）<<<
    A) 把集群的 hadoop 客户端 jar 暴露给 flink（推荐，零拷贝大文件）：
       在启动 jupyter 前设环境变量指向集群 hadoop 目录的 jar：
         export FLINK_HADOOP_CLASSPATH=$(hadoop classpath)
       （容器里没装 hadoop 客户端的话不适用）
    B) 下载 flink-shaded-hadoop2-uber-2.8.3-10.0.jar 放进：
         {lib_dir}
       下载：https://repo.maven.apache.org/maven2/org/apache/flink/flink-shaded-hadoop2-uber/2.8.3-10.0/
    """.format(lib_dir=lib_dir))

# %% [markdown]
# ## 1. 本地模式 sanity check（不连集群，确认 pyflink 能 import + 跑通）
# bounded datagen 产 10 行后停止，作业自然结束，不会阻塞 kernel。

# %%
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment

env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(1)
t_env = StreamTableEnvironment.create(env)

t_env.execute_sql("""
    CREATE TABLE source (
        word STRING
    ) WITH (
        'connector' = 'datagen',
        'rows-per-second' = '3',
        'number-of-rows' = '10',
        'fields.word.length' = '1'
    )
""")

t_env.execute_sql("""
    CREATE TABLE sink (
        word STRING,
        cnt BIGINT
    ) WITH ('connector' = 'print')
""")

t_env.execute_sql("""
    INSERT INTO sink
    SELECT word, COUNT(*) AS cnt
    FROM source
    GROUP BY word
""").wait()
print("✅ PyFlink 本地模式可运行")

# %% [markdown]
# ## 2. YARN 提交连通性测试
# 前提：Cell 0 检查出的 hadoop jar 问题已解决。
# 模式：yarn-session —— flink 起一个常驻 session 集群，作业提交到其上。
#
# 注意：pyflink 提交 YARN 需要 HADOOP_CONF_DIR（已挂载 /etc/hadoop/conf）能被读到。

# %%
import os
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment

env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(1)

# 关键：在创建 TableEnv 后、提交前，通过配置声明提交目标为 YARN session
config = env.get_config()
config.set_string("execution.target", "yarn-session")
config.set_string("yarn.application.name", "jupyter-flink-test")
# 若需要指定队列：config.set_string("yarn.application.queue", "default")

t_env = StreamTableEnvironment.create(env)

t_env.execute_sql("""
    CREATE TABLE sink (
        cnt BIGINT
    ) WITH ('connector' = 'print')
""")
t_env.execute_sql("INSERT INTO sink SELECT COUNT(*) FROM (VALUES (1), (2), (3)) AS t(c)").wait()
print("✅ PyFlink YARN 提交成功（如失败多为 hadoop jar 缺失，见 Cell 0）")
