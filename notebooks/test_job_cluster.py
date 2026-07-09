"""集群模式 Spark 测试作业。

由 notebook 通过 `spark-submit --deploy-mode cluster` 提交，在 YARN AM 上运行。
count 后把结果写入 HDFS（路径由 argv[1] 传入），供 notebook 回读验证。
cluster 模式下 driver 在集群内，不需要 docker 宿主机开入站端口。
"""
import sys
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("jupyter-yarn-cluster-test").getOrCreate()
sc = spark.sparkContext

n = sc.range(0, 1000).count()
sc.parallelize([str(n)], 1).saveAsTextFile(sys.argv[1])

spark.stop()
