# My approach to the [Exactly Finance challenge](https://github.com/exactly-finance/challenge)

The project is divided into two sections: `Smart Contracts` & `Frontend`.

> The challenge does not explicitly require a frontend, however I've decided to add it anyway as an extra learning experience for myself.

## 🧙‍♂️ Tech used

-   `Smart Contracts`:
    -   Solidity - _Smart Contracts_
    -   ETH-Brownie - _Development Framework_
-   `Frontend`
    -   React - _UI Framework_
    -   Ethers.js - _Web3 Library_

---

## Index

-   [🤔 Thought Process](#-thought-process)
    -   [The Problem: Efficiency](#the-problem-efficiency)
    -   [Proposed Solution](#proposed-solution)
-   [💻 Set up](#-set-up)
-   [🖱 Give it a try](#-give-it-a-try)
-   [📹 Showcase](#-showcase)
-   [📚 Resources](#-resources)

---

## 🤔 Thought Process

Below is the thought process I took, and the way I decided to solve the challenge.
<a name="b"></a>

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

### The Problem: Efficiency

<a name="efficiency"></a>

It is easy and intuitive to come up with a straight-forward solution that's able to distribute the rewards proportionally between all of the pool's participants whenever the rewards are deposited.

However, _in my opinion_, doing this would not be elegant at all, as it would require looping through all users and calculate their share every single time. In general - though specially in a blockchain context - this would make the transaction considerably **expensive** in terms of computational power, and **not scalable** as it would only get worse the more users are involved.

This is why I've opted to look for an alternative to try and solve this in a much more efficient way.

### Proposed Solution

> ### Domain Assumptions
>
> -   **ERC-20 Reward Token**: For the sake of making it slightly more interesting, I've decided to make the reward token an ERC-20 instead of just ETH.
>
> -   TODO :)

## 💻 Set up

TODO :)

## 🖱 Give it a try

TODO :)

## 📹 Showcase

TODO :)

## 📚 Resources

> ### Smart Contract Solution <a name="resources"></a>
>
> -   Paper _"Scalable Reward Distribution on the Ethereum Blockchain"_ by Bogdan Batog, Lucian Boca, Nick Johnson.
>
> -   EIP-1973 [Scalable Rewards](https://eips.ethereum.org/EIPS/eip-1973).
>
> -   Scalable implementation of the [Synthetix Reward System](https://github.com/Synthetixio/synthetix/blob/develop/contracts/StakingRewards.sol), despite not being completely applicable to this challenge's requirements.
>
> -   [Scalable Reward Distribution with Changing Stake Sizes](https://solmaz.io/2019/02/24/scalable-reward-changing/), Solmaz.io.
