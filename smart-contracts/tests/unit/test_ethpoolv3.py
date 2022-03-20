from tkinter import E
from brownie import network, exceptions
from scripts.utils.utils import ENV_LOCAL, get_account, get_contract
from scripts.deploy import deploy_ethpool_v3
import pytest
from web3 import Web3
from decimal import Decimal


def _init():
    if network.show_active in ENV_LOCAL:
        pytest.skip("Test only for Local environment.")

    return get_account(), deploy_ethpool_v3()


def _fund_accounts(_accounts, _erc20_name, _amount=None):
    _amount = _amount if _amount is not None else Decimal("10")
    erc20 = get_contract(_erc20_name, "tokens")

    for account in _accounts:
        erc20.faucet(_amount, {"from": account})


def _approve_accounts(_accounts, _erc20_name, _to_approve_addr, _amount):
    erc20 = get_contract(_erc20_name, "tokens")

    for account in _accounts:
        erc20.approve(_to_approve_addr, _amount, {"from": account})


def test_can_stake():
    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    toStakeAmount = Web3.toWei(0.5, "ether")
    stakingToken = get_contract("fau", "tokens")

    _fund_accounts([owner, userA], "fau", toStakeAmount)
    _approve_accounts([owner, userA], "fau", ethpool.address, toStakeAmount)

    owner_initBalance = stakingToken.balanceOf(owner.address)
    userA_initBalance = stakingToken.balanceOf(userA.address)
    # Act
    ethpool.stakeWithPermit(
        toStakeAmount,
        {
            "from": owner,
        },
    ).wait(1)

    ethpool.stakeWithPermit(
        toStakeAmount,
        {
            "from": userA,
        },
    ).wait(1)

    # Assert
    assert ethpool.getPoolBalance() == toStakeAmount * 2
    assert stakingToken.balanceOf(owner.address) == owner_initBalance - toStakeAmount
    assert stakingToken.balanceOf(userA.address) == userA_initBalance - toStakeAmount


def test_cant_stake_zero():
    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    toStakeAmount = 0

    _fund_accounts([owner, userA], "fau", toStakeAmount)
    _approve_accounts([owner, userA], "fau", ethpool.address, toStakeAmount)

    # Assert
    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.stakeWithPermit(
            toStakeAmount,
            {
                "from": userA,
            },
        ).wait(1)
    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.stakeWithPermit(
            toStakeAmount,
            {
                "from": owner,
            },
        ).wait(1)

    assert ethpool.getPoolBalance() == 0


def test_cant_withdraw_if_no_deposit():
    # User should not be able to withdraw if no deposit has been made

    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    userA_initBalance = userA.balance()

    # Assert
    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawAll({"from": userA})

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawExact(Web3.toWei(0.01, "ether"), {"from": userA})

    assert userA_initBalance == userA.balance()


def test_can_withdraw_all():
    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    stakingToken = get_contract("fau", "tokens")
    toStakeAmount = Web3.toWei(0.5, "ether")

    _fund_accounts([owner, userA], "fau", toStakeAmount)
    _approve_accounts([owner, userA], "fau", ethpool.address, toStakeAmount)

    initBalanceOwner = stakingToken.balanceOf(owner.address)
    initBalanceUserA = stakingToken.balanceOf(userA.address)

    ethpool.stakeWithPermit(
        toStakeAmount,
        {
            "from": owner,
        },
    ).wait(1)
    ethpool.stakeWithPermit(
        toStakeAmount,
        {
            "from": userA,
        },
    ).wait(1)

    # Act
    ethpool.withdrawAll(
        {"from": owner},
    ).wait(1)

    ethpool.withdrawAll(
        {"from": userA},
    ).wait(1)

    # Assert
    assert initBalanceOwner == stakingToken.balanceOf(owner.address)
    assert initBalanceUserA == stakingToken.balanceOf(userA.address)

    assert ethpool.userStakedBalance(owner.address) == 0
    assert ethpool.userStakedBalance(userA.address) == 0
    assert ethpool.getPoolBalance() == 0

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawAll(
            {"from": owner},
        ).wait(1)

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawAll(
            {"from": userA},
        ).wait(1)


def test_can_withdraw_exact():
    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    stakingToken = get_contract("fau", "tokens")
    toStakeAmount = Web3.toWei(2, "ether")

    _fund_accounts([owner, userA], "fau", toStakeAmount)
    _approve_accounts([owner, userA], "fau", ethpool.address, toStakeAmount)

    initBalanceOwner = stakingToken.balanceOf(owner.address)
    initBalanceUserA = stakingToken.balanceOf(userA.address)

    ethpool.stakeWithPermit(
        toStakeAmount,
        {
            "from": owner,
        },
    ).wait(1)
    ethpool.stakeWithPermit(
        toStakeAmount,
        {
            "from": userA,
        },
    ).wait(1)

    # Act
    ethpool.withdrawExact(
        toStakeAmount,
        {"from": owner},
    ).wait(1)

    ethpool.withdrawExact(
        toStakeAmount / 2,
        {"from": userA},
    ).wait(1)

    userA_partialBalance = ethpool.userStakedBalance(userA.address)

    ethpool.withdrawExact(
        toStakeAmount / 2,
        {"from": userA},
    ).wait(1)

    # Assert
    assert initBalanceOwner == stakingToken.balanceOf(owner.address)
    assert initBalanceUserA == stakingToken.balanceOf(userA.address)
    assert userA_partialBalance == toStakeAmount / 2

    assert ethpool.userStakedBalance(owner.address) == 0
    assert ethpool.userStakedBalance(userA.address) == 0
    assert ethpool.getPoolBalance() == 0

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawAll(
            {"from": owner},
        ).wait(1)

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawAll(
            {"from": userA},
        ).wait(1)

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawExact(
            ethpool.userStakedBalance(owner.address),
            {"from": owner},
        ).wait(1)

    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.withdrawExact(
            ethpool.userStakedBalance(userA.address),
            {"from": userA},
        ).wait(1)


def test_no_rewards_to_claim_if_user_didnt_deposit():
    # An userA shouldn't be able to claim any rewards if they aren't staked during
    # the reward periods

    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    userB = get_account(2)
    stakingToken = get_contract("fau", "tokens")
    rewardTokenFau = get_contract("fau", "tokens")

    toStakeAmount = Web3.toWei(1, "ether")
    toRewardAmount = Web3.toWei(1, "ether")

    _fund_accounts([userA, userB], "fau", toStakeAmount)
    _fund_accounts([owner], "fau", toRewardAmount)
    _approve_accounts(
        [owner, userA, userB], "fau", ethpool.address, Web3.toWei(1001, "ether")
    )

    userA_initBalance = stakingToken.balanceOf(userA.address)

    # Act
    ethpool.stakeWithPermit(toStakeAmount, {"from": userB}).wait(1)

    ethpool.allowRewardToken(rewardTokenFau, {"from": owner})
    # This would simulate the passing of n periods as well
    periods = 3
    for _ in range(0, periods):
        ethpool.depositRewards(toRewardAmount, rewardTokenFau, {"from": owner}).wait(1)

    # Assert
    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.claimRewards({"from": userA}).wait(1)

    assert ethpool.getRewardBalance(rewardTokenFau) == toRewardAmount * periods

    assert ethpool.userStakedBalance(userA.address) == 0
    assert userA_initBalance == stakingToken.balanceOf(userA.address)
    assert ethpool.userRewards(userA.address, rewardTokenFau)["pendingAmount"] == 0
    assert ethpool.userRewards(userA.address, rewardTokenFau)["totalAmount"] == 0


def test_can_deposit_rewards():
    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    stakingToken = get_contract("fau", "tokens")
    rewardTokenFau = get_contract("fau", "tokens")

    toStakeAmount = Web3.toWei(1, "ether")
    toRewardAmount = Web3.toWei(0.5, "ether")

    _fund_accounts([userA], "fau", toStakeAmount)
    _fund_accounts([owner], "fau", toRewardAmount)
    _approve_accounts([userA], "fau", ethpool.address, toStakeAmount)
    _approve_accounts([owner], "fau", ethpool.address, toRewardAmount)

    # Act
    ethpool.allowRewardToken(rewardTokenFau, {"from": owner})

    # Cant distribute rewards if empty
    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.depositRewards(
            toRewardAmount,
            rewardTokenFau,
            {
                "from": owner,
            },
        ).wait(1)

    ethpool.stakeWithPermit(toStakeAmount, {"from": userA}).wait(1)

    ethpool.depositRewards(
        toRewardAmount,
        rewardTokenFau,
        {
            "from": owner,
        },
    ).wait(1)

    # Assert
    ethpool.getRewardBalance(rewardTokenFau) == rewardTokenFau.balanceOf(ethpool)
    ethpool.getRewardBalance(rewardTokenFau) == toRewardAmount

    # Only owner
    with pytest.raises(exceptions.VirtualMachineError):
        ethpool.depositRewards(toRewardAmount, rewardTokenFau, {"from": userA}).wait(1)


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

    stakingToken = get_contract("fau", "tokens")
    rewardTokenFau = get_contract("fau", "tokens")

    userA_toStake = Web3.toWei(5, "ether")
    userB_toStake = userA_toStake
    owner_toReward = Web3.toWei(1, "ether")

    _fund_accounts([userA, userB], "fau", userA_toStake)
    _fund_accounts([owner], "fau", owner_toReward * 2)
    _approve_accounts(
        [owner, userA, userB], "fau", ethpool.address, Web3.toWei(1000, "ether")
    )

    userA_initBalance = stakingToken.balanceOf(userA.address)
    userB_initBalance = stakingToken.balanceOf(userB.address)

    # Act
    ethpool.stakeWithPermit(
        userA_toStake,
        {
            "from": userA,
        },
    ).wait(1)

    ethpool.allowRewardToken(rewardTokenFau, {"from": owner})
    ethpool.depositRewards(
        owner_toReward,
        rewardTokenFau,
        {
            "from": owner,
        },
    ).wait(1)

    ethpool.stakeWithPermit(
        userB_toStake,
        {
            "from": userB,
        },
    ).wait(1)

    ethpool.depositRewards(
        owner_toReward,
        rewardTokenFau,
        {
            "from": owner,
        },
    ).wait(1)

    ethpool.claimRewards({"from": userA}).wait(1)
    ethpool.claimRewards({"from": userB}).wait(1)

    # Assert
    userA_expectedReward = Web3.toWei(1.5, "ether")
    userB_expectedReward = Web3.toWei(0.5, "ether")

    assert (
        pytest.approx(stakingToken.balanceOf(userA))
        == userA_expectedReward + userA_initBalance - userA_toStake
    )
    assert (
        pytest.approx(stakingToken.balanceOf(userB))
        == userB_expectedReward + userB_initBalance - userB_toStake
    )


def test_can_claim_rewards_after_withdraw():
    # User should be able to claim accumulated rewards even after withdrawing
    # aka with a zero staking balance
    #
    # t0:   A deposits 1 ETH
    # t1:   ADMIN distributes 1 ETH reward
    #       A withdraws 1 ETH
    #       A claims rewards
    # Expected:
    #       A claims 1 ETH

    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    stakingToken = get_contract("fau", "tokens")
    rewardTokenFau = get_contract("fau", "tokens")

    userA_toStake = Web3.toWei(5, "ether")
    owner_toReward = Web3.toWei(1, "ether")

    _fund_accounts([userA], "fau", userA_toStake)
    _fund_accounts([owner], "fau", owner_toReward)
    _approve_accounts([owner, userA], "fau", ethpool.address, Web3.toWei(1000, "ether"))

    userA_initBalance = stakingToken.balanceOf(userA.address)

    # Act
    ethpool.stakeWithPermit(userA_toStake, {"from": userA}).wait(1)

    # t1
    ethpool.allowRewardToken(rewardTokenFau, {"from": owner})
    ethpool.depositRewards(owner_toReward, rewardTokenFau, {"from": owner}).wait(1)

    ethpool.withdrawAll({"from": userA}).wait(1)

    claimTx = ethpool.claimRewards({"from": userA})
    claimTx.wait(1)

    # Assert
    userA_expectedReward = Web3.toWei(1, "ether")
    assert ethpool.userStakedBalance(userA.address) == 0
    assert "ClaimedRewards" in claimTx.events
    assert claimTx.events["ClaimedRewards"]["amount"] == userA_expectedReward
    assert claimTx.events["ClaimedRewards"]["rewardToken"] == rewardTokenFau.address


def test_can_deposit_multiple_times_and_claim():
    # An user should be to deposit multiple times throughout the contract's lifetime
    # and still be able to claim the appropriate rewards.
    #
    # In this example, UserA will deposit 5 ETH in batches of 1, 2, 1, 1 and then claim.
    # UserB will be in the pool as well from the start so rewards don't all go to A.
    # ADMIN will distribute 5 ETH total in batches of 1, 1, 3
    #
    # t0:   A deposits 1 ETH
    #       B deposits 1 ETH
    # t1:   ADMIN distributes 1 ETH
    #       A deposits 2 ETH
    # t2:   ADMIN distributes 1 ETH
    #       A deposits 1 ETH
    #       A deposits 1 ETH
    # t3:   ADMIN distributes 3 ETH
    #       A, B withdraw all.
    #
    # Expected rewards:
    #       A: 3.75 ETH
    #       B: 1.25 ETH

    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    userB = get_account(2)
    stakingToken = get_contract("fau", "tokens")
    rewardTokenFau = get_contract("fau", "tokens")

    _fund_accounts([owner, userA, userB], "fau", Web3.toWei(1000, "ether"))
    _approve_accounts(
        [owner, userA, userB], "fau", ethpool.address, Web3.toWei(1000, "ether")
    )

    userA_initBalance = stakingToken.balanceOf(userA.address)
    userB_initBalance = stakingToken.balanceOf(userB.address)

    # Act
    # t0
    ethpool.stakeWithPermit(Web3.toWei(1, "ether"), {"from": userA}).wait(1)
    ethpool.stakeWithPermit(Web3.toWei(1, "ether"), {"from": userB}).wait(1)

    # t1
    ethpool.allowRewardToken(rewardTokenFau, {"from": owner})
    ethpool.depositRewards(
        Web3.toWei(1, "ether"), rewardTokenFau, {"from": owner}
    ).wait(1)

    ethpool.stakeWithPermit(Web3.toWei(2, "ether"), {"from": userA}).wait(1)

    # t2
    ethpool.depositRewards(
        Web3.toWei(1, "ether"), rewardTokenFau, {"from": owner}
    ).wait(1)

    ethpool.stakeWithPermit(Web3.toWei(1, "ether"), {"from": userA}).wait(1)
    ethpool.stakeWithPermit(Web3.toWei(1, "ether"), {"from": userA}).wait(1)

    # t3
    ethpool.depositRewards(
        Web3.toWei(3, "ether"), rewardTokenFau, {"from": owner}
    ).wait(1)

    ethpool.claimRewards({"from": userA}).wait(1)
    ethpool.claimRewards({"from": userB}).wait(1)

    # Assert
    userA_expectedReward = Decimal(3.75)
    userB_expectedReward = Decimal(1.25)
    userA_totalStaked = Decimal(5)
    userB_totalStaked = Decimal(1)

    assert pytest.approx(stakingToken.balanceOf(userA)) == Web3.toWei(
        userA_expectedReward, "ether"
    ) + userA_initBalance - Web3.toWei(userA_totalStaked, "ether")
    assert pytest.approx(stakingToken.balanceOf(userB)) == Web3.toWei(
        userB_expectedReward, "ether"
    ) + userB_initBalance - Web3.toWei(userB_totalStaked, "ether")


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

    stakingToken = get_contract("fau", "tokens")
    rewardTokenFau = get_contract("fau", "tokens")

    _fund_accounts([owner, userA, userB, userC], "fau", Web3.toWei(1000, "ether"))
    _approve_accounts(
        [owner, userA, userB, userC], "fau", ethpool.address, Web3.toWei(1000, "ether")
    )

    userA_initBalance = stakingToken.balanceOf(userA.address)
    userB_initBalance = stakingToken.balanceOf(userB.address)
    userC_initBalance = stakingToken.balanceOf(userC.address)

    # Act
    # t0
    ethpool.stakeWithPermit(Web3.toWei(10, "ether"), {"from": userA}).wait(1)
    ethpool.stakeWithPermit(Web3.toWei(10, "ether"), {"from": userB}).wait(1)
    ethpool.stakeWithPermit(Web3.toWei(20, "ether"), {"from": userB}).wait(1)

    # t1
    ethpool.allowRewardToken(rewardTokenFau, {"from": owner}).wait(1)
    ethpool.depositRewards(
        Web3.toWei(10, "ether"), rewardTokenFau, {"from": owner}
    ).wait(1)

    ethpool.stakeWithPermit(Web3.toWei(60, "ether"), {"from": userC}).wait(1)
    ethpool.stakeWithPermit(Web3.toWei(20, "ether"), {"from": userA}).wait(1)

    # t2
    ethpool.depositRewards(
        Web3.toWei(20, "ether"), rewardTokenFau, {"from": owner}
    ).wait(1)

    ethpool.withdrawExact(Web3.toWei(30, "ether"), {"from": userC}).wait(1)

    # t3
    ethpool.depositRewards(
        Web3.toWei(45, "ether"), rewardTokenFau, {"from": owner}
    ).wait(1)

    ethpool.withdrawAll({"from": userA}).wait(1)
    ethpool.withdrawAll({"from": userB}).wait(1)
    ethpool.withdrawAll({"from": userC}).wait(1)

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

    assert Web3.fromWei(userA_initBalance, "ether") == pytest.approx(
        Web3.fromWei(stakingToken.balanceOf(userA), "ether") - expectedRewardA
    )
    assert Web3.fromWei(userB_initBalance, "ether") == pytest.approx(
        Web3.fromWei(stakingToken.balanceOf(userB), "ether") - expectedRewardB
    )
    assert Web3.fromWei(userC_initBalance, "ether") == pytest.approx(
        Web3.fromWei(stakingToken.balanceOf(userC), "ether") - expectedRewardC
    )


def test_can_claim_multiple_rewards():
    # Arrange
    owner, ethpool = _init()
    userA = get_account(1)
    userB = get_account(2)

    stakingToken = get_contract("fau", "tokens")
    rewardTokenFau = get_contract("fau", "tokens")
    rewardTokenLink = get_contract("link", "tokens")

    _fund_accounts([owner, userA, userB], "fau", Web3.toWei(1000, "ether"))
    _fund_accounts([owner], "link", Web3.toWei(1000, "ether"))

    _approve_accounts(
        [owner, userA, userB], "fau", ethpool.address, Web3.toWei(1000, "ether")
    )
    _approve_accounts([owner], "link", ethpool.address, Web3.toWei(1000, "ether"))

    userA_initBalance = rewardTokenFau.balanceOf(userA.address)
    userB_initBalance = rewardTokenFau.balanceOf(userB.address)

    # Act
    ethpool.stakeWithPermit(Web3.toWei(10, "ether"), {"from": userA}).wait(1)

    # t1
    ethpool.allowRewardToken(rewardTokenFau, {"from": owner}).wait(1)
    ethpool.depositRewards(
        Web3.toWei(5, "ether"), rewardTokenFau, {"from": owner}
    ).wait(1)

    ethpool.stakeWithPermit(Web3.toWei(10, "ether"), {"from": userB}).wait(1)

    # t2
    ethpool.allowRewardToken(rewardTokenLink, {"from": owner}).wait(1)
    ethpool.depositRewards(
        Web3.toWei(5, "ether"), rewardTokenLink, {"from": owner}
    ).wait(1)

    # t3
    ethpool.depositRewards(
        Web3.toWei(5, "ether"), rewardTokenFau, {"from": owner}
    ).wait(1)

    ethpool.stakeWithPermit(Web3.toWei(20, "ether"), {"from": userB}).wait(1)

    # t4
    ethpool.depositRewards(
        Web3.toWei(10, "ether"), rewardTokenLink, {"from": owner}
    ).wait(1)

    # Claim
    ethpool.claimRewards({"from": userA}).wait(1)
    ethpool.claimRewards({"from": userB}).wait(1)

    # Assert
    userA_expectedFau = Web3.toWei(Decimal(7.5), "ether")
    userB_expectedFau = Web3.toWei(Decimal(2.5), "ether")
    userA_expectedLink = Web3.toWei(Decimal(5), "ether")
    userB_expectedLink = Web3.toWei(Decimal(10), "ether")
    userA_totalStaked = Web3.toWei(Decimal(10), "ether")
    userB_totalStaked = Web3.toWei(Decimal(30), "ether")

    assert (
        userA_initBalance - userA_totalStaked + userA_expectedFau
    ) == rewardTokenFau.balanceOf(userA)
    assert (
        userB_initBalance - userB_totalStaked + userB_expectedFau
    ) == rewardTokenFau.balanceOf(userB)

    assert rewardTokenLink.balanceOf(userA) == userA_expectedLink
    assert rewardTokenLink.balanceOf(userB) == userB_expectedLink
