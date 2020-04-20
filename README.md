# Install
- Create an [Azure account](https://azure.microsoft.com/en-us/free/).
- Download and install [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest).
- Download and install [conda](https://docs.anaconda.com/anaconda/install/).
- Download this [repository](https://github.com/ewyuanzhang/forza_iot_demo).
- Open an `Anaconda Prompt`, change the directory into this repository, and run the commands below.
- Create conda environment and install the dependencies:
  - `conda env create -f environment.yml`
- Activate the environment:
  - `conda activate forza_iot`
- Install Azure IoT extension:
  - `az extension add --name azure-cli-iot-ext`
- Setup Azure IoT Hub and get the connection string:
  - `python setup_iothub.py`

# Run
- Activate the environment:
  - `conda activate forza_iot`
- Run `main.py`
  - `python main.py`