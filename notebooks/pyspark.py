from pyspark.sql import SparkSession

HDFS_USER = "hdfs"
DRIVER_HOST = "10.25.100.126"
DRIVER_PORT = "12000"
os.environ["HADOOP_USER_NAME"] = HDFS_USER

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
    .appName("jupyter-yarn")
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
    .enableHiveSupport()
    .getOrCreate()
)
app_id = spark.sparkContext.applicationId
print("🚀 当前任务的 YARN ApplicationID 是:", app_id)

# sc = spark.sparkContext
# sc.setLogLevel("ERROR")  # 运行时再保底压一次


sql_text = """
select
    distinct acctcode, rptdate
from lion_dw_ods.sq_predit_crs_p_bz_inacctinf_doris
where dt='2026-07-08'
  and end_dt = '3000-12-31'
  and acctcode = 'A24010904500103000001'
"""

df = spark.sql(sql_text)
df.show()
# spark.stop()
