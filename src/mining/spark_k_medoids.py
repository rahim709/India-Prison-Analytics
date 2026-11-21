"""Run distributed PAM swap evaluation on the frozen state-year features."""
import argparse
import json
import os
from pathlib import Path
import platform
import sys
from time import perf_counter

import numpy as np
import pandas as pd
import psutil
from scipy.spatial.distance import cdist
from sklearn.metrics import adjusted_rand_score, silhouette_score

from src.mining.k_medoids import MAX_ITER, TOL, load_profiles, pam, swap_costs
from src.mining.spark_fp_growth import measure
from src.preprocessing.cleaning import sha256


def partition_swap_costs(iterator, medoids, n):
    """Sum assignment and every medoid-swap cost for this worker partition."""
    medoids=np.asarray(medoids,dtype=int)
    candidates=np.setdiff1d(np.arange(n),medoids)
    costs=np.zeros((len(medoids),len(candidates)))
    objective=0.0
    for _, row in iterator:
        row=np.asarray(row,dtype=float)
        local=row[medoids]
        closest=int(local.argmin())
        nearest=float(local[closest])
        second=float(np.partition(local,1)[1]) if len(medoids)>1 else np.inf
        objective+=nearest
        for position in range(len(medoids)):
            remaining=second if position==closest else nearest
            costs[position]+=np.minimum(remaining,row[candidates])
    yield objective,costs


def partition_assignments(iterator, medoids):
    medoids=np.asarray(medoids,dtype=int)
    own={int(index):j for j,index in enumerate(medoids)}
    for index,row in iterator:
        local=np.asarray(row)[medoids]
        label=own.get(int(index),int(local.argmin()))
        yield int(index),label,float(local[label])


def spark_pam(distance_rows, n, initial_medoids, tol=TOL, max_iter=MAX_ITER):
    medoids=np.sort(np.asarray(initial_medoids,dtype=int))
    if len(set(medoids))!=len(medoids) or len(medoids)==0 or medoids.min()<0 or medoids.max()>=n:
        raise ValueError('Initial medoids must be unique valid observation indices.')
    history=[];snapshots=[]
    removed=added=None
    for iteration in range(max_iter+1):
        current_medoids=medoids.tolist()
        # Workers evaluate all swaps over their observation blocks; only partial sums return.
        partial=distance_rows.mapPartitions(lambda rows: partition_swap_costs(rows,current_medoids,n)).collect()
        current=float(sum(value[0] for value in partial))
        costs=sum((value[1] for value in partial),np.zeros((len(medoids),n-len(medoids))))
        candidates=np.setdiff1d(np.arange(n),medoids)
        history.append(dict(step=iteration,cost=current,removed=removed,added=added,
                            medoid_indices=medoids.tolist()))
        snapshots.append((medoids.copy(),candidates.copy(),costs.copy()))
        if not costs.size or costs.min()>=current-tol:break
        if iteration==max_iter:raise RuntimeError('Spark PAM did not converge within the iteration limit.')
        position,candidate_position=np.argwhere((costs<=costs.min()+tol)&(costs<current-tol))[0]
        removed,added=int(medoids[position]),int(candidates[candidate_position])
        medoids=np.sort(np.append(np.delete(medoids,position),added))
    final_medoids=medoids.tolist()
    assignments=sorted(distance_rows.mapPartitions(lambda rows: partition_assignments(rows,final_medoids)).collect())
    if [r[0] for r in assignments]!=list(range(n)):raise AssertionError('Spark assignments lost observation indices.')
    labels=np.array([r[1] for r in assignments]);distances=np.array([r[2] for r in assignments])
    if not np.isclose(distances.sum(),current,atol=1e-9,rtol=0):raise AssertionError('Distributed objective and assignments differ.')
    return dict(medoids=medoids,labels=labels,distances=distances,cost=current,
                history=history,snapshots=snapshots,swaps=len(history)-1,converged=True)


def validate_fit(actual, expected, d):
    if not np.array_equal(actual['medoids'],expected['medoids']):raise AssertionError('Medoid identities differ.')
    if adjusted_rand_score(actual['labels'],expected['labels'])!=1:raise AssertionError('Partitions differ.')
    if not np.isclose(actual['cost'],expected['cost'],atol=1e-9,rtol=0):raise AssertionError('Objectives differ.')
    np.testing.assert_allclose(actual['distances'],expected['distances'],atol=1e-12,rtol=0)
    if len(actual['history'])!=len(expected['history']):raise AssertionError('Accepted swap counts differ.')
    max_error=0.0
    for snapshot,reference in zip(actual['snapshots'],expected['history']):
        medoids,candidates,costs=snapshot
        if medoids.tolist()!=reference['medoid_indices']:raise AssertionError('Swap trajectories differ.')
        expected_candidates,expected_costs=swap_costs(d,medoids)
        np.testing.assert_array_equal(candidates,expected_candidates)
        np.testing.assert_allclose(costs,expected_costs,atol=1e-9,rtol=0)
        max_error=max(max_error,float(np.max(np.abs(costs-expected_costs))) if costs.size else 0)
    return dict(ari=1.0,objective_difference=abs(actual['cost']-expected['cost']),
                max_assignment_distance_difference=float(np.max(np.abs(actual['distances']-expected['distances']))),
                max_candidate_swap_cost_difference=max_error,equivalent=True)


def run_spark_k_medoids(root,repetitions=3):
    from pyspark.sql import SparkSession
    from pyspark.sql.types import StructType
    import pyspark
    if repetitions<3:raise ValueError('At least three repetitions are required.')
    root=Path(root).resolve()
    output=root/'results/tables/spark_k_medoids';output.mkdir(parents=True,exist_ok=True)
    benchmarks=root/'results/benchmarks/spark_k_medoids';benchmarks.mkdir(parents=True,exist_ok=True)
    raw,scaled,x=load_profiles(root);n=len(raw)
    reference=json.loads((root/'results/tables/k_medoids/run_summary.json').read_text())
    initial=np.sort([int(raw.index[raw.profile_id.eq(name)][0]) for name in reference['initial_medoid_profile_ids']])
    k=len(initial)
    inputs=[dict(file=str(p.relative_to(root)),sha256=sha256(p)) for p in (root/'data/processed/transformed').iterdir() if p.is_file()]
    inputs.append(dict(file='results/tables/k_medoids/run_summary.json',sha256=sha256(root/'results/tables/k_medoids/run_summary.json')))
    os.environ['SPARK_LOCAL_IP']='127.0.0.1'
    os.environ['PYSPARK_PYTHON']=sys.executable;os.environ['PYSPARK_DRIVER_PYTHON']=sys.executable
    os.environ['PYTHONPATH']=str(root)+os.pathsep+os.environ.get('PYTHONPATH','')
    start=perf_counter()
    spark=(SparkSession.builder.master('local[2]').appName('IndiaPrisonPhase10')
           .config('spark.ui.showConsoleProgress','false')
           .config('spark.log.level','ERROR')
           .config('spark.driver.extraJavaOptions', '-Dlog4j2.configurationFile=' + (root/'src/utils/spark-log4j2.properties').as_uri())
           .config('spark.ui.enabled','false').config('spark.driver.host','127.0.0.1')
           .config('spark.driver.bindAddress','127.0.0.1').config('spark.driver.memory','1g')
           .config('spark.default.parallelism','2').config('spark.sql.shuffle.partitions','2')
           .config('spark.sql.adaptive.enabled','false').getOrCreate())
    startup=perf_counter()-start;spark.sparkContext.setLogLevel('ERROR')
    records=[];validations=[]
    try:
        start=perf_counter();d=cdist(x,x,metric='cityblock');python_distance_preparation=perf_counter()-start
        start=perf_counter()
        contract=json.loads((root/'results/tables/transformation/spark_input_contract.json').read_text())
        frame=spark.read.schema(StructType.fromJson(contract['clustering']['schema'])).json(str(root/'data/processed/transformed/spark_profiles.jsonl'))
        loaded={row['profile_id']:row['features'] for row in frame.collect()}
        if set(loaded)!=set(raw.profile_id):raise AssertionError('Spark profile identities differ.')
        np.testing.assert_array_equal(np.array([loaded[name] for name in raw.profile_id]),x)
        # Broadcast the small feature matrix; workers compute and cache separate distance rows.
        context=spark.sparkContext;broadcast=context.broadcast(x)
        distance_rows=context.parallelize(list(range(n)),2).map(
            lambda index:(index,np.abs(broadcast.value-broadcast.value[index]).sum(axis=1))).cache()
        if distance_rows.count()!=n:raise AssertionError('Cached distance rows are incomplete.')
        spark_preparation=perf_counter()-start
        start=perf_counter();cold=spark_pam(distance_rows,n,initial);first_fit=perf_counter()-start
        expected=pam(d,k,initial)
        validations.append(dict(initialization='phase7_selected_initial',**validate_fit(cold,expected,d)))
        random_initial=np.sort(np.random.default_rng(42).choice(n,size=k,replace=False))
        alternate=spark_pam(distance_rows,n,random_initial)
        validations.append(dict(initialization='random_seed_42',**validate_fit(alternate,pam(d,k,random_initial),d)))
        for name in ['python','spark']:
            function=(lambda:pam(d,k,initial)) if name=='python' else (lambda:spark_pam(distance_rows,n,initial))
            result,elapsed,baseline,peak=measure(function,name=='spark')
            records.append(dict(engine=name,repetition=0,warmup=True,seconds=elapsed,
                                rss_baseline_mib=baseline,sampled_peak_rss_mib=peak,objective=result['cost'],swaps=result['swaps']))
        for repeat in range(1,repetitions+1):
            pair={}
            for name in (['python','spark'] if repeat%2 else ['spark','python']):
                function=(lambda:pam(d,k,initial)) if name=='python' else (lambda:spark_pam(distance_rows,n,initial))
                result,elapsed,baseline,peak=measure(function,name=='spark');pair[name]=result
                records.append(dict(engine=name,repetition=repeat,warmup=False,seconds=elapsed,
                                    rss_baseline_mib=baseline,sampled_peak_rss_mib=peak,objective=result['cost'],swaps=result['swaps']))
            validate_fit(pair['spark'],pair['python'],d)
        config=dict(context.getConf().getAll())
        java=context._jvm.java.lang.System.getProperty('java.version')
        distance_rows.unpersist();broadcast.destroy()
    finally:spark.stop()
    assignments=raw.copy();assignments['cluster']=cold['labels']
    assignments['medoid_profile_id']=[raw.iloc[cold['medoids'][label]].profile_id for label in cold['labels']]
    assignments['distance_to_medoid']=cold['distances']
    assignments.to_csv(output/'cluster_assignments.csv',index=False)
    raw.iloc[cold['medoids']].assign(cluster=range(k)).to_csv(output/'medoids.csv',index=False)
    pd.DataFrame([{**row,'medoid_indices':json.dumps(row['medoid_indices'])} for row in cold['history']]).to_csv(output/'objective_trace.csv',index=False)
    pd.DataFrame(validations).to_csv(output/'equivalence.csv',index=False)
    timings=pd.DataFrame(records);timings.to_csv(benchmarks/'timing_runs.csv',index=False)
    py=timings[(~timings.warmup)&timings.engine.eq('python')].seconds
    sp=timings[(~timings.warmup)&timings.engine.eq('spark')].seconds
    result=dict(python_median_seconds=float(py.median()),spark_median_seconds=float(sp.median()),
                python_min_seconds=float(py.min()),python_max_seconds=float(py.max()),
                spark_min_seconds=float(sp.min()),spark_max_seconds=float(sp.max()),
                speedup_python_over_spark=float(py.median()/sp.median()),spark_over_python_ratio=float(sp.median()/py.median()))
    pd.DataFrame([result]).to_csv(benchmarks/'timing_summary.csv',index=False)
    for item in inputs:
        if sha256(root/item['file'])!=item['sha256']:raise AssertionError('Frozen inputs changed.')
    summary=dict(profiles=n,k=k,distance='cityblock',features=list(scaled.columns[1:]),
                 initial_medoid_ids=raw.iloc[initial].profile_id.tolist(),medoid_ids=raw.iloc[cold['medoids']].profile_id.tolist(),
                 objective=cold['cost'],silhouette=silhouette_score(d,cold['labels'],metric='precomputed'),
                 swaps=cold['swaps'],tol=TOL,max_iter=MAX_ITER,input_roundtrip_equivalent=True,
                 distributed_work='Python Spark workers compute/cache distance rows, assignment distances and every candidate-swap partial cost; driver sums partition aggregates and selects the best improving swap',
                 benchmark_scope='fixed saved initialization; cached pairwise distances on both engines; PAM SWAP iterations, assignments and result materialization; excludes BUILD, distance preparation, validation and exports',
                 scalability_limit='O(n^2) distance storage, broadcast small complete feature matrix, O(k*n) driver cost table; local host only',
                 cluster_label_scope='labels follow sorted medoid/profile indices and may permute Phase 7 occupancy-ordered IDs; compare representative IDs and ARI',
                 memory_scope='20 ms RSS: driver only for Python; driver plus recursive children including JVM and Python workers for Spark; footprints, not isolated allocations',
                 repetitions=repetitions,warmups_per_engine=1,benchmark=result,
                 startup_seconds=startup,python_distance_preparation_seconds=python_distance_preparation,
                 spark_input_validation_and_distance_preparation_seconds=spark_preparation,first_spark_fit_seconds=first_fit,
                 cold_spark_observed_seconds=startup+spark_preparation+first_fit,
                 cold_scope='single session startup + input validation and distance preparation + first fit; excludes imports and process launch; no repeated cold ratio',
                 spark_version=pyspark.__version__,python=platform.python_version(),java=java,
                 logical_cpus=psutil.cpu_count(),physical_cpus=psutil.cpu_count(logical=False),host_memory_gib=psutil.virtual_memory().total/2**30,
                 cpu=next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),
                 master='local[2]',partitions=2,spark_configuration=config,inputs=inputs)
    (benchmarks/'environment_and_protocol.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    summary=run_spark_k_medoids(parser.parse_args().root)
    print(json.dumps(summary['benchmark'],indent=2))


if __name__=='__main__':main()
