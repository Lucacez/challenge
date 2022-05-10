// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/// @title ETHPool

contract ETHPool is AccessControl, ReentrancyGuard{

    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant TEAM_ROLE = keccak256("TEAM_ROLE");

    constructor() {
        s_owner = msg.sender;
        _setupRole(ADMIN_ROLE, s_owner);
        _setRoleAdmin(TEAM_ROLE, ADMIN_ROLE);
    }

    /* --------------------------------- Variables -------------------------------- */

    /// @notice The total amount of staked tokens in the pool
    uint256 private s_totalPoolBalance;
    address public s_owner;

    /// @notice The total amount of rewards yet to be distributed
    uint256 private s_totalRewardBalance;

    /// @notice CURRENT total cumulative rewards per token
    uint256 public s_totalRewardPerTokenMask;

    /// @notice SNAPSHOT of the [totalRewardPerTokenMask] at the user's last reward
    /// calculation
    mapping(address => uint256) public s_userRewardPerTokenMask;

    /// @notice The user's rewards data
    mapping(address => Client) public s_client;


    /* --------------------------------- Structs -------------------------------- */
    /// 
    struct Client {
        uint256 pendingAmount;
        uint256 balance;
    }

    /* --------------------------------- Events -------------------------------- */
    event StakedETH(address indexed user, uint256 amount);
    event WithdrawnETH(address indexed user, uint256 amount);
    event DepositedRewards(
        uint256 blockNumber,
        uint256 amount
    );
    event ClaimedRewards(address indexed user, uint256 amount);

    /* --------------------------------- Modifiers -------------------------------- */
    /// @dev Comprueba si el [msg.value] es un valor positivo
    modifier positiveEthValue() {
        require(msg.value > 0, "Must send a positive amount of ETH.");
        _;
    }

    /// @notice Actualiza las recompensas pendientes del usuario y cambia su máscara.
    modifier updateUserRewards(address _account) {
        // Actualiza las recompensas pendientes del usuario
        s_client[_account].pendingAmount = getUserPendingRewards(_account);
        // Actualiza la máscara de recompensa del usuario
        s_userRewardPerTokenMask[_account] = s_totalRewardPerTokenMask;
        _;
    }

    /// @notice Update the contract's total rewards mask with the newest rewards.
    modifier updateTotalRewards(uint256 _reward) {
        s_totalRewardPerTokenMask = getNextTotalRewardMask(_reward);
        _;
    }


    /* --------------------------------- Functions -------------------------------- */
    /// @notice Recibe un depósito de ETH y actualiza el saldo del usuario.
    receive() 
        external
        payable
        nonReentrant
        positiveEthValue
        updateUserRewards(msg.sender)
    {
        s_totalPoolBalance += msg.value;
        s_client[msg.sender].balance += msg.value;
        emit StakedETH(msg.sender, msg.value);
    }

    /// @notice Withdraws all the user's staked tokens and updates the pool's balance.
    function withdrawAllETH() public {
        withdrawExactETH(s_client[msg.sender].balance);
    }

    /// @notice Withdraws an exact amount of user's staked tokens and updates the pool's balance.
    /// @param _amount the exact amount of tokens to withdraw.
    function withdrawExactETH(uint256 _amount)
        public
        nonReentrant
        updateUserRewards(msg.sender)
    {
        uint256 staked = s_client[msg.sender].balance;
        require(staked > 0, "Must have staked ETH to withdraw.");
        require(_amount > 0, "Must unstake a positive value.");
        require(staked >= _amount, "Not enough ETH staked.");

        s_client[msg.sender].balance = staked - _amount;
        s_totalPoolBalance -= _amount;

        // AFAIK This is the preferred way of transferring ETH currently
        (bool sent, ) = msg.sender.call{value: _amount}("");
        require(sent, "Failed to send Ether.");

        emit WithdrawnETH(msg.sender, _amount);
    }

    /* --------------------------------- Views --------------------------------- */
    /// @return the current total of staked tokens.
    function getPoolBalance() public view returns (uint256) {
        return s_totalPoolBalance;
    }

    /// @return the current total of rewards tokens to be distributed.
    function getRewardBalance() public view returns (uint256) {
        return s_totalRewardBalance;
    }

    function getUserBalance(address _account) public view returns(uint256){
        return s_client[_account].balance;
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
        Client memory client = s_client[_account];
        return
            ((client.balance *
                (s_totalRewardPerTokenMask - s_userRewardPerTokenMask[_account])) /
                1e18) + client.pendingAmount;
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
        if (s_totalPoolBalance == 0) {
            return 0;
        }
        return s_totalRewardPerTokenMask + ((_reward * 1e18) / s_totalPoolBalance);
    }

    /* --------------------------------- Rewards -------------------------------- */
    /// @notice Admin's function to distribute rewards to stakers.
    function depositRewards()
        public
        payable
        onlyRole(TEAM_ROLE)
        positiveEthValue
        updateTotalRewards(msg.value)
    {
        require(
            s_totalPoolBalance > 0,
            "The pool must have at least one staking user."
        );
        s_totalRewardBalance += msg.value;
        emit DepositedRewards(block.number, msg.value);
    }

    /// @notice Claim all the user's pending rewards.
    function claimRewards() public nonReentrant updateUserRewards(msg.sender) {
        Client memory client = s_client[msg.sender];
        uint256 pending = client.pendingAmount;
        require(client.pendingAmount > 0, "User has no pending rewards.");
        require(
            address(this).balance >= pending,
            "CRITICAL: Contract has no ETH."
        );
        require(
            s_totalRewardBalance >= pending,
            "CRITICAL: Contract has no rewards left to distribute."
        );

        client.pendingAmount = 0;
        client.balance += pending;
        s_totalPoolBalance += pending;
        s_totalRewardBalance -= pending;

        emit ClaimedRewards(msg.sender, pending);
    }
}
