
```bash
conda activate tram


pip install -v -e third-party/ViTPose



cd third-party/DPVO
wget https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.zip
unzip eigen-3.4.0.zip -d thirdparty && rm -rf eigen-3.4.0.zip


conda install pytorch-scatter=2.0.9 -c rusty1s
# conda install cudatoolkit-dev=11.3.1 -c conda-forge
# conda install -c conda-forge gxx=9.5   # Only if GCC version is greater than 10.

pip install .


# mkdir -p datasets
# ln -s /data/hualin/EMDB dataset/EMDB
ln -s /data/hualin/WHAM_dataset dataset

cd dataset/
gdown --folder 13T2ghVvrw_fEk3X-8L0e6DVSYx_Og8o3
# this will download to `dataset/parsed_data`
```