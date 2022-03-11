// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

contract ETHPool {
    /*
    User Address
    User Balance
    
    */

    /* --------------------------------- Staking -------------------------------- */
    // mapping(address => bool) isUserStaking; // Maybe?
    mapping(address => uint256) userStakedAmount;

    /* --------------------------------- Staking -------------------------------- */
    function stakeETH() public payable {
        require(msg.value > 0, "Must send a positive amount of ETH.");    

        userStakedAmount[msg.sender] += msg.value;
    }

}