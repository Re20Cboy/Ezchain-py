# Ezchain - A Decentralized Scale-out Blockchain Ledger System for Web3.0

[![arXiv](https://img.shields.io/badge/arXiv-2312.00281-b31b1b.svg)](https://arxiv.org/abs/2312.00281)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Ezchain is a novel decentralized "scale-out" ledger system designed for Web3.0 that enables blockchain technology to support ledger applications in large-scale fully decentralized networks without compromising security and decentralization.

## 🌟 Key Features

- **🚀 Scalability**: System throughput is directly proportional to node size, not constrained by bandwidth resources
- **💻 Hardware Compatibility**: Designed for consumer-grade hardware, supporting storage, computation, and verification requirements
- **⚡ Efficient Transaction Confirmation**: Maintains transaction confirmation delays within one minute
- **🔐 Decentralization and Security**: Strict adherence to decentralization principles with robust security

## 📚 Research Paper

This project is based on the research paper published on arXiv: [A Scale-out Decentralized Blockchain Ledger System for Web3.0](https://arxiv.org/abs/2312.00281)

### Citation

```bibtex
@misc{xue2023scaleout,
    title={A Scale-out Decentralized Blockchain Ledger System for Web3.0},
    author={Lide Xue and Wei Yang and Wei Li},
    year={2023},
    eprint={2312.00281},
    archivePrefix={arXiv},
    primaryClass={cs.CR}
}
```

## 🚀 Quick Start

Ezchain provides two simulation modes:

1. **NON-DST Mode**: Centralized simulation for experimental evaluation and metrics collection
2. **DST Mode**: Distributed simulation with individual node processes (under development)

### 📋 Prerequisites

- Python 3.8 or higher
- pip package manager
- Git

### 🔧 Installation

```bash
# Clone the repository
git clone https://github.com/Re20Cboy/Ezchain-py.git

# Navigate to the project directory
cd Ezchain-py

# Install dependencies
pip install -r requirements.txt
```

## 🎯 Running Tutorials

### Tutorial 1: NON-DST Mode (Centralized Simulation)

This mode runs all nodes in a centralized manner for efficient simulation and metrics collection.

#### Step 1: Configure Parameters

Edit `const.py` to adjust simulation parameters:

```python
# Network configuration
NODE_NUM = 5                    # Number of consensus nodes
ACCOUNT_NUM = 5                 # Number of account nodes
SAMPLE_NEIGHBORS_NUM = 30       # P2P neighbor connections

# Simulation parameters
SIMULATE_ROUND = 10            # Mining rounds
BANDWIDTH = 1024 * 1024 * 1    # Network bandwidth (bytes)
HASH_DIFFICULTY = 0.0005       # Mining difficulty

# Performance parameters
NODE_ACCOUNT_DELAY = 1.5       # Node-to-account delay (seconds)
ACC_ACC_DELAY = 1.5           # Account-to-account delay (seconds)
PICK_TXNS_NUM = 12             # Transactions per block
```

#### Step 2: Run Simulation

```bash
# Run the centralized simulation
python3 Ezchain_simulate.py

# Alternatively
./Ezchain_simulate.py
```

#### Step 3: Monitor Output

The simulation will display:
- Blockchain creation and mining progress
- Transaction propagation and validation
- Network communication metrics
- Performance statistics

### Tutorial 2: DST Mode (Distributed Simulation)

This mode runs individual nodes as separate processes with real network communication.

#### Step 1: Configure DST Parameters

Edit `const.py` for distributed mode:

```python
# DST-specific configuration
DST_NODE_NUM = 2               # Number of consensus nodes in DST mode
DST_ACC_NUM = 2                # Number of account nodes in DST mode
MAX_PACKAGES = 2               # Transaction pool threshold
ONE_HASH_TIME = 0.5            # Hash calculation time
ONE_HASH_SUCCESS_RATE = 0.03   # Mining success rate
```

#### Step 2: Run Distributed Simulation

```bash
# Launch the distributed system
python3 DST_ENTRY_POINT.py

# Alternatively
./DST_ENTRY_POINT.py
```

## ⚙️ Configuration Reference

### Key Parameters in `const.py`

| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `NODE_NUM` | Number of consensus nodes (NON-DST) | 5 |
| `ACCOUNT_NUM` | Number of account nodes (NON-DST) | 5 |
| `DST_NODE_NUM` | Number of consensus nodes (DST) | 2 |
| `DST_ACC_NUM` | Number of account nodes (DST) | 2 |
| `SIMULATE_ROUND` | Number of mining rounds | 10 |
| `BANDWIDTH` | Network bandwidth in bytes | 1MB |
| `HASH_DIFFICULTY` | Mining success probability | 0.0005 |
| `PICK_TXNS_NUM` | Transactions per block | 12 |
| `SAMPLE_NEIGHBORS_NUM` | P2P connections per node | 30 |

### Performance Tuning

- **For faster simulation**: Reduce `NODE_NUM`, `ACCOUNT_NUM`, and `SIMULATE_ROUND`
- **For realistic testing**: Increase `BANDWIDTH` and adjust `HASH_DIFFICULTY`
- **For network testing**: Modify `NODE_ACCOUNT_DELAY` and `ACC_ACC_DELAY`

## 🏗️ Project Structure

```
Ezchain-py/
├── Ezchain_simulate.py          # Main simulation script (NON-DST)
├── DST_ENTRY_POINT.py           # Distributed system entry point (DST)
├── const.py                     # Configuration parameters
├── requirements.txt             # Python dependencies
├── blockchain.py                # Blockchain core implementation
├── node.py                      # Node logic
├── network.py                   # Network communication
├── transaction.py               # Transaction handling
├── p2p_network.py              # P2P network layer
└── website/                    # Web interface (optional)
```

## 🧪 Testing

Run the test suite to verify functionality:

```bash
python3 test.py
```

## 📊 Expected Output

The simulation produces:
- Blockchain creation and mining logs
- Transaction propagation statistics
- Network performance metrics
- Consensus mechanism validation results
- Throughput and latency measurements
