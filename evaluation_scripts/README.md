# Evaluation Scripts

This directory contains Docker images to generate topologies, evaluate availabilities, and plot Figures 6 and 8 of our paper.


### Setup

```zsh
# (A): Clone the repository (with submodules)
git clone --recurse-submodules https://github.com/seemoo-lab/island-ready-5g-deployments.git

# (B): If you already cloned without submodules:
git submodule update --init --recursive # from the project root
```

### Evaluation

```zsh
cd evaluation_scripts/
vi .env # update the paths for your environment
./pipeline.sh
```