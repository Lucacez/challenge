from brownie import network, exceptions
from scripts.utils.utils import ENV_LOCAL, get_account
from scripts.deploy import deploy_ethpool
import pytest
from web3 import Web3
from decimal import Decimal


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


def test_cant_stake_zero():
    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    toStakeETHAmount = 0

    # Assert
    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.stakeETH(
            {
                "from": owner,
                "value": Web3.toWei(toStakeETHAmount, "ether"),
            }
        ).wait(1)
    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.stakeETH(
            {
                "from": userA,
                "value": Web3.toWei(toStakeETHAmount, "ether"),
            }
        ).wait(1)

    assert ethpool.getPoolBalance() == 0


def test_can_withdraw_all():
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
    ethpool.withdrawAllETH(
        {"from": owner},
    ).wait(1)

    ethpool.withdrawAllETH(
        {"from": userA},
    ).wait(1)

    # Assert
    assert initBalanceOwner == owner.balance()
    assert initBalanceUserA == userA.balance()

    assert ethpool.userStakedBalance(owner.address) == 0
    assert ethpool.userStakedBalance(userA.address) == 0
    assert ethpool.getPoolBalance() == 0

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawAllETH(
            {"from": owner},
        ).wait(1)

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawAllETH(
            {"from": userA},
        ).wait(1)


def test_can_withdraw_exact():
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
    ethpool.withdrawExactETH(
        Web3.toWei(toStakeETHAmount, "ether"),
        {"from": owner},
    ).wait(1)

    ethpool.withdrawExactETH(
        Web3.toWei(toStakeETHAmount / 2, "ether"),
        {"from": userA},
    ).wait(1)

    userA_partialBalance = ethpool.userStakedBalance(userA.address)

    ethpool.withdrawExactETH(
        Web3.toWei(toStakeETHAmount / 2, "ether"),
        {"from": userA},
    ).wait(1)

    # Assert
    assert initBalanceOwner == owner.balance()
    assert initBalanceUserA == userA.balance()
    assert userA_partialBalance == Web3.toWei(toStakeETHAmount / 2, "ether")

    assert ethpool.userStakedBalance(owner.address) == 0
    assert ethpool.userStakedBalance(userA.address) == 0
    assert ethpool.getPoolBalance() == 0

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawAllETH(
            {"from": owner},
        ).wait(1)

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawAllETH(
            {"from": userA},
        ).wait(1)

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawExactETH(
            ethpool.userStakedBalance(owner.address),
            {"from": owner},
        ).wait(1)

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawExactETH(
            ethpool.userStakedBalance(userA.address),
            {"from": userA},
        ).wait(1)


def test_can_deposit_rewards():
    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    toDepositRewardAmount = 0.5

    # Act
    ethpool.depositRewards(
        {
            "from": owner,
            "value": Web3.toWei(toDepositRewardAmount, "ether"),
        }
    ).wait(1)

    # Assert
    ethpool.getRewardBalance() == ethpool.balance()
    ethpool.getRewardBalance() == Web3.toWei(toDepositRewardAmount, "ether")

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.depositRewards({"from": userA}).wait(1)


def test_can_claim_rewards():
    # A, B are users
    # Actions:
    #   A deposits 5 ETH
    #   ADMIN distributes 1 ETH reward
    #   B deposits 5 ETH
    #   ADMIN distributes 1 ETH reward
    #   A, B claim their rewards
    # Expected:
    #   A claims 1.5 ETH
    #   B claims 0.5 ETH

    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    userB = get_account(2)

    userA_initialBal = userA.balance()
    userB_initialBal = userB.balance()

    userA_toStake = 5
    userB_toStake = 5
    owner_toReward = 1

    # Act
    ethpool.stakeETH(
        {
            "from": userA,
            "value": Web3.toWei(userA_toStake, "ether"),
        }
    ).wait(1)

    ethpool.depositRewards(
        {
            "from": owner,
            "value": Web3.toWei(owner_toReward, "ether"),
        }
    ).wait(1)

    ethpool.stakeETH(
        {
            "from": userB,
            "value": Web3.toWei(userB_toStake, "ether"),
        }
    ).wait(1)

    ethpool.depositRewards(
        {
            "from": owner,
            "value": Web3.toWei(owner_toReward, "ether"),
        }
    ).wait(1)

    ethpool.claimRewards({"from": userA}).wait(1)
    ethpool.claimRewards({"from": userB}).wait(1)

    # Assert
    userA_expectedReward = 1.5
    userB_expectedReward = 0.5

    assert pytest.approx(userA.balance()) == Web3.toWei(
        userA_expectedReward, "ether"
    ) + userA_initialBal - Web3.toWei(userA_toStake, "ether")
    assert pytest.approx(userB.balance()) == Web3.toWei(
        userB_expectedReward, "ether"
    ) + userB_initialBal - Web3.toWei(userB_toStake, "ether")


def test_custom_scenario():
    # In this scenario, users A, B, C will deposit ETH to the pool at different intervals
    # as well as change their balances throughout time.
    #
    # t0:   A deposits 10 ETH
    #       B deposits 10 ETH
    #       B deposits 20 ETH
    # t1:   ADMIN distributes 10 ETH
    #       C deposits 60 ETH
    #       A deposits 20 ETH
    # t2:   ADMIN distributes 20 ETH
    #       C withdraws 30 ETH
    # t3:   ADMIN distributes 45 ETH
    #       A, B, C withdraw all.
    #
    # Expected rewards:
    #       A: 22,5 ETH
    #       B: 27,5 ETH
    #       C: 25 ETH

    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    userB = get_account(2)
    userC = get_account(3)

    userA_initialBal = userA.balance()
    userB_initialBal = userB.balance()
    userC_initialBal = userC.balance()

    # Act
    # t0
    ethpool.stakeETH({"from": userA, "value": Web3.toWei(10, "ether")}).wait(1)
    ethpool.stakeETH({"from": userB, "value": Web3.toWei(10, "ether")}).wait(1)
    ethpool.stakeETH({"from": userB, "value": Web3.toWei(20, "ether")}).wait(1)

    # t1
    ethpool.depositRewards({"from": owner, "value": Web3.toWei(10, "ether")}).wait(1)

    ethpool.stakeETH({"from": userC, "value": Web3.toWei(60, "ether")}).wait(1)
    ethpool.stakeETH({"from": userA, "value": Web3.toWei(20, "ether")}).wait(1)

    # t2
    ethpool.depositRewards({"from": owner, "value": Web3.toWei(20, "ether")}).wait(1)

    ethpool.withdrawExactETH(Web3.toWei(30, "ether"), {"from": userC}).wait(1)

    # t3
    ethpool.depositRewards({"from": owner, "value": Web3.toWei(45, "ether")}).wait(1)

    ethpool.withdrawAllETH({"from": userA}).wait(1)
    ethpool.withdrawAllETH({"from": userB}).wait(1)
    ethpool.withdrawAllETH({"from": userC}).wait(1)

    userA_tx = ethpool.claimRewards({"from": userA})
    userA_tx.wait(1)
    userB_tx = ethpool.claimRewards({"from": userB})
    userB_tx.wait(1)
    userC_tx = ethpool.claimRewards({"from": userC})
    userC_tx.wait(1)

    # Assert
    expectedRewardA = Decimal(22.5)
    expectedRewardB = Decimal(27.5)
    expectedRewardC = Decimal(25)
    assert "ClaimedRewards" in userA_tx.events
    assert (
        pytest.approx(
            Web3.fromWei(userA_tx.events["ClaimedRewards"]["amount"], "ether")
        )
        == expectedRewardA
    )
    assert "ClaimedRewards" in userB_tx.events
    assert (
        pytest.approx(
            Web3.fromWei(userB_tx.events["ClaimedRewards"]["amount"], "ether")
        )
        == expectedRewardB
    )
    assert "ClaimedRewards" in userC_tx.events
    assert (
        pytest.approx(
            Web3.fromWei(userC_tx.events["ClaimedRewards"]["amount"], "ether")
        )
        == expectedRewardC
    )

    assert Web3.fromWei(userA_initialBal, "ether") == pytest.approx(
        Web3.fromWei(userA.balance(), "ether") - expectedRewardA
    )
    assert Web3.fromWei(userB_initialBal, "ether") == pytest.approx(
        Web3.fromWei(userB.balance(), "ether") - expectedRewardB
    )
    assert Web3.fromWei(userC_initialBal, "ether") == pytest.approx(
        Web3.fromWei(userC.balance(), "ether") - expectedRewardC
    )

    # print(userA_tx.events)
