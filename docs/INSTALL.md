# Installation

WHAM has been implemented and tested on Ubuntu 20.04 and 22.04 with python = 3.9. We provide [anaconda](https://www.anaconda.com/) environment to run WHAM as below.

```bash
# Clone the repo
git clone https://github.com/lithiumice/WHAM.git --recursive
cd WHAM/

# Create Conda environment
conda create -n wham python=3.9 -y
conda activate wham

# just want to use same conda environment as TRAM, this should work...
# conda activate tram

# Install PyTorch libraries
# conda install pytorch==1.11.0 torchvision==0.12.0 torchaudio==0.11.0 cudatoolkit=11.3 -c pytorch
conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia -y


# Install PyTorch3D (optional) for visualization
conda install -c fvcore -c iopath -c conda-forge fvcore iopath -y
# pip install pytorch3d -f https://dl.fbaipublicfiles.com/pytorch3d/packaging/wheels/py39_cu113_pyt1110/download.html

# Install WHAM dependencies
pip install -r requirements.txt

# Install ViTPose
pip install -v -e third-party/ViTPose

# Install DPVO

### <====== Prepare for DPVO
# looking for alternatives:
# https://data.pyg.org/whl/torch-2.1.2%2Bcu121.html


# refer: https://stackoverflow.com/questions/67285115/building-wheels-for-torch-sparse-in-colab-takes-forever
# pip install https://data.pyg.org/whl/torch-2.1.0%2Bcu121/torch_scatter-2.1.2%2Bpt21cu121-cp39-cp39-linux_x86_64.whl
pip install -q torch-scatter -f https://data.pyg.org/whl/torch-2.3.0%2Bcu121.html
pip install -q torch-sparse -f https://data.pyg.org/whl/torch-2.3.0%2Bcu121.html
# conda install pytorch-scatter -c rusty1s

# conda install pytorch-scatter=2.0.9 -c rusty1s
# conda install cudatoolkit-dev=11.3.1 -c conda-forge

# # ONLY IF your GCC version is larger than 10
# conda install -c conda-forge gxx=9.5

cd third-party/DPVO

if [ ! -d "thirdparty/eigen-3.4.0/" ]; then
wget https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.zip
unzip eigen-3.4.0.zip -d thirdparty && rm -rf eigen-3.4.0.zip
fi

pip install .
cd ../..

# download all model weights
git clone https://huggingface.co/lithiumice/WHAM data
ln -s data/checkpoints checkpoints
ln -s data/dataset dataset


# # Backup
# # mkdir -p datasets
# # ln -s /data/hualin/EMDB dataset/EMDB
# ln -s /data/hualin/WHAM_dataset dataset

# cd dataset/
# gdown --folder 13T2ghVvrw_fEk3X-8L0e6DVSYx_Og8o3
# # this will download to `dataset/parsed_data`
```