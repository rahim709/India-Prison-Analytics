"""Validate local Spark FP-Growth and measure materialized mining workloads."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
from time import perf_counter

import numpy as np
import pandas as pd
import psutil

from src.mining.fp_growth import load_transactions, mine_itemsets, mine_rules, minimum_count
from src.preprocessing.cleaning import sha256


def canonical_python(matrix, support, confidence):
    sets=mine_itemsets(matrix,support)
    rules=mine_rules(sets,len(matrix),confidence)
    return ({frozenset(r.itemsets):int(round(r.support*len(matrix))) for r in sets.itertuples()},
            {(r.antecedents,r.consequents):(r.support,r.confidence,r.lift)
             for r in rules.itertuples() if len(r.consequents)==1})


def canonical_spark(data, support, confidence):
    from pyspark.ml.fpm import FPGrowth
    model=FPGrowth(itemsCol='items',minSupport=support,minConfidence=confidence,numPartitions=2).fit(data)
    sets=model.freqItemsets.collect()
    rules=model.associationRules.collect()
    return ({frozenset(r['items']):int(r['freq']) for r in sets},
            {(frozenset(r['antecedent']),frozenset(r['consequent'])):
             (float(r['support']),float(r['confidence']),float(r['lift'])) for r in rules})


def validate_equivalence(actual, expected):
    if actual[0]!=expected[0] or actual[1].keys()!=expected[1].keys():
        raise AssertionError('Spark/Python itemsets or single-consequent rule identities differ.')
    for key in actual[1]:
        if not np.allclose(actual[1][key],expected[1][key],atol=1e-12,rtol=0):
            raise AssertionError('Spark/Python support, confidence or lift differs.')


def measure(function, children=False):
    process=psutil.Process()
    stop=threading.Event()
    def resident():
        total=0
        candidates=[process]
        if children:candidates+=process.children(recursive=True)
        for p in candidates:
            try:total+=p.memory_info().rss
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        return total
    baseline=resident()
    peak=[baseline]
    def sample():
        while not stop.wait(.02):peak[0]=max(peak[0],resident())
    sampler=threading.Thread(target=sample,daemon=True)
    sampler.start()
    start=perf_counter()
    try:result=function()
    finally:
        elapsed=perf_counter()-start
        stop.set()
        sampler.join()
        peak[0]=max(peak[0],resident())
    return result,elapsed,baseline/2**20,peak[0]/2**20


def export_outputs(output,label,result,n):
    itemsets,rules=result
    pd.DataFrame([dict(items=json.dumps(sorted(items)),support_count=count,support=count/n)
                  for items,count in sorted(itemsets.items(),key=lambda p:(len(p[0]),tuple(sorted(p[0]))))],
                 columns=['items','support_count','support']).to_csv(output/f'itemsets_{label}.csv',index=False)
    pd.DataFrame([dict(antecedents=json.dumps(sorted(a)),consequents=json.dumps(sorted(b)),
                       support=values[0],confidence=values[1],lift=values[2])
                  for (a,b),values in sorted(rules.items(),key=lambda p:(tuple(sorted(p[0][0])),tuple(sorted(p[0][1]))))],
                 columns=['antecedents','consequents','support','confidence','lift']).to_csv(output/f'rules_{label}.csv',index=False)


def run_spark_fp_growth(root, repetitions=3):
    from pyspark.sql import SparkSession
    from pyspark.sql.types import StructType
    import pyspark
    if repetitions<3:raise ValueError('Use at least three measured repetitions.')
    root=Path(root).resolve()
    output=root/'results/tables/spark_fp_growth';output.mkdir(parents=True,exist_ok=True)
    benchmarks=root/'results/benchmarks/spark_fp_growth';benchmarks.mkdir(parents=True,exist_ok=True)
    rows,matrix=load_transactions(root)
    inputs=[dict(file=str(p.relative_to(root)),sha256=sha256(p)) for p in (root/'data/processed/transformed').iterdir() if p.is_file()]
    os.environ['SPARK_LOCAL_IP']='127.0.0.1'
    os.environ['PYSPARK_PYTHON']=sys.executable
    os.environ['PYSPARK_DRIVER_PYTHON']=sys.executable
    start=perf_counter()
    spark=(SparkSession.builder.master('local[2]').appName('IndiaPrisonPhase9')
           .config('spark.ui.showConsoleProgress','false')
           .config('spark.log.level','ERROR')
           .config('spark.driver.extraJavaOptions', '-Dlog4j2.configurationFile=' + (root/'src/utils/spark-log4j2.properties').as_uri())
           .config('spark.ui.enabled','false').config('spark.driver.host','127.0.0.1')
           .config('spark.driver.bindAddress','127.0.0.1').config('spark.driver.memory','1g')
           .config('spark.sql.shuffle.partitions','2').config('spark.default.parallelism','2')
           .config('spark.sql.adaptive.enabled','false').getOrCreate())
    startup=perf_counter()-start
    spark.sparkContext.setLogLevel('ERROR')
    measurements=[];validation=[]
    try:
        start=perf_counter()
        contract=json.loads((root/'results/tables/transformation/spark_input_contract.json').read_text())
        data=spark.read.schema(StructType.fromJson(contract['association']['schema'])).json(
            str(root/'data/processed/transformed/transactions.jsonl')).repartition(2).cache()
        actual_rows={r['profile_id']:(r['state'],r['year'],tuple(sorted(r['items']))) for r in data.collect()}
        expected_rows={r['profile_id']:(r['state'],r['year'],tuple(sorted(r['items']))) for r in rows}
        if actual_rows!=expected_rows or data.count()!=len(rows):raise AssertionError('Spark transaction input differs.')
        preparation=perf_counter()-start
        config=dict(spark.sparkContext.getConf().getAll())
        start=perf_counter()
        cold=canonical_spark(data,.10,.70)
        first_job=perf_counter()-start
        validate_equivalence(cold,canonical_python(matrix,.10,.70))
        export_outputs(output,'s0p10_c0p70',cold,len(rows))
        for support in [.05,.10,.15,.20]:
            result=canonical_spark(data,support,.60)
            for confidence in [.60,.70,.80]:
                filtered=(result[0],{key:values for key,values in result[1].items() if values[1]>=confidence})
                expected=canonical_python(matrix,support,confidence)
                validate_equivalence(filtered,expected)
                label=f's{support:.2f}_c{confidence:.2f}'.replace('.','p')
                export_outputs(output,label,filtered,len(rows))
                validation.append(dict(min_support=support,min_count=minimum_count(support,len(rows)),
                                       min_confidence=confidence,itemsets=len(result[0]),rules=len(filtered[1]),equivalent=True))
        for support,confidence in [(.10,.70),(.05,.70)]:
            # Warm each scenario once; exclude these runs from measured repetitions.
            for name,function,children in [('python',lambda:canonical_python(matrix,support,confidence),False),
                                           ('spark',lambda:canonical_spark(data,support,confidence),True)]:
                result,elapsed,baseline,peak=measure(function,children)
                measurements.append(dict(engine=name,min_support=support,min_confidence=confidence,
                                         repetition=0,warmup=True,seconds=elapsed,rss_baseline_mib=baseline,
                                         sampled_peak_rss_mib=peak,itemsets=len(result[0]),rules=len(result[1])))
            for repeat in range(1,repetitions+1):
                order=['python','spark'] if repeat%2 else ['spark','python']
                observed={}
                for name in order:
                    function=(lambda:canonical_python(matrix,support,confidence)) if name=='python' else (lambda:canonical_spark(data,support,confidence))
                    result,elapsed,baseline,peak=measure(function,name=='spark')
                    observed[name]=result
                    measurements.append(dict(engine=name,min_support=support,min_confidence=confidence,
                                             repetition=repeat,warmup=False,seconds=elapsed,rss_baseline_mib=baseline,
                                             sampled_peak_rss_mib=peak,itemsets=len(result[0]),rules=len(result[1])))
                validate_equivalence(observed['spark'],observed['python'])
        data.unpersist()
        java=spark.sparkContext._jvm.java.lang.System.getProperty('java.version')
        java_vendor=spark.sparkContext._jvm.java.lang.System.getProperty('java.vendor')
    finally:spark.stop()
    timings=pd.DataFrame(measurements)
    timings.to_csv(benchmarks/'timing_runs.csv',index=False)
    stats=[]
    measured=timings[~timings.warmup]
    for support,group in measured.groupby('min_support'):
        py=group[group.engine=='python'].seconds
        sp=group[group.engine=='spark'].seconds
        stats.append(dict(min_support=support,min_confidence=.70,repetitions=repetitions,
                          python_median_seconds=float(py.median()),spark_median_seconds=float(sp.median()),
                          python_min_seconds=float(py.min()),python_max_seconds=float(py.max()),
                          spark_min_seconds=float(sp.min()),spark_max_seconds=float(sp.max()),
                          speedup_python_over_spark=float(py.median()/sp.median()),
                          spark_over_python_ratio=float(sp.median()/py.median())))
    pd.DataFrame(stats).to_csv(benchmarks/'timing_summary.csv',index=False)
    pd.DataFrame(validation).to_csv(output/'equivalence.csv',index=False)
    for item in inputs:
        if sha256(root/item['file'])!=item['sha256']:raise AssertionError('Prepared inputs changed.')
    summary=dict(transactions=len(rows),vocabulary=len(matrix.columns),spark_version=pyspark.__version__,
                 python=platform.python_version(),java=java,java_vendor=java_vendor,platform=platform.platform(),
                 cpu=next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),'unknown'),
                 logical_cpus=psutil.cpu_count(),physical_cpus=psutil.cpu_count(logical=False),
                 host_memory_gib=psutil.virtual_memory().total/2**30,master='local[2]',partitions=2,
                 spark_configuration={k:v for k,v in config.items() if not any(token in k.lower() for token in ['secret','password','token'])},
                 startup_seconds=startup,cached_input_preparation_and_validation_seconds=preparation,
                 first_materialized_baseline_job_seconds=first_job,
                 cold_baseline_end_to_end_seconds=startup+preparation+first_job,
                 cold_scope='single observed Spark startup + schema read/cache/input equivalence + first baseline fit and both output collections; not a repeated cold benchmark',
                 benchmark_scope='preloaded Boolean matrix versus cached two-partition Spark input; fit, rule generation, both materializations and canonical output conversion; excludes disk export and validation',
                 rule_scope='single-item consequents, matching Spark API; Python complete rules are generated before this restriction',
                 repetitions=repetitions,warmup_per_engine_per_scenario=1,
                 memory_scope='20 ms RSS samples: Python driver only for Python runs; driver plus recursive children/JVM for Spark; retained heaps/shared pages mean these are process footprints, not isolated algorithm allocations',
                 input_roundtrip_equivalent=True,parameter_settings_verified=12,benchmark_results=stats,inputs=inputs)
    (benchmarks/'environment_and_protocol.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--repetitions',type=int,default=3)
    args=parser.parse_args()
    summary=run_spark_fp_growth(args.root,args.repetitions)
    print(json.dumps(summary['benchmark_results'],indent=2))


if __name__=='__main__':main()
