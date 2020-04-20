*The repository is based on [holgerkenn/Forza-IoT-Relay](https://github.com/holgerkenn/Forza-IoT-Relay)*
# Pre-requisite
To run this, you need:
- An XBox One (but a powerful PC might also do)
- Forza Horizon 4 Standard or higher (the demo version lacks the telemetry output)
- Another PC/board to receive telemetry
- An [Azure account](https://azure.microsoft.com/en-us/free/)

# Set up Forza Horizon 4 telemetry output
1. Start the game, play through the first run experience if you haven't yet.
1. Press the hamburger key (three horizontal lines) on the controler
1. Go to settings
1. Go to HUD and Gameplay
1. Scroll down to the bottom
1. Enable telemerty/data output
1. Enter IP address of the PC/board (press x on controller to edit)
1. Enter `6669` as ip port (press x on controller to edit)
1. Return to game and drive. The display of the MXChip dev kit should now display timestamp, speed, RPM and gear.

# Install
On the PC/board to receive telemetry:
- Download and install [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest).
- Download and install [conda](https://docs.anaconda.com/anaconda/install/).
- Download this [repository](https://github.com/ewyuanzhang/forza_iot_demo).
- Change the configuration in `config/forza_config.json` if needed.
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