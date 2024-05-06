# VLM for ARTA

## Prerequisites

Before you begin, ensure the following tools are installed on your system:
- **Git**
- **Anaconda or Miniconda**

## Installation

Follow these step-by-step instructions to set up your environment for VLM for ARTA.

### Clone the Repository

Clone the repository to your local machine using this command, and follow the instructions at https://github.com/Vision-CAIR/MiniGPT-4 to properly set up and deploy the models:
 

```bash
git clone https://github.com/Vision-CAIR/MiniGPT-4.git
cd MiniGPT-4
```


### Environment Setup
Create and activate the Conda environment using the environment.yml provided in the repository:

```bash
conda env create -f environment.yml
conda activate minigptv
pip install beautifulsoup4
pip install lxml
```

### Data Preparation
Place the `dataset_pre.py` script in the MiniGPT-4 directory. This script preprocesses your dataset:

```bash
python dataset_pre.py
```
Default JSON files are saved under the json_file folder. Additionally, when running the script, make sure to modify the data paths on lines 40 and 48 to reflect the locations where your data is stored. This ensures the script correctly accesses and processes your specific dataset.

### Running Inference

Ensure the `inference.py` script is placed in the MiniGPT-4 directory. Execute the script to perform inference on your data:

```bash
python inference.py
```

Make sure to change the path on line 145 of the inference.py script to your own JSON folder path. This adjustment ensures the script correctly accesses the JSON files needed for processing your data.