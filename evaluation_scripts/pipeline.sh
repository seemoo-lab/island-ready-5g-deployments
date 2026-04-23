#!/bin/bash
set -e

# Load env
set -o allexport
source .env
set +o allexport

# Convert lists into arrays
IFS=',' read -ra GEN_REPLICA_FACTOR_ARRAY <<< "$GEN_REPLICA_FACTOR_ARRAY"
IFS=',' read -ra GEN_TOPO_ARRAY <<< "$GEN_TOPO_ARRAY"
IFS=',' read -ra EVAL_REPLICA_FACTOR_ARRAY <<< "$EVAL_REPLICA_FACTOR_ARRAY"
IFS=',' read -ra EVAL_A_TOPO_ARRAY <<< "$EVAL_A_TOPO_ARRAY"
IFS=',' read -ra EVAL_A_REPLICA_AVAIL <<< "$EVAL_A_REPLICA_AVAIL"
IFS=',' read -ra EVAL_A_LINK_AVAIL <<< "$EVAL_A_LINK_AVAIL"
IFS=',' read -ra EVAL_B_TOPO_ARRAY <<< "$EVAL_B_TOPO_ARRAY"
IFS=',' read -ra EVAL_B_REPLICA_AVAIL <<< "$EVAL_B_REPLICA_AVAIL"
IFS=',' read -ra EVAL_B_LINK_AVAIL <<< "$EVAL_B_LINK_AVAIL"
IFS=',' read -ra EVAL_C_TOPO_ARRAY <<< "$EVAL_C_TOPO_ARRAY"
IFS=',' read -ra EVAL_C_REPLICA_AVAIL <<< "$EVAL_C_REPLICA_AVAIL"
IFS=',' read -ra EVAL_C_LINK_AVAIL <<< "$EVAL_C_LINK_AVAIL"

# Build images
docker build -f generation/Dockerfile --cpu-quota=${CPU_QUOTA} -t ${GEN_IMAGE_NAME} .
docker build -f evaluation/Dockerfile --cpu-quota=${CPU_QUOTA} -t ${EVAL_IMAGE_NAME} .
docker build -f plotting/Dockerfile --cpu-quota=${CPU_QUOTA} -t ${PLOT_IMAGE_NAME} .


for topo in "${GEN_TOPO_ARRAY[@]}"; do
  for num_replicas in "${GEN_REPLICA_FACTOR_ARRAY[@]}"; do
    echo "generating topology [num_replicas=$num_replicas, topology=$topo] ..."
    
    output_file="${TOPOLOGIES_DIR}/${num_replicas}-${topo}-10000/result_folium_map.html"

    if [[ -f "$output_file" ]]; then
      echo "exists."
      continue
    fi

    docker rm ${GEN_CONTAINER_NAME} 2>/dev/null || true
    docker run \
      -v ${DATA_DIR}:/app/data \
      -v ${TOPOLOGIES_DIR}:/app/topologies \
      --name ${GEN_CONTAINER_NAME} \
      ${GEN_IMAGE_NAME} \
      --num-replicas ${num_replicas} \
      --topology ${topo}
    echo "done."
  done
done
      

for num_replicas in "${EVAL_REPLICA_FACTOR_ARRAY[@]}"; do
  for topo in "${EVAL_A_TOPO_ARRAY[@]}"; do
    for link_avail in "${EVAL_A_LINK_AVAIL[@]}"; do
      for replica_avail in "${EVAL_A_REPLICA_AVAIL[@]}"; do
        
        output_file="${TOPOLOGIES_DIR}/${num_replicas}-${topo}-10000/out/${link_avail}-${replica_avail}/regions.csv"

        if [[ -f "$output_file" ]]; then
          echo "${output_file} exists."
          continue
        else
          echo "${output_file} does not exist."
          echo "evaluating availability [num_replicas=$num_replicas, topology=$topo, link_avail=$link_avail, replica_avail=$replica_avail] ..."
          docker rm ${EVAL_CONTAINER_NAME} 2>/dev/null || true
          docker run \
            -v ${TOPOLOGIES_DIR}:/app/topologies \
            -v ${EVAL_OUTPUT_DIR}:/app/out \
            --name ${EVAL_CONTAINER_NAME} \
            ${EVAL_IMAGE_NAME} \
            --num-replicas ${num_replicas} \
            --topology ${topo} \
            --link-availability ${link_avail} \
            --replica-availability ${replica_avail}
          echo "done."
        fi
      done
    done
  done

  for topo in "${EVAL_B_TOPO_ARRAY[@]}"; do
    for link_avail in "${EVAL_B_LINK_AVAIL[@]}"; do
      for replica_avail in "${EVAL_B_REPLICA_AVAIL[@]}"; do
        echo "evaluating availability [num_replicas=$num_replicas, topology=$topo, link_avail=$link_avail, replica_avail=$replica_avail] ..."
        docker rm ${EVAL_CONTAINER_NAME} 2>/dev/null || true
        docker run \
          -v ${TOPOLOGIES_DIR}:/app/topologies \
          -v ${EVAL_OUTPUT_DIR}:/app/out \
          --name ${EVAL_CONTAINER_NAME} \
          ${EVAL_IMAGE_NAME} \
          --num-replicas ${num_replicas} \
          --topology ${topo} \
          --link-availability ${link_avail} \
          --replica-availability ${replica_avail}
        echo "done."
      done
    done
  done

  for topo in "${EVAL_C_TOPO_ARRAY[@]}"; do
    for link_avail in "${EVAL_C_LINK_AVAIL[@]}"; do
      for replica_avail in "${EVAL_C_REPLICA_AVAIL[@]}"; do
        echo "evaluating availability [num_replicas=$num_replicas, topology=$topo, link_avail=$link_avail, replica_avail=$replica_avail] ..."
        docker rm ${EVAL_CONTAINER_NAME} 2>/dev/null || true
        docker run \
          -v ${TOPOLOGIES_DIR}:/app/topologies \
          -v ${EVAL_OUTPUT_DIR}:/app/out \
          --name ${EVAL_CONTAINER_NAME} \
          ${EVAL_IMAGE_NAME} \
          --num-replicas ${num_replicas} \
          --topology ${topo} \
          --link-availability ${link_avail} \
          --replica-availability ${replica_avail}
        echo "done."
      done
    done
  done
done

echo "plotting figures 8a, 8b, 8c, 6a, 6b, 6c ..."

docker rm ${PLOT_CONTAINER_NAME} 2>/dev/null || true
docker run \
  -v ${EVAL_OUTPUT_DIR}:/app/data \
  -v ${TOPOLOGIES_DIR}:/app/topologies \
  -v ${PLOT_OUTPUT_DIR}:/app/out \
  --name ${PLOT_CONTAINER_NAME} \
  ${PLOT_IMAGE_NAME}

echo "done."