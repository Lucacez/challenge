# My approach to the [Exactly Finance challenge](https://github.com/exactly-finance/challenge)

The project is divided into two sections: `Smart Contracts` & `Frontend`.

> The challenge does not explicitly require a frontend, however I've decided to add it anwyway as an extra learning experience for myself.

## 🧙‍♂️ Tech used

-   `Smart Contracts`:
    -   Solidity - _Smart Contracts_
    -   ETH-Brownie - _Development Framework_
-   `Frontend`
    -   React - _UI Framework_
    -   Ethers.js - _Web3 Library_

---

## 💻 Set up

TODO :)

## 🤔 Thought Process

Below is the thought process I took, and the way I decided to solve the challenge.

### Smart Contracts

As far as the description goes, only one contract is required, which is `ETHPool`.

It should allow:

-   (Public) Deposit _ETH_ staking.
-   (Public) Withdraw staked _ETH_.
-   (Public) Claim accumulated _ETH_ rewards.
-   (Public) Claim&Withdraw combined method.

--

-   (Owner) Deposit _ETH_ rewards.

--

-   (Read) Check user's staked _ETH_ balance.
-   (Read) Check contract's _ETH_ balance.

The reward system must:

-   Only transfer the _ETH_ rewards to the user when they claim it.
-   Reward calculation only takes into account the users in the pool at the time it is deposited by the owner.
-   More?

### Frontend

TODO :)

> ## Assumptions
>
> TODO :)

## 🖱 Give it a try

TODO :)

## 📹 Showcase

TODO :)
