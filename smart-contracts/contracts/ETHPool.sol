// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";

/// @title ETHPool
/// @author CMierez
/// @notice ETH Staking Pool with an sporadic centralized Rewards distribution
contract ETHPool is Ownable {
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
    event DepositedRewards(uint256 blockNumber, uint256 amount);
    event ClaimedRewards(address indexed user, uint256 amount);

    /* -------------------------------------------------------------------------- */
    /*                                  Modifiers                                 */
    /* -------------------------------------------------------------------------- */
    /// @dev Checks whether the [msg.value] is a positive number
    modifier positiveEthValue() {
        require(msg.value > 0, "Must send a positive amount of ETH.");
        _;
    }

    modifier updateUserRewards(address account) {
        // Update the user's pending rewards
        userRewards[account].pendingAmount = getUserPendingRewards(account);
        // Update the user's reward mask
        userRewardPerTokenMask[account] = totalRewardPerTokenMask;
        _;
    }

    /* -------------------------------------------------------------------------- */
    /*                                  Functions                                 */
    /* -------------------------------------------------------------------------- */
    /// @notice Receives an ETH deposit and updates the user's balance accordingly.
    function stakeETH()
        public
        payable
        positiveEthValue
        updateUserRewards(msg.sender)
    {
        _totalPoolBalance += msg.value;
        userStakedBalance[msg.sender] += msg.value;
        emit StakedETH(msg.sender, msg.value);
    }

    /// @notice Withdraws the user's staked tokens and updates the pool's balance.
    function withdrawETH() public updateUserRewards(msg.sender) {
        uint256 staked = userStakedBalance[msg.sender];
        require(staked > 0, "Must have staked ETH to withdraw.");

        userStakedBalance[msg.sender] = 0;
        _totalPoolBalance -= staked;

        // AFAIK This is the preferred way of transferring ETH currently
        (bool sent, ) = msg.sender.call{value: staked}("");
        require(sent, "Failed to send Ether.");

        emit WithdrawnETH(msg.sender, staked);
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

    function getUserPendingRewards(address account)
        public
        view
        returns (uint256)
    {
        return
            (userStakedBalance[account] *
                (totalRewardPerTokenMask - userRewardPerTokenMask[account])) +
            userRewards[account].pendingAmount;
    }

    /* --------------------------------- Rewards -------------------------------- */
    /// @notice Admin's function to distribute rewards to stakers.
    function depositRewards() public payable onlyOwner positiveEthValue {
        _totalRewardBalance += msg.value;
        emit DepositedRewards(block.number, msg.value);
    }
}
