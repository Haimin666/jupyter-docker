# ===== builder：带编译链，装全部依赖到 venv =====
FROM python:3.9.23-slim AS builder

# apt 切清华源（国内加速）
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources

# 构建期编译依赖（sasl 等可能从源码编译）+ 下载 Java 8 用的 wget
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libsasl2-dev \
        libffi-dev \
        wget \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Java 8 (Temurin) —— 集群为 JDK 8；trixie 主源无 openjdk-8，用 Temurin 8 tarball
# 走清华 Adoptium 镜像（github releases 国内不稳）
RUN mkdir -p /opt/jdk8 \
    && wget -q --tries=3 -O /tmp/jdk8.tar.gz \
        https://mirrors.tuna.tsinghua.edu.cn/Adoptium/8/jre/x64/linux/OpenJDK8U-jre_x64_linux_hotspot_8u492b09.tar.gz \
    && tar xzf /tmp/jdk8.tar.gz -C /opt/jdk8 --strip-components=1 \
    && rm /tmp/jdk8.tar.gz

# venv 隔离，便于整目录拷到 final 阶段
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements.txt /tmp/requirements.txt
# jupyterlab 固定版本（可复现）；其余依赖按 requirements.txt
RUN pip install --upgrade pip && \
    pip install jupyterlab==4.5.9 && \
    pip install -r /tmp/requirements.txt

# ===== final：只带运行期 so + Java 8，不带编译链 =====
FROM python:3.9.23-slim

# Java 8 从 builder 拷过来（builder 已用 wget 下载解压）
COPY --from=builder /opt/jdk8 /opt/jdk8

# apt 切清华源（国内加速）
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources

# 运行期系统库：
# - libsasl2-2：sasl / thrift-sasl 运行需要
# - procps：pyspark 的 load-spark-env.sh / spark-submit 需要 ps 命令
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsasl2-2 \
        procps \
    && rm -rf /var/lib/apt/lists/*

# 拷贝构建期装好的 venv（python:3.9.23-slim 两阶段一致，venv 内解释器符号链接有效）
COPY --from=builder /opt/venv /opt/venv

ENV JAVA_HOME=/opt/jdk8 \
    PATH=/opt/venv/bin:/opt/jdk8/bin:$PATH \
    HADOOP_CONF_DIR=/etc/hadoop/conf \
    HIVE_CONF_DIR=/etc/hive/conf \
    FLINK_LOG_DIR=/home/jovyan/.flink/log
# 注意：不全局设 PYSPARK_PYTHON。
# - 本地模式：pyspark 默认用 venv python（sys.executable），工作进程能 import pyspark。
# - YARN 提交：在 notebook 里按需设 spark.pyspark.python=python3（executor 走集群 python）。

# 创建非 root 普通用户
RUN useradd -m -s /bin/bash jovyan

# pyflink 日志目录（FLINK_LOG_DIR）—— 默认写到 root 所有的 pyflink/log 会权限拒绝，预建到 jovyan 家目录
RUN mkdir -p /home/jovyan/.flink/log && chown -R jovyan:jovyan /home/jovyan/.flink

COPY --chown=jovyan:jovyan start.sh /home/jovyan/start.sh
RUN chmod +x /home/jovyan/start.sh

USER jovyan
WORKDIR /home/jovyan/work

EXPOSE 8888
CMD ["/home/jovyan/start.sh"]
