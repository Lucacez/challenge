// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/* ------------------------------------------------------------------------------ */
/*                                     !! NOTICE !!                               */
/* ------------------------------------------------------------------------------ */
/* THIS IS A MODIFIED VERSION OF THE ORIGINAL CHALLENGE, IN WHICH I CHANGE THE
 * REWARD TOKEN TO BE AN ERC-20 INSTEAD OF JUST ETH.
 *
 * For the original solution, check "../original/ETHPool.sol"
 */

/// @title ETHPool
/// @author CMierez
/// @notice ETH Staking Pool with an sporadic centralized Rewards distribution
contract ETHPoolV2 is Ownable {
    /* -------------------------------------------------------------------------- */
    /*                                  Variables                                 */
    /* -------------------------------------------------------------------------- */

    /// @notice The total amount of staked tokens in the pool
    uint256 private _totalPoolBalance;

    /* --------------------------------- Staking -------------------------------- */
    /// @notice Each user's token staking balance
    mapping(address => uint256) public userStakedBalance;

    /// @notice The contract address of the staking token
    IERC20 public stakingToken;

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

    /// @notice The contract's reward token
    IERC20 public rewardToken;

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
    event Staked(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event DepositedRewards(
        uint256 indexed depositNumber,
        uint256 blockNumber,
        uint256 amount
    );
    event ClaimedRewards(address indexed user, uint256 amount);

    /* -------------------------------------------------------------------------- */
    /*                                  Modifiers                                 */
    /* -------------------------------------------------------------------------- */
    /// @notice Require a positive value.
    modifier requirePositiveValue(uint256 _value) {
        require(_value > 0, "Value must be positive.");
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
    /*                                 Constructor                                */
    /* -------------------------------------------------------------------------- */
    constructor(address _stakingToken, address _rewardToken) public {
        stakingToken = IERC20(_stakingToken);
        rewardToken = IERC20(_rewardToken);
    }

    /* -------------------------------------------------------------------------- */
    /*                                  Functions                                 */
    /* -------------------------------------------------------------------------- */
    /// @notice Receives a deposit and updates the user's balance accordingly.
    function stakeWithPermit(uint256 _amount)
        public
        payable
        requirePositiveValue(_amount)
        updateUserRewards(msg.sender)
    {
        _totalPoolBalance += _amount;
        userStakedBalance[msg.sender] += _amount;

        stakingToken.transferFrom(msg.sender, address(this), _amount);

        emit Staked(msg.sender, _amount);
    }

    /// @notice Withdraws all the user's staked tokens and updates the pool's balance.
    function withdrawAll() public {
        withdrawExact(userStakedBalance[msg.sender]);
    }

    /// @notice Withdraws an exact amount of user's staked tokens and updates the pool's balance.
    /// @param _amount the exact amount of tokens to withdraw.
    function withdrawExact(uint256 _amount)
        public
        requirePositiveValue(_amount)
        updateUserRewards(msg.sender)
    {
        uint256 staked = userStakedBalance[msg.sender];
        require(staked >= _amount, "Not enough tokens staked.");

        userStakedBalance[msg.sender] = staked - _amount;
        _totalPoolBalance -= _amount;

        stakingToken.transfer(msg.sender, _amount);

        emit Withdrawn(msg.sender, _amount);
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
        if (_totalPoolBalance == 0) return 0;

        return totalRewardPerTokenMask + ((_reward * 1e18) / _totalPoolBalance);
    }

    /* --------------------------------- Rewards -------------------------------- */
    /// @notice Admin's function to distribute rewards to stakers.
    function depositRewards(uint256 _amount)
        public
        payable
        onlyOwner
        requirePositiveValue(_amount)
        updateTotalRewards(_amount)
    {
        require(_totalPoolBalance > 0, "Staking pool must not be empty.");
        _totalRewardBalance += _amount;
        _totalRewardCount += 1;

        rewardToken.transferFrom(msg.sender, address(this), _amount);

        emit DepositedRewards(_totalRewardCount, block.number, _amount);
    }

    /// @notice Claim all the user's pending rewards.
    function claimRewards() public updateUserRewards(msg.sender) {
        UserReward storage uReward = userRewards[msg.sender];
        uint256 pending = uReward.pendingAmount;
        require(uReward.pendingAmount > 0, "User has no pending rewards.");
        require(
            stakingToken.balanceOf(address(this)) >= pending,
            "CRITICAL: Contract has not enough tokens."
        );
        require(
            _totalRewardBalance >= pending,
            "CRITICAL: Contract has no rewards left to distribute."
        );

        uReward.pendingAmount = 0;
        uReward.totalAmount += pending;
        _totalRewardBalance -= pending;

        rewardToken.transfer(msg.sender, pending);

        emit ClaimedRewards(msg.sender, pending);
    }
}
