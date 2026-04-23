import argparse
import hashlib
import json
from pathlib import Path
from src.demo_logic_calculation import run_calculation_pipeline

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
    '--population-threshold',
    type=int,
    default=10000,
    help="Max. number of inhabitants per Voronoi cell (default: 10000)",
  )

  return parser.parse_args()

args = parse_args()

folder_path = Path("topologies") / f"{args.num_replicas}-{args.topology}-{args.population_threshold}"

folder_path.mkdir(parents=True, exist_ok=True)
df_path = folder_path / "df.gpkg"
json_path = folder_path / "result.json"
folium_path = folder_path / "result_folium_map.html"

result_folder = folder_path
  
if folder_path.exists() and folium_path.exists():
  print(f'{result_folder} exists... skip.')
  exit(0)

config = {
  "country": "FRA",
  "DT_max_capacity": args.population_threshold,
  "num_layers": 4,
  "num_lower_layer_nodes": [
      args.num_replicas,
      50,
      400
  ],
  "connection": [
      args.topology,
      "star",
      "star",
      "ring"
  ],
  "link_capacity": [
      400000000000.0,
      100000000000.0,
      10000000000.0,
      1000000000.0
  ],
  "redundancy": [
      1,
      1,
      1,
      1
  ],
  "augmentation": None,
  "save_to_json": False,
  "save_to_gpkg": True,
  "save_to_html": True
}


config_hash = hashlib.md5(
  json.dumps(
    {
      k: config[k]
      for k in [
        'country',
        'num_layers',
        'num_lower_layer_nodes',
        'connection',
        'link_capacity',
        'redundancy'
      ]
    },
    sort_keys=False
  ).encode()
).hexdigest()[:8]

config.update({
  'config_hash': f"{config['country']}_{config['num_layers']}L_{config_hash}",
  "df_output": str(df_path),
  "json_output": str(json_path),
  "folium_output": str(folium_path)
})

print(f'generating {result_folder} ...')
run_calculation_pipeline(config)
print('done')
