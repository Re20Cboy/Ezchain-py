# Ezchain-A DECENTRALIZED SCALE-OUT BLOCKCHAIN LEDGER SYSTEM FOR WEB3.0

The development of underlying technologies in blockchain mostly revolves around a difficult problem: how to enhance the performance of the system and reduce various costs of nodes (such as communication, storage and verification) without compromising the system's security and decentralization. Various layer-1 and layer-2 protocols have provided excellent solutions for this challenge. However, they cannot yet be considered as a "silver bullet". This paper proposes EZchain---a novel decentralized "scale-out" ledger system designed for web3.0, aiming to enable blockchain technology to truly support ledger applications in large-scale fully decentralized networks. Without compromising security and decentralization, EZchain successfully accomplishes the following milestones: 1) Scalability: The theoretical throughput of EZchain can be infinitely expanded, nearly unaffected by bandwidth and other resource constraints. 2) Consumer-Grade Hardware Compatibility: EZchain is designed to be compatible with consumer-grade hardware, supporting storage, computation, and verification requirements. 3) Efficient Transaction Confirmation: EZchain strives to maintain transaction confirmation delays within one minute.
Our prototype experiment demonstrates that under typical daily bandwidth network conditions, EZchain's performance in all aspects approaches that of the accounts in centralized payment systems. This provides a solid infrastructure for realizing mobile payments in web3.0.

## Highlights

* Scalability: System throughput is directly proportional to node size, not constrained by bandwidth resources.
* Hardware Compatibility: Designed for consumer-grade hardware, supporting necessary storage, computation, and verification requirements.
* Efficient Transaction Confirmation: Strives to keep transaction confirmation delays within one minute.
* Decentralization and Security: Maintains strict adherence to decentralization principles and ensures robust security​​.

## Running simulation

### Environment setup

```
git clone xxx.git

cd xxx

pip install -r requirements.txt
```

### Useful configuration options

These are some critical configuration options in the project, which can be modified in the `Const.py` file.

* SAMPLE_NEIGHBORS_NUM controls the neighbors' number of each p2p node (include consensus and account).
* NODE_ACCOUNT_DELAY and ACC_ACC_DELAY control the delay of consensus node to account node and the delay of account node to account node (referring here to queuing delays, excluding transmission times).
* NODE_NUM controls number of consensus nodes.
* ACCOUNT_NUM controls number of account nodes.
* PICK_TXNS_NUM controls the upper limit of transactions packaged at one round (block), it should theoretically not exceed ACCOUNT_NUM^2/2.
* SIMULATE_ROUND controls the mining round.
* BANDWIDTH controls the network's bandwidth.
* HASH_DIFFICULTY controls the mining difficulty, i.e., the probability of successful mining in one hash computation.
* HASH_POWER controls the hash computing power, indicating the number of hashes computation performed per second.
* GENESIS_SENDER and GENESIS_MINER_ID represent genesis sender's address and genesis miner's ID.

### Run

```
python3 Ezchain_simulate.py
```

or

```
chmod +x Ezchain_simulate.py
./Ezchain_simulate.py
```
