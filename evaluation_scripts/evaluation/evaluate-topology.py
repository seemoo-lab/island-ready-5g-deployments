import argparse
import geopandas as gpd
import math
import networkx as nx
import numpy as np
import pandas as pd
import pickle
from pathlib import Path
from networkx.algorithms.connectivity import build_auxiliary_edge_connectivity
from networkx.algorithms.flow import build_residual_network
from shapely.geometry import LineString
import time




t0 = time.time()

# ----------------------------------------------------------------------------------------------------
def parse_args():
  parser = argparse.ArgumentParser(
    description="Generate a population-based mobile network topology."
  )

  parser.add_argument(
    '--num-replicas',
    type=int,
    default=5,
    help="Number of core replicas (default: 5)",
  )

  parser.add_argument(
    '--topology',
    type=str,
    default='full',
    help="Core network topology (default 'full')",
  )

  parser.add_argument(
    '--link-availability',
    type=float,
    default=0.99999,
    help="Link availability per km (default: 0.99999)",
  )

  parser.add_argument(
    '--replica-availability',
    type=float,
    default=1.0,
    help="Core replica availability (default: 1.0)",
  )

  parser.add_argument(
    '--overwrite',
    action="store_true",
    help="Overwrite existing results",
  )

  return parser.parse_args()

args = parse_args()
# ----------------------------------------------------------------------------------------------------





# ----------------------------------------------------------------------------------------------------
TOPOLOGY = args.topology
NUM_REPLICAS = args.num_replicas
REPLICA_AVAILABILITY = args.replica_availability
LINK_AVAILABILITY = args.link_availability

POBTOG_DIR = f'/app/topologies/{NUM_REPLICAS}-{TOPOLOGY}-10000'
POBTOG_OUT_DIR = f'{POBTOG_DIR}/out/{LINK_AVAILABILITY}-{REPLICA_AVAILABILITY}'
OUT_DIR = f'/app/out'

if Path(f'{POBTOG_OUT_DIR}/regions.csv').exists():
  if args.overwrite:
    print(f'{POBTOG_OUT_DIR}/out/ exists. Overwriting')
  else:
    print(f'{POBTOG_OUT_DIR}/out/ exists. Skipping')
    exit(0)

print(f'[ {TOPOLOGY} | n={NUM_REPLICAS} | A_b={LINK_AVAILABILITY} | A_c={REPLICA_AVAILABILITY} ]')
# ----------------------------------------------------------------------------------------------------





# ----------------------------------------------------------------------------------------------------
nodes = gpd.read_file(f'{POBTOG_DIR}/df_bounds.gpkg')

fix_id = lambda id: id if np.isnan(id) else str(int(id))

nodes['id'] = nodes['id'].astype(str)
nodes['parent_id'] = nodes['parent_id'].apply(fix_id)
nodes['ancestor0'] = nodes['ancestor0'].apply(fix_id)
nodes['ancestor1'] = nodes['ancestor1'].apply(fix_id)
nodes['ancestor2'] = nodes['ancestor2'].apply(fix_id)

nodes = nodes.drop(columns=['pop', 'switch', 'capacity', 'R', 'is_leaf']).rename(columns={'geometry': 'bounds_mp'})
nodes['geometry'] = gpd.points_from_xy(nodes['lon'], nodes['lat'])
nodes = gpd.GeoDataFrame(nodes[['id', 'level', 'parent_id', 'ancestor0', 'ancestor1', 'ancestor2', 'geometry', 'bounds_mp']], geometry='geometry', crs=4326)
# ----------------------------------------------------------------------------------------------------





# ----------------------------------------------------------------------------------------------------
with open(f'{POBTOG_DIR}/graph.pkl', 'rb') as f:
  G = pickle.load(f)

edges = nx.to_pandas_edgelist(G)
edges['source'] = edges['source'].apply(lambda node: node.name.split('_')[0])
edges['target'] = edges['target'].apply(lambda node: node.name.split('_')[0])
edges['source'] = edges['source'].astype(float).apply(fix_id)
edges['target'] = edges['target'].astype(float).apply(fix_id)
edges = edges.merge(nodes, left_on='source', right_on='id', suffixes=['_source', None], how='left').rename(columns={'geometry': 'point_source'})
edges = edges.merge(nodes, left_on='target', right_on='id', suffixes=['_target', None], how='left').rename(columns={'geometry': 'point_target'})
edges = edges.drop(columns=['bandwidth', 'id_target', 'id'])
edges['geometry'] = edges.apply(lambda row: LineString([row['point_source'], row['point_target']]), axis=1)
edges = gpd.GeoDataFrame(edges, geometry='geometry', crs=nodes.crs)
edges['distance_km'] = edges.to_crs(2154).length / 1000
edges = edges.drop(columns=['bounds_mp', 'bounds_mp_target', 'point_source', 'point_target', 'level_target', 'parent_id_target',	'ancestor0_target',	'ancestor1_target',	'ancestor2_target',	'level',	'parent_id',	'ancestor0',	'ancestor1',	'ancestor2'])

print(f'{len(nodes.index)} nodes and {len(edges.index)} edges')
# ----------------------------------------------------------------------------------------------------





# ----------------------------------------------------------------------------------------------------
graph = nx.Graph()
graph.add_edges_from(
  (
    edge.source,
    edge.target,
    {
      'distance': edge.distance_km,
      'availability': LINK_AVAILABILITY ** edge.distance_km
    }
  ) for edge in edges.itertuples(index=False)
)

regions = gpd.GeoDataFrame(nodes[nodes['level'] == 3])
core_replicas = gpd.GeoDataFrame(nodes[nodes['level'] == 0])

print(f'{graph}')
# ----------------------------------------------------------------------------------------------------





# ----------------------------------------------------------------------------------------------------
def path_availability(path):
  return math.prod(
    [
      graph[u][v]["availability"]
      for u, v in zip(path[:-1], path[1:])
    ]
  )

def topology_availability(source, target, cutoff=None):
  key = (source, target)
  if key in known_paths.keys():
    return known_paths[key]
  
  paths = list(nx.all_simple_paths(graph, source, target, cutoff=cutoff))

  result = 1 - math.prod(
    [
      1 - path_availability(path)
      for path in paths
    ]
  )
  known_paths[key] = result
  
  return result

def core_star_center_avail(l0_node):
  # core always available except when all replicas unavailable
  return 1 - (
    # l0 unavailable
    (1 - REPLICA_AVAILABILITY) *
    math.prod(
      [
        # lx is unavailable except when edge 0->x available AND lx available | 1-x
        #      edge 0->x available                        AND lx unavailable 
        1  -   graph[l0_node][other_node]['availability']  *  REPLICA_AVAILABILITY
        for other_node in core_replicas['id'] if other_node != l0_node  
      ]
    )
  )

def core_star_notcenter_avail(l0_node, center_node):
  return 1 - math.prod(
    [
      # l0 unavailable
      1 - REPLICA_AVAILABILITY,
      # center unavailable except when edge and center are available
      1 - graph[l0_node][center_node]['availability'] * REPLICA_AVAILABILITY,
      # lx unavailable except when 0->center and center->x and lx available 
      1 - graph[l0_node][center_node]['availability'] * (
        1 - math.prod(
          [
            1 - graph[center_node][other_node]['availability'] * REPLICA_AVAILABILITY
            for other_node in core_replicas['id']
            if other_node != l0_node and other_node != center_node
          ]
        )
      )
    ]
  )

def core_ring_avail(l0_node):
  return 1 - (1 - REPLICA_AVAILABILITY) * math.prod(
    [
      1 - REPLICA_AVAILABILITY *
      (
        1 - math.prod(
          [
            1 - path_availability(path)
            for path in nx.all_simple_paths(graph, l0_node, other_node)
          ]
        )
      ) 
      for other_node in core_replicas['id'] if other_node != l0_node
    ]
  )

core_avail = {}

def core_network_availability(l0_node):
  if l0_node in core_avail.keys():
    return core_avail[l0_node]
  
  if REPLICA_AVAILABILITY == 1:
    result = 1
  
  elif NUM_REPLICAS == 1:
    result = REPLICA_AVAILABILITY

  elif TOPOLOGY == 'star':
    neighbors = { n for n in graph.neighbors(l0_node) if n in core_replicas['id'].to_list() }
    if len(neighbors) > 1: # at least one node to center of star, if more -> l0 is center
      result = core_star_center_avail(l0_node)
    else:
      result = core_star_notcenter_avail(l0_node, neighbors.pop())
  
  elif TOPOLOGY == 'ring':
    result = core_ring_avail(l0_node)

  elif TOPOLOGY == 'full':
    result = core_star_center_avail(l0_node)
  
  core_avail[l0_node] = result
  return result


def end_to_end_availability(row):
  l3_node = row['id']
  l2_node = row['ancestor2']
  l1_node = row['ancestor1']
  l0_node = row['ancestor0']

  an_avail = topology_availability(l3_node, l2_node)
  tnl_avail = topology_availability(l2_node, l1_node)
  tnu_avail = topology_availability(l1_node, l0_node)
  cn_avail = core_network_availability(l0_node)
  
  return an_avail * tnl_avail * tnu_avail * cn_avail

# print(f'Loading precomputed paths...')
# precomputed_path_avails = pd.read_csv(f'/app/out/precomputed_paths.csv')
known_paths = {} #{
#   (str(row.id), str(row.parent_id)): row.path_avail
#   for row in precomputed_path_avails.itertuples(index=False)
# }
# nx_auxiliary = build_auxiliary_edge_connectivity(graph)
# nx_residual = build_residual_network(nx_auxiliary, "capacity")

print(f'Computing core availability...')
regions['core_availability'] = regions.apply(end_to_end_availability, axis=1)

# ----------------------------------------------------------------------------------------------------





# ----------------------------------------------------------------------------------------------------
mean = regions['core_availability'].mean()
iqr = regions['core_availability'].agg(lambda x: x.quantile(0.75) - x.quantile (0.25))

print(f'[ mean={mean} | iqr={iqr} ]')
# TODO: create violin plot with a violin per distribution factor (n=5,10,20) and 9751 points per violin
# ----------------------------------------------------------------------------------------------------





# ----------------------------------------------------------------------------------------------------
print('Storing results...')

result = pd.DataFrame({
  'link_availability': [LINK_AVAILABILITY],
  'replica_availability': [REPLICA_AVAILABILITY],
  'topology':      [TOPOLOGY],
  'num_replicas':  [NUM_REPLICAS],
  'mean':          [mean],
  'iqr':           [iqr]
})

if Path(f'{OUT_DIR}/core_availability.csv').exists():
  out_csv = pd.read_csv(f'{OUT_DIR}/core_availability.csv')
  if args.overwrite:
    mask = (
      (out_csv["link_availability"] == LINK_AVAILABILITY) &
      (out_csv["replica_availability"] == REPLICA_AVAILABILITY) &
      (out_csv["topology"] == TOPOLOGY) &
      (out_csv["num_replicas"] == NUM_REPLICAS)
    )
    if mask.sum() == 1:
      print('Force flag detected -> overwriting')
      out_csv.loc[
        mask,
        ["mean", "iqr"]
      ] = [mean, iqr]
    else:
      if mask.sum() == 0:
        print('Force flag detected but no row to overwrite -> appending')
        pd.concat([out_csv,result], ignore_index=True).to_csv(f'{OUT_DIR}/core_availability.csv', index=False)
      else:
        print('Force flag detected but too many rows to overwrite -> aborting')
        exit(1)
  else:
    print('No force flag -> appending')
    pd.concat([out_csv,result], ignore_index=True).to_csv(f'{OUT_DIR}/core_availability.csv', index=False)
else:
  print('No file exists -> creating')
  result.to_csv(f'{OUT_DIR}/core_availability.csv', index=False)

Path(POBTOG_OUT_DIR).mkdir(exist_ok=True, parents=True)
nodes.drop(columns=['bounds_mp']).to_file(f'{POBTOG_OUT_DIR}/nodes.geojson')
nodes.drop(columns=['bounds_mp', 'geometry']).to_csv(f'{POBTOG_OUT_DIR}/nodes.csv', index=False)
regions.drop(columns=['bounds_mp', 'geometry']).to_csv(f'{POBTOG_OUT_DIR}/regions.csv', index=False)
edges.to_file(f'{POBTOG_OUT_DIR}/edges.geojson')

t1 = time.time()
print(f'Done in {t1-t0}')
# ----------------------------------------------------------------------------------------------------