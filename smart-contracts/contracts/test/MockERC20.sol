// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

abstract contract MockERC20 is ERC20 {
    constructor(string memory _name, string memory _symbol)
        internal
        ERC20(_name, _symbol)
    {}

    function faucet(uint256 _amount) public {
        _mint(msg.sender, _amount);
    }
}
