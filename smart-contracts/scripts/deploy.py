from scripts.utils.utils import get_account, get_verify, get_contract
from brownie import ETHPool, ETHPoolV2, ETHPoolV3


def deploy_ethpool():
    print("Deploying ETHPool...")

    owner = get_account()

    contract = ETHPool.deploy(
        {"from": owner},
        publish_source=get_verify(),
    )

    print("ETHPool deployed.")

    return contract


def deploy_ethpool_v2(staking_addr=None, reward_addr=None):
    print("Deploying ETHPoolV2...")

    owner = get_account()
    staking_addr = (
        staking_addr if staking_addr is not None else get_contract("fau", "tokens")
    )
    reward_addr = (
        reward_addr if reward_addr is not None else get_contract("fau", "tokens")
    )

    contract = ETHPoolV2.deploy(
        staking_addr,
        reward_addr,
        {"from": owner},
        publish_source=get_verify(),
    )

    print("ETHPoolV2 deployed.")

    return contract


def deploy_ethpool_v3(staking_addr=None):
    print("Deploying ETHPoolV3...")

    owner = get_account()
    staking_addr = (
        staking_addr if staking_addr is not None else get_contract("fau", "tokens")
    )

    contract = ETHPoolV3.deploy(
        staking_addr,
        {"from": owner},
        publish_source=get_verify(),
    )

    print("ETHPoolV3 deployed.")

    return contract


def main():
    deploy_ethpool_v2()
