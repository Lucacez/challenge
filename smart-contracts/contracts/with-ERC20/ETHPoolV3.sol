// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/* ------------------------------------------------------------------------------ */
/*                                     !! NOTICE !!                               */
/* ------------------------------------------------------------------------------ */
/* THIS IS A MODIFIED VERSION OF THE ORIGINAL CHALLENGE.
 *
 * IN V3, THE REWARDS CAN BE DIFFERENT ERC20 TOKENS. WHATEVER THE OWNER WANTS
 *
 * For the original solution, check "../original/ETHPool.sol"
 * For the modified solution, check "../with-ERC20/ETHPoolV2.sol"
 */

/// @title ETHPool
/// @author CMierez
/// @notice ETH Staking Pool with an sporadic centralized Rewards distribution
contract ETHPoolV3 is Ownable {
    /* -------------------------------------------------------------------------- */
    /*                                  Variables                                 */
    /* -------------------------------------------------------------------------- */
    /// @notice The total amount of staked tokens in the pool
    uint256 private _totalPoolBalance;

    /* --------------------------------- Staking -------------------------------- */
    /// @notice The contract address of the staking token
    IERC20 public stakingToken;

    /// @notice Each user's token staking balance
    mapping(address => uint256) public userStakedBalance;

    /* --------------------------------- Rewards -------------------------------- */
    /// @notice Counts the total amount of times admins have deposited rewards.
    uint256 private _totalRewardCount;

    /// @notice The user's rewards data.
    /// User -> ERC20 -> UserRewardData
    mapping(address => mapping(address => UserRewardData)) public userRewards;

    /// @notice The contract's allowed reward tokens
    /// ERC20 -> AllowedReward
    mapping(address => AllowedReward) public allowedRewardTokens;

    /// @dev This is needed so that all tokens can be looped through.
    /// See [updateUserRewards] for the explanation.
    address[] public s_allowedRewardTokensList;

    /* -------------------------------------------------------------------------- */
    /*                                   Structs                                  */
    /* -------------------------------------------------------------------------- */
    struct UserRewardData {
        /// @notice SNAPSHOT of the [totalRewardPerTokenMask] at the user's last reward
        /// calculation.
        uint256 userRewardPerTokenMask;
        uint256 pendingAmount;
        uint256 totalAmount;
    }

    struct AllowedReward {
        bool isAllowed;
        /// @notice CURRENT total cumulative rewards per token of this kind
        uint256 totalRewardPerTokenMask;
        /// @notice The amount of rewards yet to be distributed
        uint256 toDistributeBalance;
    }

    /* -------------------------------------------------------------------------- */
    /*                                   Events                                   */
    /* -------------------------------------------------------------------------- */
    event Staked(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event DepositedRewards(
        uint256 indexed depositNumber,
        address indexed rewardToken,
        uint256 blockNumber,
        uint256 amount
    );
    event ClaimedRewards(
        address indexed user,
        address indexed rewardToken,
        uint256 amount
    );

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
        /*
         * Since there are multiple possible tokens to be received as rewards, this
         * step will require a loop.
         * However, this should be acceptable since the amount of possible reward
         * tokens shouldn't scale to big amounts.
         * Thus I believe, despite making this compromise, this algorithm is still
         * considerably efficient.
         */
        /*
         * Also, this loop will happen for each token that is allowed in the
         * contract. It would seem more efficient to only go through the ones that
         * the user has been present for to receive, but that would mean having to
         * store the tokens for each user, which would in turn create a not
         * scalable use of storage. So this is yet another compromise that needs
         * to be made.
         */
        address[] memory tokenList = s_allowedRewardTokensList;
        for (uint128 i = 0; i < tokenList.length; i++) {
            userRewards[_account][tokenList[i]]
                .pendingAmount = getUserPendingRewards(_account, tokenList[i]);
            // Update the user's reward mask
            userRewards[_account][tokenList[i]]
                .userRewardPerTokenMask = allowedRewardTokens[tokenList[i]]
                .totalRewardPerTokenMask;
        }
        _;
    }

    /// @notice Update the contract's total rewards mask with the newest rewards.
    modifier updateTotalRewards(uint256 _reward, address _token) {
        allowedRewardTokens[_token]
            .totalRewardPerTokenMask = getNextTotalRewardMask(_reward, _token);
        _;
    }

    /* -------------------------------------------------------------------------- */
    /*                                 Constructor                                */
    /* -------------------------------------------------------------------------- */
    constructor(address _stakingToken) public {
        stakingToken = IERC20(_stakingToken);
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
    function getRewardBalance(address _token) public view returns (uint256) {
        return allowedRewardTokens[_token].toDistributeBalance;
    }

    /// @notice Subtract the user's mask from the total mask to obtain the rewards
    /// per token, and multiply that by the user's staked balance.
    /// Accumulate the result with the already pending rewards.
    /// @param _account the user's address.
    /// @return the user's pending rewards.
    function getUserPendingRewards(address _account, address _token)
        public
        view
        returns (uint256)
    {
        return
            ((userStakedBalance[_account] *
                (allowedRewardTokens[_token].totalRewardPerTokenMask -
                    userRewards[_account][_token].userRewardPerTokenMask)) /
                1e18) + userRewards[_account][_token].pendingAmount;
    }

    /// @notice Calculate the next total rewards mask, accumulating the pool's
    /// current balance and a specific reward.
    /// @param _reward the amount of reward to be distributed in the current pool.
    /// @return the next total rewards mask.
    function getNextTotalRewardMask(uint256 _reward, address _token)
        public
        view
        returns (uint256)
    {
        if (_totalPoolBalance == 0) return 0;

        return
            allowedRewardTokens[_token].totalRewardPerTokenMask +
            ((_reward * 1e18) / _totalPoolBalance);
    }

    /* --------------------------------- Rewards -------------------------------- */
    /// @notice Admin's function to distribute rewards to stakers.
    function depositRewards(uint256 _amount, address _token)
        public
        payable
        onlyOwner
        requirePositiveValue(_amount)
        updateTotalRewards(_amount, _token)
    {
        require(_totalPoolBalance > 0, "Staking pool must not be empty.");
        require(
            allowedRewardTokens[_token].isAllowed,
            "The sent token is not a valid reward."
        );
        allowedRewardTokens[_token].toDistributeBalance += _amount;
        _totalRewardCount += 1;

        IERC20(_token).transferFrom(msg.sender, address(this), _amount);

        emit DepositedRewards(_totalRewardCount, _token, block.number, _amount);
    }

    function allowRewardToken(address _token) public onlyOwner {
        require(
            !allowedRewardTokens[_token].isAllowed,
            "Token already allowed."
        );
        allowedRewardTokens[_token].isAllowed = true;
        s_allowedRewardTokensList.push(_token);
    }

    /// @notice Claim all the user's pending rewards.
    function claimRewards() public updateUserRewards(msg.sender) {
        mapping(address => UserRewardData) storage uReward = userRewards[
            msg.sender
        ];

        address[] memory tokenList = s_allowedRewardTokensList;
        for (uint128 i = 0; i < tokenList.length; i++) {
            uint256 pending = uReward[tokenList[i]].pendingAmount;
            require(pending > 0, "User has no pending rewards.");
            require(
                stakingToken.balanceOf(address(this)) >= pending,
                "CRITICAL: Contract has not enough tokens."
            );
            require(
                allowedRewardTokens[tokenList[i]].toDistributeBalance >=
                    pending,
                "CRITICAL: Contract has no rewards left to distribute."
            );

            uReward[tokenList[i]].pendingAmount = 0;
            uReward[tokenList[i]].totalAmount += pending;
            allowedRewardTokens[tokenList[i]].toDistributeBalance -= pending;

            IERC20(tokenList[i]).transfer(msg.sender, pending);

            emit ClaimedRewards(msg.sender, tokenList[i], pending);
        }
    }

    // Disgusting loops everywhere, that at least don't get out of hand
    // But still
    // THIS IS JUST A PROOF OF CONCEPT
    // A better solution is discussed in the Solution.md file.
}
