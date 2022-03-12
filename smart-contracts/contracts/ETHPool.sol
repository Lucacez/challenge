// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";

contract ETHPool is Ownable {

    /* --------------------------------- Staking -------------------------------- */
    mapping(address => uint256) public userStakedAmount;

    /* --------------------------------- Rewards -------------------------------- */
    uint256 public totalRewardBalance;

    /* --------------------------------- Events -------------------------------- */
    event StakedETH(
        address indexed user,
        uint256 amount
    );
    event WithdrawnETH(
        address indexed user,
        uint256 amount
    );
    event DepositedRewards(
        uint256 amount
    );

    /* -------------------------------- Modifiers ------------------------------- */
    modifier positiveEthValue {
        require(msg.value > 0, "Must send a positive amount of ETH.");    
        _;
    }

    /* --------------------------------- Staking -------------------------------- */
    function stakeETH() public payable positiveEthValue{
        userStakedAmount[msg.sender] += msg.value;
        emit StakedETH(msg.sender, msg.value);
    }

    function withdrawETH() public {
        uint256 staked = userStakedAmount[msg.sender];
        require(staked > 0, "Must have staked ETH to withdraw.");
        
        userStakedAmount[msg.sender] = 0;

        // AFAIK This is the preferred way of transferring ETH currently
        (bool sent, ) = msg.sender.call{value: staked}("");
        require(sent, "Failed to send Ether.");

        emit WithdrawnETH(msg.sender, staked);
    }

    /* ---------------------------------- View --------------------------------- */
    function getPoolBalance() public view returns (uint256) {
        return address(this).balance;
    }

    /* --------------------------------- Rewards -------------------------------- */
    function depositRewards() public payable onlyOwner positiveEthValue {
        totalRewardBalance += msg.value;
        emit DepositedRewards(msg.value);
    }
}