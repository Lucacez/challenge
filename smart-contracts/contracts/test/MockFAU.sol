// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "./MockERC20.sol";

contract MockFAU is MockERC20 {
    constructor() public MockERC20("MockFAU", "FAU") {}
}
