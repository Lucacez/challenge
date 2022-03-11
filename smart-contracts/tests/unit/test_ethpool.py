from brownie import network, exceptions
from scripts.utils.utils import ENV_LOCAL, get_account
from scripts.deploy import deploy_ethpool
import pytest
from web3 import Web3


def _init():
    if network.show_active in ENV_LOCAL:
        pytest.skip("Test only for Local environment.")

    return get_account(), deploy_ethpool()


def test_can_stake():
    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    toStakeETHAmount = 0.5

    # Act
    ethpool.stakeETH(
        {
            "from": owner,
            "value": Web3.toWei(toStakeETHAmount, "ether"),
        }
    ).wait(1)

    ethpool.stakeETH(
        {
            "from": userA,
            "value": Web3.toWei(toStakeETHAmount, "ether"),
        }
    ).wait(1)

    # Assert
    assert ethpool.getPoolBalance() == Web3.toWei(toStakeETHAmount * 2, "ether")


def test_can_withdraw():
    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    toStakeETHAmount = 0.5

    initBalanceOwner = owner.balance()
    initBalanceUserA = userA.balance()

    ethpool.stakeETH(
        {
            "from": owner,
            "value": Web3.toWei(toStakeETHAmount, "ether"),
        }
    ).wait(1)
    ethpool.stakeETH(
        {
            "from": userA,
            "value": Web3.toWei(toStakeETHAmount, "ether"),
        }
    ).wait(1)

    # Act
    ethpool.withdrawETH(
        {"from": owner},
    ).wait(1)

    ethpool.withdrawETH(
        {"from": userA},
    ).wait(1)

    # Assert
    assert initBalanceOwner == owner.balance()
    assert initBalanceUserA == userA.balance()

    assert ethpool.userStakedAmount(owner.address) == 0
    assert ethpool.userStakedAmount(userA.address) == 0
    assert ethpool.getPoolBalance() == 0

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawETH(
            {"from": owner},
        ).wait(1)

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawETH(
            {"from": userA},
        ).wait(1)
