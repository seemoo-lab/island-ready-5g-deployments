import contextily as ctx
import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import pickle
import seaborn as sns
from shapely.geometry import LineString

from matplotlib import scale as mscale
from matplotlib import transforms as mtransforms
from matplotlib.ticker import FixedFormatter, FixedLocator
from numpy import ma

class CloseToOne(mscale.ScaleBase):
  name = 'close_to_one'

  def __init__(self, axis, **kwargs):
    mscale.ScaleBase.__init__(self, axis)
    self.nines = kwargs.get('nines', 7)

  def get_transform(self):
    return self.Transform(self.nines)

  def set_default_locators_and_formatters(self, axis):
    axis.set_major_locator(FixedLocator(
      np.array([1-10**(-k) for k in range(1+self.nines)])))
    axis.set_major_formatter(FixedFormatter(
      [str(1-10**(-k)) for k in range(1+self.nines)]))


  def limit_range_for_scale(self, vmin, vmax, minpos):
    return vmin, min(1 - 10**(-self.nines), vmax)

  class Transform(mtransforms.Transform):
    input_dims = 1
    output_dims = 1
    is_separable = True

    def __init__(self, nines):
      mtransforms.Transform.__init__(self)
      self.nines = nines

    def transform_non_affine(self, a):
      masked = ma.masked_where(a > 1-10**(-1-self.nines), a)
      if masked.mask.any():
        return -ma.log10(1-a)
      else:
        return -np.log10(1-a)

    def inverted(self):
      return CloseToOne.InvertedTransform(self.nines)

  class InvertedTransform(mtransforms.Transform):
    input_dims = 1
    output_dims = 1
    is_separable = True

    def __init__(self, nines):
      mtransforms.Transform.__init__(self)
      self.nines = nines

    def transform_non_affine(self, a):
      return 1. - 10**(-a)

    def inverted(self):
      return CloseToOne.Transform(self.nines)

mscale.register_scale(CloseToOne)

sns.set_theme(style='darkgrid')
plt.rcParams.update(
  {
    'figure.figsize': [6.8, 3.8],
    # 'text.usetex': True,
    'font.size': 28,
    'font.family': 'serif'
  }
)

avail = pd.read_csv('data/core_availability.csv')

# --------------------
# Figure 8a
# --------------------
plt.yscale('close_to_one', nines=8)
ax = sns.lineplot(
  avail[
    (avail['replica_availability'] == .99999) &
    (avail['topology'] == 'star') &
    (avail['link_availability'].isin([0.999, 0.9999, 0.99999, 0.999999]))
  ],
  x='num_replicas',
  y='mean',
  hue='link_availability',
  style='link_availability',
  legend='full'
)
plt.xlabel('Core replication factor')
plt.ylabel('End-to-end availability (mean)')
ax.legend(
  title="Link availability per km",
  ncols=2
)
plt.tight_layout()
plt.savefig('out/sns-link-avail.pdf')
plt.close()


# --------------------
# Figure 8b
# --------------------
plt.yscale('close_to_one', nines=5)
ax = sns.lineplot(
  avail[avail['replica_availability'].isin([0.5, 0.6, 0.7, 0.8, 0.9])],
  x='num_replicas',
  y='mean',
  hue='replica_availability',
  style='replica_availability',
  legend='full',
  errorbar=None
)
plt.xlabel('Core replication factor')
plt.ylabel('End-to-end availability (mean)')
ax.legend(
  # unique.values(),
  # unique.keys(),
  title="Core replica availability",
  ncols=3
)
plt.tight_layout()
plt.savefig('out/sns-replica-avail-star.pdf')
plt.close()




# --------------------
# Figure 8c
# --------------------
dfs = []
for t in ['star', 'ring']:
  for n in [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]:
    data = pd.read_csv(f'topologies/{n}-{t}-10000/out/0.99999-0.99999/regions.csv')
    data['network_topology'] = t
    data['replication_factor'] = n
    dfs.append(data)

data = pd.concat(dfs, ignore_index=True)
plt.yscale('close_to_one', nines=8)
ax = sns.lineplot(
  data=data,
  x="replication_factor",
  y="core_availability",
  hue="network_topology",
  style="network_topology",
  errorbar=('pi',50)
)

plt.xlabel('Core replication factor')
plt.ylabel('End-to-end availability (mean,iqr)')
ax.legend(
  title="Core network topology",
  ncols=2
)

plt.tight_layout()
plt.savefig('out/sns-topology-avail.pdf')






nodes = gpd.read_file('/app/topologies/5-star-10000/df_bounds.gpkg')
fix_id = lambda id: id if np.isnan(id) else str(int(id))
nodes['id'] = nodes['id'].astype(str)
nodes['parent_id'] = nodes['parent_id'].apply(fix_id)
nodes['ancestor0'] = nodes['ancestor0'].apply(fix_id)
nodes['ancestor1'] = nodes['ancestor1'].apply(fix_id)
nodes['ancestor2'] = nodes['ancestor2'].apply(fix_id)

nodes = nodes.drop(columns=['pop', 'switch', 'capacity', 'R', 'is_leaf']).rename(columns={'geometry': 'bounds_mp'})
nodes['geometry'] = gpd.points_from_xy(nodes['lon'], nodes['lat'])
nodes = gpd.GeoDataFrame(nodes[['id', 'level', 'parent_id', 'ancestor0', 'ancestor1', 'ancestor2', 'geometry', 'bounds_mp']], geometry='geometry', crs=4326)

with open('/app/topologies/5-star-10000/graph.pkl', 'rb') as f:
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




nodes = nodes.to_crs(epsg=3857)
edges = edges.to_crs(epsg=3857)

minx, miny, maxx, maxy = nodes.total_bounds

pad_x = (maxx - minx) * 0.02
pad_y = (maxy - miny) * 0.02

minx -= pad_x
maxx += pad_x
miny -= pad_y
maxy += pad_y





# --------------------
# Figure 6a
# --------------------
fig, ax = plt.subplots(figsize=(9, 11))
edges[(edges['level'] == 3) | (edges['level_target'] == 3)].plot(
  ax=ax,
  color='#2ca02c',
  # markersize=1
)
nodes[nodes['level'] == 2].plot(
  ax=ax,
  color='#1f77b4',
  # marker='o',
  # markersize=20
)
ax.set_xlim(minx, maxx)
ax.set_ylim(miny, maxy)
ctx.add_basemap(
  ax,
  source=ctx.providers.CartoDB.Positron,
  zoom=6
)

ax.set_axis_off()
plt.tight_layout()
plt.savefig("/app/out/ctx-access.pdf", bbox_inches="tight")




# --------------------
# Figure 6b
# --------------------
fig, ax = plt.subplots(figsize=(9, 11))
edges[
    ((edges['level'] == 2) & (edges['level_target'] == 2)) |
    ((edges['level'] == 2) & (edges['level_target'] == 1)) |
    ((edges['level'] == 1) & (edges['level_target'] == 2))
  ].plot(
  ax=ax,
  color="#1f77b4",
  # markersize=1
)
nodes[(nodes['level'] == 2)].plot(
  ax=ax,
  color="#1f77b4",
  # marker='o',
  # markersize=20
)
edges[
    ((edges['level'] == 1) & (edges['level_target'] == 1)) |
    ((edges['level'] == 1) & (edges['level_target'] == 0)) |
    ((edges['level'] == 0) & (edges['level_target'] == 1))
  ].plot(
  ax=ax,
  color="#9467bd",
  # markersize=1
)
nodes[(nodes['level'] == 1)].plot(
  ax=ax,
  color='#9467bd',
  # marker='o',
  # markersize=20
)
ax.set_xlim(minx, maxx)
ax.set_ylim(miny, maxy)
ctx.add_basemap(
  ax,
  source=ctx.providers.CartoDB.Positron,
  zoom=6
)

ax.set_axis_off()
plt.tight_layout()
plt.savefig("/app/out/ctx-transport.pdf", bbox_inches="tight")





# --------------------
# Figure 6c
# --------------------
fig, ax = plt.subplots(figsize=(9, 11))
edges[
    ((edges['level'] == 0) & (edges['level_target'] == 0))
  ].plot(
  ax=ax,
  color="#333333",
  # markersize=1
)
nodes[(nodes['level'] == 0)].plot(
  ax=ax,
  color='#333333',
  # marker='o',
  # markersize=20
)
ax.set_xlim(minx, maxx)
ax.set_ylim(miny, maxy)
ctx.add_basemap(
  ax,
  source=ctx.providers.CartoDB.Positron,
  zoom=6
)

ax.set_axis_off()
plt.tight_layout()
plt.savefig("/app/out/ctx-core.pdf", bbox_inches="tight")
