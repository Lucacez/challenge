from scripts.utils.utils import get_account, get_verify
from brownie import ETHPool


def deploy_ethpool():
    print("Deploying ETHPool...")

    owner = get_account()

    contract = ETHPool.deploy(
        {"from": owner},
        publish_source=get_verify(),
    )

    print("ETHPool deployed.")

    return contract


def main():
    deploy_ethpool()
