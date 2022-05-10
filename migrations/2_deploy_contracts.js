var ETHPool = artifacts.require("ETHPool");

module.exports = function(deployer) {
  // deployment steps
  deployer.deploy(ETHPool);
};
