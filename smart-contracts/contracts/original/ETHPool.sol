// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/// @title ETHPool
/// @author CMierez
/// @notice ETH Staking Pool with an sporadic centralized Rewards distribution
contract ETHPool is Ownable, ReentrancyGuard {
    /* -------------------------------------------------------------------------- */
    /*                                  Variables                                 */
    /* -------------------------------------------------------------------------- */

    /// @notice The total amount of staked tokens in the pool
    uint256 private _totalPoolBalance;

    /* --------------------------------- Staking -------------------------------- */
    /// @notice Each user's token staking balance
    mapping(address => uint256) public userStakedBalance;

    /* --------------------------------- Rewards -------------------------------- */
    /// @notice The total amount of rewards yet to be distributed
    uint256 private _totalRewardBalance;

    /// @notice Counts the total amount of times admins have deposited rewards.
    uint256 private _totalRewardCount;

    /// @notice CURRENT total cumulative rewards per token
    uint256 public totalRewardPerTokenMask;

    /// @notice SNAPSHOT of the [totalRewardPerTokenMask] at the user's last reward
    /// calculation
    mapping(address => uint256) public userRewardPerTokenMask;

    /// @notice The user's rewards data
    mapping(address => UserReward) public userRewards;

    /* -------------------------------------------------------------------------- */
    /*                                   Structs                                  */
    /* -------------------------------------------------------------------------- */
    /// @dev For the sake of analysis, I'm storing the historical total amount
    /// of rewards as well.
    /// This Struct could be avoided otherwise.
    /// Another solution could be aggregating the [ClaimedRewards] event from an
    /// off-chain backend.
    struct UserReward {
        uint256 pendingAmount;
        uint256 totalAmount;
    }

    /* -------------------------------------------------------------------------- */
    /*                                   Events                                   */
    /* -------------------------------------------------------------------------- */
    event StakedETH(address indexed user, uint256 amount);
    event WithdrawnETH(address indexed user, uint256 amount);
    event DepositedRewards(
        uint256 indexed depositNumber,
        uint256 blockNumber,
        uint256 amount
    );
    event ClaimedRewards(address indexed user, uint256 amount);

    /* -------------------------------------------------------------------------- */
    /*                                  Modifiers                                 */
    /* -------------------------------------------------------------------------- */
    /// @dev Checks whether the [msg.value] is a positive number
    modifier positiveEthValue() {
        require(msg.value > 0, "Must send a positive amount of ETH.");
        _;
    }

    /// @notice Update the user's pending rewards and shift its mask accordingly.
    modifier updateUserRewards(address _account) {
        // Update the user's pending rewards
        userRewards[_account].pendingAmount = getUserPendingRewards(_account);
        // Update the user's reward mask
        userRewardPerTokenMask[_account] = totalRewardPerTokenMask;
        _;
    }

    /// @notice Update the contract's total rewards mask with the newest rewards.
    modifier updateTotalRewards(uint256 _reward) {
        totalRewardPerTokenMask = getNextTotalRewardMask(_reward);
        _;
    }

    /* -------------------------------------------------------------------------- */
    /*                                  Functions                                 */
    /* -------------------------------------------------------------------------- */
    /// @notice Receives an ETH deposit and updates the user's balance accordingly.
    function stakeETH()
        public
        payable
        nonReentrant
        positiveEthValue
        updateUserRewards(msg.sender)
    {
        _totalPoolBalance += msg.value;
        userStakedBalance[msg.sender] += msg.value;
        emit StakedETH(msg.sender, msg.value);
    }

    /// @notice Withdraws all the user's staked tokens and updates the pool's balance.
    function withdrawAllETH() public {
        withdrawExactETH(userStakedBalance[msg.sender]);
    }

    /// @notice Withdraws an exact amount of user's staked tokens and updates the pool's balance.
    /// @param _amount the exact amount of tokens to withdraw.
    function withdrawExactETH(uint256 _amount)
        public
        nonReentrant
        updateUserRewards(msg.sender)
    {
        uint256 staked = userStakedBalance[msg.sender];
        require(staked > 0, "Must have staked ETH to withdraw.");
        require(_amount > 0, "Must unstake a positive value.");
        require(staked >= _amount, "Not enough ETH staked.");

        userStakedBalance[msg.sender] = staked - _amount;
        _totalPoolBalance -= _amount;

        // AFAIK This is the preferred way of transferring ETH currently
        (bool sent, ) = msg.sender.call{value: _amount}("");
        require(sent, "Failed to send Ether.");

        emit WithdrawnETH(msg.sender, _amount);
    }

    /* --------------------------------- Views --------------------------------- */
    /// @return the current total of staked tokens.
    function getPoolBalance() public view returns (uint256) {
        return _totalPoolBalance;
    }

    /// @return the current total of rewards tokens to be distributed.
    function getRewardBalance() public view returns (uint256) {
        return _totalRewardBalance;
    }

    /// @notice Subtract the user's mask from the total mask to obtain the rewards
    /// per token, and multiply that by the user's staked balance.
    /// Accumulate the result with the already pending rewards.
    /// @param _account the user's address.
    /// @return the user's pending rewards.
    function getUserPendingRewards(address _account)
        public
        view
        returns (uint256)
    {
        return
            ((userStakedBalance[_account] *
                (totalRewardPerTokenMask - userRewardPerTokenMask[_account])) /
                1e18) + userRewards[_account].pendingAmount;
    }

    /// @notice Calculate the next total rewards mask, accumulating the pool's
    /// current balance and a specific reward.
    /// @param _reward the amount of reward to be distributed in the current pool.
    /// @return the next total rewards mask.
    function getNextTotalRewardMask(uint256 _reward)
        public
        view
        returns (uint256)
    {
        if (_totalPoolBalance == 0) {
            return 0;
        }
        return totalRewardPerTokenMask + ((_reward * 1e18) / _totalPoolBalance);
    }

    /* --------------------------------- Rewards -------------------------------- */
    /// @notice Admin's function to distribute rewards to stakers.
    function depositRewards()
        public
        payable
        onlyOwner
        positiveEthValue
        updateTotalRewards(msg.value)
    {
        require(
            _totalPoolBalance > 0,
            "The pool must have at least one staking user."
        );
        _totalRewardBalance += msg.value;
        _totalRewardCount += 1;
        emit DepositedRewards(_totalRewardCount, block.number, msg.value);
    }

    /// @notice Claim all the user's pending rewards.
    function claimRewards() public nonReentrant updateUserRewards(msg.sender) {
        UserReward storage uReward = userRewards[msg.sender];
        uint256 pending = uReward.pendingAmount;
        require(uReward.pendingAmount > 0, "User has no pending rewards.");
        require(
            address(this).balance >= pending,
            "CRITICAL: Contract has no ETH."
        );
        require(
            _totalRewardBalance >= pending,
            "CRITICAL: Contract has no rewards left to distribute."
        );

        uReward.pendingAmount = 0;
        uReward.totalAmount += pending;
        _totalRewardBalance -= pending;

        (bool sent, ) = msg.sender.call{value: pending}("");
        require(sent, "Failed to send Ether.");

        emit ClaimedRewards(msg.sender, pending);
    }
}
